# profesor/views.py
from django.contrib import messages
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.http import HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET
from gestion_administrativa.models import Tipo_Contrato,Persona
from seguridad.models import PerfilUsuario
from django.db.models.deletion import ProtectedError, RestrictedError
from django.utils import timezone
from django.utils.dateparse import parse_date
from profesor.models import Facilitador
from .forms import FacilitadorAltaForm
from django.contrib.auth.decorators import login_required
from seguridad.decorators import requiere_rol as role_required
from seguridad.models import PerfilUsuario
from profesor.models import Facilitador, Facilitador_has_Contrato, FacilitadorDisponibilidad
from profesor.forms import DisponibilidadForm
from profesor.models import Asignaturas_has_Facilitador
from .forms import AsignaturasProfesorForm
from decimal import Decimal, InvalidOperation
from django.http import HttpResponse
from seguridad.decorators import requiere_rol as role_required
from participante.models import Materia_Inscrita
from gestion_administrativa.models import Asignatura, Periodo_Academico  # ajusta si tu app/paths difieren
from .forms import CargaNotasCSVForm
from .models import Asignaturas_has_Facilitador  # tu tabla puente

import csv
import io
# ==========================
# Helpers
# ==========================

def _msg_integridad(_: Exception) -> str:
    return "No se pudo guardar. Verifica datos duplicados o restricciones relacionadas."

def _msg_protegido() -> str:
    return "No se pudo eliminar porque el registro está relacionado con otros datos."

def _validar_instancia(instance):
    instance.full_clean()
    return instance

def _redirect_next(request, fallback_url: str):
    nxt = request.GET.get("next") or request.POST.get("next")
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        return redirect(nxt)
    return redirect(fallback_url)


# ==========================
# CRUD Facilitador (+ contrato)
# ==========================

def facilitador_list_create(request):
    if request.method == "POST":
        form = FacilitadorAltaForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():
                    persona = form.cleaned_data["id_persona"]  # Persona
                    estatu_fac = form.cleaned_data["id_estatu"]
                    fecha_creacion = form.cleaned_data["fecha_creacion"]

                    tipo_contrato = form.cleaned_data["id_tipo_Contrato"]  # Tipo_Contrato
                    estatu_contrato = form.cleaned_data["id_estatu_contrato"]
                    horas = form.cleaned_data["horas_academicas"]

                    # 1) Crear Facilitador
                    fac = Facilitador(
                        id_persona=persona,
                        id_estatu=estatu_fac,
                        activo=True,
                        fecha_creacion=fecha_creacion,
                        fecha_fin=None,
                    )
                    _validar_instancia(fac)
                    fac.save()

                    # 2) Crear Facilitador_has_Contrato
                    fac_contrato = Facilitador_has_Contrato(
                        id_facilitador=fac,
                        id_contrato=tipo_contrato,     # FK a Tipo_Contrato
                        id_estatu=estatu_contrato,
                        horas_academicas=horas,
                        fecha_inicio=fecha_creacion,
                        fecha_fin=None,
                    )
                    _validar_instancia(fac_contrato)
                    fac_contrato.save()

                    # 3) Asignar grupo "Profesor" (si existe perfil/usuario)
                    perfil = (
                        PerfilUsuario.objects
                        .filter(persona=persona, activo=True)
                        .select_related("user")
                        .first()
                    )
                    if perfil and perfil.user:
                        grupo = Group.objects.filter(name="Profesor").first()
                        if grupo:
                            perfil.user.groups.add(grupo)

                messages.success(request, "Facilitador creado y contrato registrado correctamente.")
                return _redirect_next(request, request.path)

            except IntegrityError as e:
                messages.error(request, _msg_integridad(e))
            except ValidationError as e:
                messages.error(request, f"Validación: {e}")

        else:
            # Muestra errores reales para que no sea “ignorado”
            messages.error(request, "Revisa los campos del formulario.")
            # Opcional útil (si quieres ver rápidamente el error):
            # messages.error(request, str(form.errors))

    else:
        form = FacilitadorAltaForm()

    registros = (
        Facilitador_has_Contrato.objects
        .select_related("id_facilitador", "id_contrato", "id_estatu")
        .order_by("-pk")
    )

    context = {
        "titulo": "Gestión - Facilitadores",
        "form": form,
        "registros": registros,
        "model_name": "facilitador",
    }
    return render(request, "profesor/facilitador_crud.html", context)

# ==========================
# AJAX: Buscar personas por cédula (para el buscador)
# ==========================

