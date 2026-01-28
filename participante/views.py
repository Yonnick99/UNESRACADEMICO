# participante/views.py
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from gestion_administrativa.models import Persona, Mencion
from seguridad.models import PerfilUsuario
from django.db.models import Q
from .models import Estudiantes_has_Carreras, Estudiante

from .forms import EstudianteForm
from django.contrib.auth.models import Group


def menciones_por_carrera(request, carrera_id: int):
    menciones = (
        Mencion.objects
        .filter(id_carrera_id=carrera_id)
        .order_by("nombre")
        .values("id_mencion", "nombre")
    )
    return JsonResponse({"results": list(menciones)})

# ==========================
# Helpers
# ==========================

def _msg_integridad(_: Exception) -> str:
    return "No se pudo guardar. Verifica datos duplicados o restricciones relacionadas."

def _msg_protegido() -> str:
    return "No se pudo eliminar porque el registro está relacionado con otros datos."

def _validar_instancia(form):
    instancia = form.instance
    instancia.full_clean()
    return instancia

def _redirect_next(request, fallback_url: str):
    """
    Permite volver a la URL anterior (por ejemplo manteniendo ?page=3)
    usando ?next=...
    """
    nxt = request.GET.get("next") or request.POST.get("next")
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        return redirect(nxt)
    return redirect(fallback_url)


# ==========================
# CRUD Estudiante
# ==========================

from django.db.models import Q


def estudiante_list_create(request):
    if request.method == "POST":
        form = EstudianteForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():
                    persona = form.cleaned_data["id_persona"]
                    carrera_nueva = form.cleaned_data.get("id_carrera")
                    mencion_nueva = form.cleaned_data.get("id_mencion")

                    # 1) Si ya existe ACTIVO con la MISMA mención => BLOQUEAR inmediatamente
                    existe_misma_mencion_activa = Estudiante.objects.filter(
                        id_persona=persona,
                        id_mencion=mencion_nueva,
                        activo=True,
                        fecha_fin__isnull=True,
                    ).exists()

                    if existe_misma_mencion_activa:
                        # Para el mensaje, buscamos el registro activo (solo para mostrar carrera/mención)
                        est_activo = (
                            Estudiante.objects
                            .select_related("id_carrera", "id_mencion")
                            .filter(id_persona=persona, activo=True, fecha_fin__isnull=True)
                            .order_by("-id_estudiante")
                            .first()
                        )
                        carrera = getattr(est_activo.id_carrera, "nombre", "N/A") if est_activo else "N/A"
                        mencion = getattr(est_activo.id_mencion, "nombre", "N/A") if est_activo else "N/A"

                        messages.warning(
                            request,
                            f"⚠️ Esta persona ya posee una carrera activa (Carrera: {carrera}, Mención: {mencion})."
                        )
                        return _redirect_next(request, request.path)

                    # 2) Si tiene OTRA carrera/mención activa => SOLO ADVERTIR (tu comportamiento original)
                    est_activo_otro = (
                        Estudiante.objects
                        .select_related("id_carrera", "id_mencion")
                        .filter(id_persona=persona, activo=True, fecha_fin__isnull=True)
                        .exclude(id_mencion=mencion_nueva)
                        .order_by("-id_estudiante")
                        .first()
                    )
                    if est_activo_otro:
                        carrera = getattr(est_activo_otro.id_carrera, "nombre", "N/A")
                        mencion = getattr(est_activo_otro.id_mencion, "nombre", "N/A")
                        messages.warning(
                            request,
                            f"⚠️ Esta persona ya posee una carrera activa (Carrera: {carrera}, Mención: {mencion})."
                        )

                    # 3) Guardar normal
                    _validar_instancia(form)
                    estudiante = form.save()

                    # 4) Asignar grupo "Participante" al user de esa persona (si existe PerfilUsuario)
                    perfil = (
                        PerfilUsuario.objects
                        .filter(persona=persona, activo=True)
                        .select_related("user")
                        .first()
                    )
                    if perfil and perfil.user:
                        grupo = Group.objects.filter(name="Participante").first()
                        if grupo:
                            perfil.user.groups.add(grupo)

                messages.success(request, "Estudiante creado correctamente.")
                return _redirect_next(request, request.path)

            except IntegrityError as e:
                messages.error(request, _msg_integridad(e))
            except ValidationError as e:
                messages.error(request, f"Validación: {e}")
        else:
            messages.error(request, f"Revisa los campos del formulario: {form.errors}")

    else:
        form = EstudianteForm()

    registros = Estudiante.objects.select_related(
        "id_persona", "id_carrera", "id_mencion"
    ).order_by("-pk")

    context = {
        "titulo": "Gestión - Estudiantes",
        "form": form,
        "registros": registros,
        "model_name": "estudiante",
    }
    return render(request, "participante/estudiante_crud.html", context)


def estudiante_update(request, pk: int):
    """
    GET (AJAX): devuelve HTML parcial con el form precargado
    POST (AJAX): guarda y redirige al listado (tu script detecta redirect y recarga)
    """
    obj = get_object_or_404(Estudiante, pk=pk)

    if request.method == "POST":
        form = EstudianteForm(request.POST, instance=obj)
        if form.is_valid():
            try:
                with transaction.atomic():
                    _validar_instancia(form)
                    form.save()
                messages.success(request, "Estudiante actualizado correctamente.")
                # Nota: volvemos a la lista; si vienes con ?page=3, pásalo como next
                return _redirect_next(request, reverse("participante:estudiante"))
            except IntegrityError as e:
                messages.error(request, _msg_integridad(e))
            except ValidationError as e:
                messages.error(request, f"Validación: {e}")
        else:
            messages.error(request, "Revisa los campos del formulario.")
    else:
        form = EstudianteForm(instance=obj)

    # Si es modal (AJAX) devolvemos SOLO el parcial
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        action_url = reverse("participante:estudiante_editar", args=[obj.pk])
        return render(
            request,
            "participante/_form_editar.html",
            {"form": form, "obj": obj, "action_url": action_url},
        )

    # Si alguien abre directo la URL de edición, renderizamos una página simple
    return render(
        request,
        "participante/editar_pagina.html",
        {"titulo": "Editar Estudiante", "form": form, "obj": obj},
    )


def estudiante_delete(request, pk: int):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    obj = get_object_or_404(Estudiante, pk=pk)

    try:
        with transaction.atomic():
            obj.delete()
        messages.success(request, "Estudiante eliminado correctamente.")
    except ProtectedError:
        messages.error(request, _msg_protegido())
    except IntegrityError as e:
        messages.error(request, _msg_integridad(e))

    return _redirect_next(request, reverse("participante:estudiante"))


@require_GET
def persona_buscar_por_cedula(request):
    """
    AJAX: devuelve lista de Personas cuyo campo cedula contenga el valor.
    - Requiere mínimo 5 dígitos.
    Retorna JSON con: id_persona, cedula, nombre, apellido
    """
    term = (request.GET.get("cedula") or "").strip()

    # solo dígitos
    term_digits = "".join(ch for ch in term if ch.isdigit())

    if len(term_digits) < 5:
        return JsonResponse({"results": []})

    qs = (
        Persona.objects
        .filter(cedula__icontains=term_digits)
        .order_by("cedula")[:10]
    )

    results = [
        {
            "id_persona": p.id_persona,
            "cedula": p.cedula,
            "nombre": p.nombre,
            "apellido": p.apellido,
        }
        for p in qs
    ]
    return JsonResponse({"results": results})
