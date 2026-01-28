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
from gestion_administrativa.models import estatu, Tipo_Contrato,Persona
from seguridad.models import PerfilUsuario
from django.db.models.deletion import ProtectedError, RestrictedError
from django.utils import timezone
from django.utils.dateparse import parse_date
from .forms import FacilitadorAltaForm
from .models import Facilitador, Facilitador_has_Contrato

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