@require_GET
def ajax_personas_cedula(request):
    q = (request.GET.get("q") or "").strip()

    if not q.isdigit() or len(q) < 5:
        return JsonResponse({"resultados": []})

    personas = (
        Persona.objects
        .filter(cedula__icontains=q)
        .order_by("cedula")[:10]
    )

    data = [
        {
            "id": p.id_persona,
            "nombre": p.nombre,
            "apellido": p.apellido,
            "cedula": str(p.cedula),
        }
        for p in personas
    ]

    return JsonResponse({"resultados": data})

def facilitador_update(request, pk: int):
    """
    GET (AJAX): devuelve HTML parcial con el form precargado.
    POST (AJAX): guarda, coloca message y redirige a lista (script recarga).
    Edición simple: Facilitador + su contrato ACTIVO (fecha_fin NULL) si existe.

    REGLA:
    - Si el estatus del Facilitador pasa a 2 (Inactivo):
        activo=False, fecha_fin = hoy (servidor).
      Si estatus != 2:
        activo=True, fecha_fin = NULL
    - (Opcional aplicado también al contrato activo):
        Si estatus contrato pasa a 2 => fecha_fin = hoy
        Si estatus contrato != 2 => fecha_fin = NULL
    """
    fac = get_object_or_404(Facilitador, pk=pk)

    contrato_activo = (
        Facilitador_has_Contrato.objects
        .select_related("id_contrato", "id_estatu")
        .filter(id_facilitador=fac, fecha_fin__isnull=True)
        .order_by("-fecha_inicio")
        .first()
    )

    if request.method == "POST":
        try:
            with transaction.atomic():
                # -----------------------
                # Facilitador
                # -----------------------
                id_estatu_str = (request.POST.get("id_estatu") or "").strip()
                fecha_creacion_str = (request.POST.get("fecha_creacion") or "").strip()

                if id_estatu_str:
                    fac.id_estatu_id = int(id_estatu_str)

                    # ✅ Regla: estatus 2 => inactivo y fecha_fin hoy
                    if fac.id_estatu_id == 2:
                        fac.activo = False
                        if not fac.fecha_fin:
                            fac.fecha_fin = timezone.localdate()
                    else:
                        fac.activo = True
                        fac.fecha_fin = None

                if fecha_creacion_str:
                    fc = parse_date(fecha_creacion_str)
                    if fc:
                        fac.fecha_creacion = fc

                _validar_instancia(fac)
                fac.save()

                # -----------------------
                # Contrato activo (si existe)
                # -----------------------
                if contrato_activo:
                    id_tipo_Contrato_str = (request.POST.get("id_tipo_Contrato") or "").strip()
                    id_estatu_contrato_str = (request.POST.get("id_estatu_contrato") or "").strip()
                    horas_str = (request.POST.get("horas_academicas") or "").strip()
                    fecha_inicio_str = (request.POST.get("fecha_inicio") or "").strip()

                    if id_tipo_Contrato_str:
                        contrato_activo.id_contrato_id = int(id_tipo_Contrato_str)

                    if id_estatu_contrato_str:
                        contrato_activo.id_estatu_id = int(id_estatu_contrato_str)

                        # ✅ Regla (recomendada) para contrato:
                        if contrato_activo.id_estatu_id == 2:
                            if not contrato_activo.fecha_fin:
                                contrato_activo.fecha_fin = timezone.localdate()
                        else:
                            contrato_activo.fecha_fin = None

                    if horas_str:
                        contrato_activo.horas_academicas = int(horas_str)

                    if fecha_inicio_str:
                        fi = parse_date(fecha_inicio_str)
                        if fi:
                            contrato_activo.fecha_inicio = fi

                    _validar_instancia(contrato_activo)
                    contrato_activo.save()

            messages.success(request, "Facilitador actualizado correctamente.")
            return _redirect_next(request, reverse("profesor:facilitador"))

        except IntegrityError as e:
            messages.error(request, _msg_integridad(e))
        except ValidationError as e:
            messages.error(request, f"Validación: {e}")

    # GET: render parcial para modal
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        action_url = reverse("profesor:facilitador_editar", args=[fac.pk])

        estatus_qs = estatu.objects.all().order_by("nombre")
        contratos_qs = Tipo_Contrato.objects.all().order_by("nombre")

        return render(
            request,
            "profesor/_form_editar.html",
            {
                "obj": fac,
                "contrato": contrato_activo,
                "action_url": action_url,
                "estatus_qs": estatus_qs,
                "contratos_qs": contratos_qs,
            },
        )

    # Si entran directo por URL (no modal)
    return render(
        request,
        "profesor/editar_pagina.html",
        {"titulo": "Editar Facilitador", "obj": fac, "contrato": contrato_activo},
    )
def facilitador_delete(request, pk: int):
    """
    "Eliminar" = BAJA LÓGICA:
    - Estatus Facilitador => 2
    - activo => False
    - fecha_fin => hoy (servidor)

    Solo permite la baja lógica si NO existe contrato activo:
    - contrato activo = (fecha_fin NULL) y (id_estatu_id == 1)
    """
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    fac = get_object_or_404(Facilitador, pk=pk)

    # 1) Bloquear si tiene contrato ACTIVO (estatus=1 y fecha_fin NULL)
    contrato_activo = fac.contratos.filter(fecha_fin__isnull=True, id_estatu_id=1).exists()
    if contrato_activo:
        messages.error(
            request,
            "No se puede eliminar/inactivar: el facilitador tiene un contrato ACTIVO (estatus=1)."
        )
        return _redirect_next(request, reverse("profesor:facilitador"))

    # 2) Baja lógica del facilitador (y opcionalmente cerrar contrato vigente)
    try:
        with transaction.atomic():
            # Si ya está inactivo, no repetir
            if fac.id_estatu_id == 2 and fac.activo is False:
                if not fac.fecha_fin:
                    fac.fecha_fin = timezone.localdate()
                    _validar_instancia(fac)
                    fac.save(update_fields=["fecha_fin"])
                messages.info(request, "Este facilitador ya está inactivo.")
                return _redirect_next(request, reverse("profesor:facilitador"))

            # Baja lógica
            fac.id_estatu_id = 2
            fac.activo = False
            fac.fecha_fin = timezone.localdate()

            _validar_instancia(fac)
            fac.save(update_fields=["id_estatu", "activo", "fecha_fin"])

            # (Recomendado) si hay algún contrato "vigente" pero NO activo (estatus!=1) con fecha_fin NULL, lo cerramos
            fac.contratos.filter(fecha_fin__isnull=True).update(fecha_fin=timezone.localdate())

        messages.success(request, "Facilitador inactivado (baja lógica) correctamente.")

    except ProtectedError:
        messages.error(request, _msg_protegido())
    except IntegrityError:
        messages.error(request, "No se pudo inactivar por restricciones en la base de datos.")
    except ValidationError as e:
        messages.error(request, f"Validación: {e}")

    return _redirect_next(request, reverse("profesor:facilitador"))



def _facilitador_activo_desde_user(user):
    perfil = PerfilUsuario.objects.filter(user=user, activo=True).select_related("persona").first()
    if not perfil or not perfil.persona_id:
        return None

    fac = (
        Facilitador.objects
        .filter(id_persona=perfil.persona, activo=True, fecha_fin__isnull=True)
        .select_related("id_persona")
        .first()
    )
    return fac


def _contrato_activo(facilitador):
    """
    Contrato activo = fecha_fin NULL y estatus 1 (según tu regla).
    """
    return (
        Facilitador_has_Contrato.objects
        .filter(id_facilitador=facilitador, fecha_fin__isnull=True, id_estatu_id=1)
        .order_by("-fecha_inicio")
        .first()
    )


@login_required
@role_required("Profesor")
def disponibilidad(request):
    fac = _facilitador_activo_desde_user(request.user)
    if not fac:
        messages.error(request, "No se encontró un Facilitador activo asociado a tu usuario.")
        return redirect("login")

    contrato = _contrato_activo(fac)
    if not contrato:
        messages.error(request, "No tienes un contrato ACTIVO (estatus 1) asociado. Contacta al administrador.")
        return redirect("seguridad:inicio_profesor")

    horas_total = int(contrato.horas_academicas or 0)

    disp = FacilitadorDisponibilidad.objects.filter(id_facilitador=fac).first()

    if request.method == "POST":
        form = DisponibilidadForm(request.POST)
        if form.is_valid():
            h_l = form.cleaned_data["horas_lunes"]
            h_m = form.cleaned_data["horas_martes"]
            h_x = form.cleaned_data["horas_miercoles"]
            h_j = form.cleaned_data["horas_jueves"]
            h_v = form.cleaned_data["horas_viernes"]
            h_s = form.cleaned_data["horas_sabado"]

            suma = int(h_l + h_m + h_x + h_j + h_v + h_s)

            if suma != horas_total:
                messages.error(
                    request,
                    f"La suma de horas (L-S) debe ser exactamente {horas_total}. Actualmente tienes {suma}."
                )
            else:
                try:
                    with transaction.atomic():
                        if not disp:
                            disp = FacilitadorDisponibilidad(id_facilitador=fac)

                        disp.horas_lunes = h_l
                        disp.horas_martes = h_m
                        disp.horas_miercoles = h_x
                        disp.horas_jueves = h_j
                        disp.horas_viernes = h_v
                        disp.horas_sabado = h_s

                        disp.full_clean()
                        disp.save()

                    messages.success(request, "Disponibilidad guardada correctamente.")
                    return redirect(request.path)

                except Exception as e:
                    messages.error(request, f"No se pudo guardar la disponibilidad: {e}")
        else:
            messages.error(request, f"Revisa los campos del formulario: {form.errors}")

    else:
        initial = {
            "horas_lunes": disp.horas_lunes if disp else 0,
            "horas_martes": disp.horas_martes if disp else 0,
            "horas_miercoles": disp.horas_miercoles if disp else 0,
            "horas_jueves": disp.horas_jueves if disp else 0,
            "horas_viernes": disp.horas_viernes if disp else 0,
            "horas_sabado": disp.horas_sabado if disp else 0,
        }
        form = DisponibilidadForm(initial=initial)

    # ✅ lo que la tabla inferior va a renderizar
    disponibilidad = {
        "lunes": disp.horas_lunes if disp else 0,
        "martes": disp.horas_martes if disp else 0,
        "miercoles": disp.horas_miercoles if disp else 0,
        "jueves": disp.horas_jueves if disp else 0,
        "viernes": disp.horas_viernes if disp else 0,
        "sabado": disp.horas_sabado if disp else 0,
    }

    context = {
        "titulo": "Disponibilidad del Profesor",
        "form": form,
        "horas_total": horas_total,
        "disponibilidad": disponibilidad,  # ✅ usado por el template
    }
    return render(request, "profesor/disponibilidad.html", context)


@login_required
@role_required("Profesor")
def gestionar_asignaturas(request):
    """
    Profesor selecciona qué asignaturas impartirá.
    - POST: set exacto (crea faltantes / elimina sobrantes) en Asignaturas_has_Facilitador
    - GET: muestra checkboxes + tabla de asignaturas asignadas
    """
    fac = _facilitador_activo_desde_user(request.user)
    if not fac:
        messages.error(request, "No se encontró un Facilitador activo asociado a tu usuario.")
        return redirect("login")

    # asignadas actuales
    asignadas_qs = (
        Asignaturas_has_Facilitador.objects
        .select_related("id_asignatura")
        .filter(id_facilitador=fac)
        .order_by("id_asignatura__nombre")
    )
    asignadas_ids = list(asignadas_qs.values_list("id_asignatura_id", flat=True))

    if request.method == "POST":
        form = AsignaturasProfesorForm(request.POST)
        if form.is_valid():
            nuevos_ids = list(form.cleaned_data["asignaturas"].values_list("id_asignatura", flat=True))

            actuales_set = set(asignadas_ids)
            nuevos_set = set(nuevos_ids)

            to_add = list(nuevos_set - actuales_set)
            to_del = list(actuales_set - nuevos_set)

            try:
                with transaction.atomic():
                    # eliminar las que quitó
                    if to_del:
                        Asignaturas_has_Facilitador.objects.filter(
                            id_facilitador=fac,
                            id_asignatura_id__in=to_del
                        ).delete()

                    # crear nuevas con valores por defecto (cupos=30, presencial=True)
                    if to_add:
                        Asignaturas_has_Facilitador.objects.bulk_create([
                            Asignaturas_has_Facilitador(
                                id_facilitador=fac,
                                id_asignatura_id=aid,
                                cupos=30,
                                presencial=True,
                            )
                            for aid in to_add
                        ])

                messages.success(request, "Asignaturas actualizadas correctamente.")
                return redirect(request.path)

            except Exception as e:
                messages.error(request, f"No se pudieron actualizar las asignaturas: {e}")
        else:
            messages.error(request, f"Revisa el formulario: {form.errors}")

    else:
        # precargar checkboxes con asignadas
        form = AsignaturasProfesorForm(initial={"asignaturas": asignadas_ids})

    # recargar tabla (por si POST)
    asignadas_qs = (
        Asignaturas_has_Facilitador.objects
        .select_related("id_asignatura")
        .filter(id_facilitador=fac)
        .order_by("id_asignatura__nombre")
    )

    return render(request, "profesor/asignaturas.html", {
        "titulo": "Gestionar asignaturas",
        "form": form,
        "asignadas": asignadas_qs,
    })



def cargar_notas(request):

    fac = _facilitador_activo_desde_user(request.user)
    if not fac:
        messages.error(request, "No se encontró un Facilitador activo asociado a tu usuario.")
        return redirect("login")

    # Asignaturas que este profesor puede manejar (tabla puente)
    asignaturas_ids = list(
        Asignaturas_has_Facilitador.objects.filter(id_facilitador=fac)
        .values_list("id_asignatura_id", flat=True)
    )

    asignaturas = Asignatura.objects.filter(id_asignatura__in=asignaturas_ids).order_by("nombre")

    # ---- selección (GET) ----
    asignatura_id = (request.GET.get("asignatura") or "").strip()
    seccion = (request.GET.get("seccion") or "").strip()
    periodo_id = (request.GET.get("periodo") or "").strip()

    asignatura_sel = None
    periodo_sel = None

    if asignatura_id.isdigit() and int(asignatura_id) in asignaturas_ids:
        asignatura_sel = Asignatura.objects.filter(pk=int(asignatura_id)).first()

    # Periodos disponibles: los que tengan inscripciones para asignaturas del profesor
    periodos_ids = (
        Materia_Inscrita.objects
        .filter(id_asignatura_id__in=asignaturas_ids)
        .values_list("id_periodo_id", flat=True)
        .distinct()
    )

    periodos_disponibles = (
        Periodo_Academico.objects
        .filter(id_periodo__in=periodos_ids)
        .order_by("-id_periodo")
    )


    if periodo_id.isdigit():
        periodo_sel = Periodo_Academico.objects.filter(pk=int(periodo_id)).first()
    if not periodo_sel:
        periodo_sel = periodos_disponibles.first()

    # Secciones disponibles según selección
    secciones_disponibles = []
    if asignatura_sel and periodo_sel:
        secciones_disponibles = list(
            Materia_Inscrita.objects.filter(
                id_asignatura=asignatura_sel,
                id_periodo=periodo_sel,
            )
            .exclude(seccion__isnull=True)
            .exclude(seccion__exact="")
            .values_list("seccion", flat=True)
            .distinct()
            .order_by("seccion")
        )

    # Registros a mostrar (tabla)
    inscripciones = []
    if asignatura_sel and periodo_sel and seccion:
        inscripciones = (
            Materia_Inscrita.objects
            .select_related("id_estudiante__id_persona", "id_asignatura", "id_periodo")
            .filter(
                id_asignatura=asignatura_sel,
                id_periodo=periodo_sel,
                seccion=seccion,
            )
            .order_by("id_estudiante__id_persona__apellido", "id_estudiante__id_persona__nombre")
        )

    # ---- POST: Manual o CSV ----
    csv_form = CargaNotasCSVForm()

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()

        # Re-leer selección desde hidden inputs (POST) para evitar inconsistencias
        asignatura_id_p = (request.POST.get("asignatura") or "").strip()
        seccion_p = (request.POST.get("seccion") or "").strip()
        periodo_id_p = (request.POST.get("periodo") or "").strip()

        if not (asignatura_id_p.isdigit() and periodo_id_p.isdigit() and seccion_p):
            messages.error(request, "Debes seleccionar Asignatura, Período y Sección.")
            return redirect(request.path)

        if int(asignatura_id_p) not in asignaturas_ids:
            messages.error(request, "No tienes acceso a esa asignatura.")
            return redirect(request.path)

        asignatura_sel = Asignatura.objects.filter(pk=int(asignatura_id_p)).first()
        periodo_sel = Periodo_Academico.objects.filter(pk=int(periodo_id_p)).first()

        if not asignatura_sel or not periodo_sel:
            messages.error(request, "Selección inválida.")
            return redirect(request.path)

        qs = (
            Materia_Inscrita.objects
            .select_related("id_estudiante__id_persona")
            .filter(id_asignatura=asignatura_sel, id_periodo=periodo_sel, seccion=seccion_p)
        )

        if action == "manual":
            # espera inputs: nota_<id_materia_inscrita>
            try:
                with transaction.atomic():
                    actualizados = 0
                    errores = []

                    for mi in qs:
                        key = f"nota_{mi.id_materia_inscrita}"
                        raw = request.POST.get(key)
                        try:
                            nota = _parse_nota(raw)
                            mi.nota = nota
                            mi.full_clean()
                            mi.save(update_fields=["nota"])
                            actualizados += 1
                        except Exception as e:
                            errores.append(f"Cédula {mi.id_estudiante.id_persona.cedula}: {e}")

                    if errores:
                        messages.error(request, "Algunas notas no se pudieron guardar.")
                        for e in errores[:6]:
                            messages.error(request, e)
                        if len(errores) > 6:
                            messages.error(request, f"... y {len(errores)-6} más.")
                    else:
                        messages.success(request, f"Notas guardadas correctamente ({actualizados} registros).")

            except Exception as e:
                messages.error(request, f"No se pudo guardar el lote manual: {e}")

            return redirect(f"{request.path}?asignatura={asignatura_sel.pk}&periodo={periodo_sel.pk}&seccion={seccion_p}")

        if action == "csv":
            csv_form = CargaNotasCSVForm(request.POST, request.FILES)
            if not csv_form.is_valid():
                messages.error(request, f"Revisa el archivo: {csv_form.errors}")
                return redirect(f"{request.path}?asignatura={asignatura_sel.pk}&periodo={periodo_sel.pk}&seccion={seccion_p}")

            f = csv_form.cleaned_data["archivo"]

            try:
                content = f.read().decode("utf-8-sig")
            except Exception:
                messages.error(request, "No se pudo leer el archivo (codificación). Usa UTF-8.")
                return redirect(f"{request.path}?asignatura={asignatura_sel.pk}&periodo={periodo_sel.pk}&seccion={seccion_p}")

            reader = csv.DictReader(io.StringIO(content))
            headers = [h.strip().lower() for h in (reader.fieldnames or [])]

            # Aceptamos 2 formatos:
            # A) cedula, nota
            # B) id_materia_inscrita, nota
            use_cedula = "cedula" in headers and "nota" in headers
            use_idmi = "id_materia_inscrita" in headers and "nota" in headers

            if not (use_cedula or use_idmi):
                messages.error(request, "CSV inválido. Debe incluir: (cedula,nota) o (id_materia_inscrita,nota).")
                return redirect(f"{request.path}?asignatura={asignatura_sel.pk}&periodo={periodo_sel.pk}&seccion={seccion_p}")

            # Mapa para validar pertenencia a la sección
            mi_by_id = {str(mi.id_materia_inscrita): mi for mi in qs}
            mi_by_ced = {str(mi.id_estudiante.id_persona.cedula): mi for mi in qs}

            actualizados = 0
            errores = []

            try:
                with transaction.atomic():
                    for i, row in enumerate(reader, start=2):
                        try:
                            raw_nota = row.get("nota") or row.get("Nota") or ""
                            nota = _parse_nota(raw_nota)

                            if use_idmi:
                                key = str(row.get("id_materia_inscrita") or "").strip()
                                mi = mi_by_id.get(key)
                                if not mi:
                                    raise ValueError(f"id_materia_inscrita {key} no pertenece a esta sección.")
                            else:
                                ced = str(row.get("cedula") or "").strip()
                                mi = mi_by_ced.get(ced)
                                if not mi:
                                    raise ValueError(f"Cédula {ced} no pertenece a esta sección.")

                            mi.nota = nota
                            mi.full_clean()
                            mi.save(update_fields=["nota"])
                            actualizados += 1

                        except Exception as e:
                            errores.append(f"Línea {i}: {e}")

                if errores:
                    messages.error(request, "Se cargó el CSV con errores.")
                    for e in errores[:6]:
                        messages.error(request, e)
                    if len(errores) > 6:
                        messages.error(request, f"... y {len(errores)-6} más.")
                else:
                    messages.success(request, f"CSV aplicado correctamente ({actualizados} notas).")

            except Exception as e:
                messages.error(request, f"No se pudo procesar el CSV: {e}")

            return redirect(f"{request.path}?asignatura={asignatura_sel.pk}&periodo={periodo_sel.pk}&seccion={seccion_p}")

        messages.error(request, "Acción inválida.")
        return redirect(request.path)

    context = {
        "titulo": "Carga de notas",
        "asignaturas": asignaturas,
        "periodos": periodos_disponibles,
        "asignatura_sel": asignatura_sel,
        "periodo_sel": periodo_sel,
        "secciones": secciones_disponibles,
        "seccion_sel": seccion,
        "inscripciones": inscripciones,
        "csv_form": csv_form,
    }
    return render(request, "profesor/cargar_notas.html", context)