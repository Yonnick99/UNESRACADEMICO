# gestion_administrativa/views.py
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError, RestrictedError
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from .forms import (EstatuForm, MencionForm, CarreraForm, TipoMateriaForm, PeriodoAcademicoForm, TipoContratoForm, PisoForm, AulaForm, AsignaturaForm, PersonaForm, PrelacionesForm)
from .models import (estatu,Mencion,Carrera,Tipo_Materia,Periodo_Academico,Tipo_Contrato,Piso,aula,Asignatura,Persona,Prelaciones   )

# ============================================================
# Helpers de validación/errores (Create/Update/Delete)
# ============================================================

def _msg_integridad(e: Exception) -> str:
    """
    Mensaje humano para IntegrityError.
    (Sin depender de detalles del motor; sirve para UNIQUE/FK/constraints)
    """
    return "No se pudo guardar. Verifica datos duplicados o restricciones relacionadas."


def _msg_protegido() -> str:
    return "No se pudo eliminar porque el registro está relacionado con otros datos."


def _validar_instancia(form):
    """
    Ejecuta validación completa del modelo (incluye constraints) antes de guardar.
    """
    instancia = form.instance
    instancia.full_clean()
    return instancia


# ============================================================
# CRUD base: (Create + List) en una sola pantalla
# Update y Delete son vistas separadas (para modal o página)
# ============================================================

def catalogo_list_create(request, *, model, form_class, template_name, titulo):
    """
    Vista tipo "componente":
    - Formulario arriba (POST crea)
    - Tabla abajo (GET lista)
    """
    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    _validar_instancia(form)
                    form.save()
                messages.success(request, "Registro creado correctamente.")
                return redirect(request.path)
            except (IntegrityError,) as e:
                messages.error(request, _msg_integridad(e))
            except ValidationError as e:
                messages.error(request, f"Validación: {e}")
        else:
            messages.error(request, "Revisa los campos del formulario.")
    else:
        form = form_class()

    # =========================
    # Paginación (15 por página)
    # =========================
    qs = model.objects.all().order_by("-pk")
    paginator = Paginator(qs, 10)

    page_number = request.GET.get("page", "1")

    # Sanitiza page para evitar page=0 o negativos
    try:
        page_int = int(page_number)
    except (TypeError, ValueError):
        page_int = 1

    if page_int < 1:
        page_int = 1

    page_obj = paginator.get_page(page_int)
    registros = page_obj.object_list


    context = {
        "titulo": titulo,
        "form": form,
        "registros": registros,
        "page_obj": page_obj,
        "model_name": model._meta.model_name,
    }
    return render(request, template_name, context)

def catalogo_update(request, *, model, form_class, template_name, pk, titulo):
    """
    Update con validación.
    - Si la petición es AJAX (modal), devuelve SOLO el formulario (partial).
    - Si no es AJAX, devuelve el template normal.
    """
    obj = get_object_or_404(model, pk=pk)

    if request.method == "POST":
        form = form_class(request.POST, instance=obj)
        if form.is_valid():
            try:
                with transaction.atomic():
                    _validar_instancia(form)
                    form.save()
                messages.success(request, "Registro actualizado correctamente.")
                return redirect(reverse(f"gestion_administrativa:{model._meta.model_name}"))
            except IntegrityError as e:
                messages.error(request, _msg_integridad(e))
            except ValidationError as e:
                messages.error(request, f"Validación: {e}")
        else:
            messages.error(request, "Revisa los campos del formulario.")

        # Si el POST viene del modal y hay errores, devolvemos el form con errores como parcial
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            action_url = reverse(
                f"gestion_administrativa:{model._meta.model_name}_editar",
                args=[obj.pk],
            )
            return render(
                request,
                "gestion_administrativa/_modal_form_editar.html",
                {"form": form, "obj": obj, "action_url": action_url},
            )

    else:
        # GET normal: construye el form
        form = form_class(instance=obj)

        # Si es AJAX (modal), devolvemos SOLO el form (partial)
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            action_url = reverse(
                f"gestion_administrativa:{model._meta.model_name}_editar",
                args=[obj.pk],
            )
            return render(
                request,
                "gestion_administrativa/_modal_form_editar.html",
                {"form": form, "obj": obj, "action_url": action_url},
            )

    # Render normal (no modal)
    return render(request, template_name, {"titulo": titulo, "form": form, "obj": obj})

def catalogo_delete(request, *, model, pk):
    """
    Delete con validación:
    - Solo por POST (seguridad)
    - Captura ProtectedError (FK RESTRICT)
    - Captura IntegrityError (constraints)
    """
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    obj = get_object_or_404(model, pk=pk)

    try:
        with transaction.atomic():
            obj.delete()
        messages.success(request, "Registro eliminado correctamente.")
    except (ProtectedError, RestrictedError):
        messages.error(request, _msg_protegido())
    except IntegrityError as e:
        messages.error(request, _msg_integridad(e))

    return redirect(reverse(f"gestion_administrativa:{model._meta.model_name}"))



# ============================================================
# 1) ESTATUS
# ============================================================

def estatu_list(request):
    return catalogo_list_create(
        request,
        model=estatu,
        form_class=EstatuForm,
        template_name="gestion_administrativa/crud_base.html",
        titulo="Estatus",
    )


def estatu_update(request, pk: int):
    return catalogo_update(
        request,
        model=estatu,
        form_class=EstatuForm,
        template_name="gestion_administrativa/crud_base.html",
        pk=pk,
        titulo="Editar Estatus",
    )


def estatu_delete(request, pk: int):
    return catalogo_delete(request, model=estatu, pk=pk)


# ============================================================
# 2) MENCION
# ============================================================

def mencion_list(request):
    return catalogo_list_create(
        request,
        model=Mencion,
        form_class=MencionForm,
        template_name="gestion_administrativa/crud_base.html",
        titulo="Menciones",
    )


def mencion_update(request, pk: int):
    return catalogo_update(
        request,
        model=Mencion,
        form_class=MencionForm,
        template_name="gestion_administrativa/crud_base.html",
        pk=pk,
        titulo="Editar Mención",
    )


def mencion_delete(request, pk: int):
    return catalogo_delete(request, model=Mencion, pk=pk)


# ============================================================
# 3) CARRERA
# ============================================================

def carrera_list(request):
    return catalogo_list_create(
        request,
        model=Carrera,
        form_class=CarreraForm,
        template_name="gestion_administrativa/crud_base.html",
        titulo="Carreras",
    )


def carrera_update(request, pk: int):
    return catalogo_update(
        request,
        model=Carrera,
        form_class=CarreraForm,
        template_name="gestion_administrativa/crud_base.html",
        pk=pk,
        titulo="Editar Carrera",
    )


def carrera_delete(request, pk: int):
    return catalogo_delete(request, model=Carrera, pk=pk)


# ============================================================
# 4) TIPO MATERIA
# ============================================================

def tipo_materia_list(request):
    return catalogo_list_create(
        request,
        model=Tipo_Materia,
        form_class=TipoMateriaForm,
        template_name="gestion_administrativa/crud_base.html",
        titulo="Tipos de Materia",
    )


def tipo_materia_update(request, pk: int):
    return catalogo_update(
        request,
        model=Tipo_Materia,
        form_class=TipoMateriaForm,
        template_name="gestion_administrativa/crud_base.html",
        pk=pk,
        titulo="Editar Tipo de Materia",
    )


def tipo_materia_delete(request, pk: int):
    return catalogo_delete(request, model=Tipo_Materia, pk=pk)


# ============================================================
# 5) PERIODO ACADEMICO
# ============================================================

def periodo_list(request):
    return catalogo_list_create(
        request,
        model=Periodo_Academico,
        form_class=PeriodoAcademicoForm,
        template_name="gestion_administrativa/crud_base.html",
        titulo="Períodos Académicos",
    )


def periodo_update(request, pk: int):
    return catalogo_update(
        request,
        model=Periodo_Academico,
        form_class=PeriodoAcademicoForm,
        template_name="gestion_administrativa/crud_base.html",
        pk=pk,
        titulo="Editar Período Académico",
    )


def periodo_delete(request, pk: int):
    return catalogo_delete(request, model=Periodo_Academico, pk=pk)


# ============================================================
# 6) TIPO CONTRATO
# ============================================================

def tipo_contrato_list(request):
    return catalogo_list_create(
        request,
        model=Tipo_Contrato,
        form_class=TipoContratoForm,
        template_name="gestion_administrativa/crud_base.html",
        titulo="Tipos de Contrato",
    )


def tipo_contrato_update(request, pk: int):
    return catalogo_update(
        request,
        model=Tipo_Contrato,
        form_class=TipoContratoForm,
        template_name="gestion_administrativa/crud_base.html",
        pk=pk,
        titulo="Editar Tipo de Contrato",
    )


def tipo_contrato_delete(request, pk: int):
    return catalogo_delete(request, model=Tipo_Contrato, pk=pk)


# ============================================================
# 8) PISO
# ============================================================

def piso_list(request):
    return catalogo_list_create(
        request,
        model=Piso,
        form_class=PisoForm,
        template_name="gestion_administrativa/crud_base.html",
        titulo="Pisos",
    )


def piso_update(request, pk: int):
    return catalogo_update(
        request,
        model=Piso,
        form_class=PisoForm,
        template_name="gestion_administrativa/crud_base.html",
        pk=pk,
        titulo="Editar Piso",
    )


def piso_delete(request, pk: int):
    return catalogo_delete(request, model=Piso, pk=pk)


# ============================================================
# 9) AULA
# ============================================================

def aula_list(request):
    return catalogo_list_create(
        request,
        model=aula,
        form_class=AulaForm,
        template_name="gestion_administrativa/crud_base.html",
        titulo="Aulas",
    )


def aula_update(request, pk: int):
    return catalogo_update(
        request,
        model=aula,
        form_class=AulaForm,
        template_name="gestion_administrativa/crud_base.html",
        pk=pk,
        titulo="Editar Aula",
    )


def aula_delete(request, pk: int):
    return catalogo_delete(request, model=aula, pk=pk)




def prelaciones_list(request):
    return catalogo_list_create(
        request,
        model=Prelaciones,
        form_class=PrelacionesForm,
        template_name="gestion_administrativa/crud_base.html",
        titulo="Prelaciones",
    )



def prelaciones_update(request, pk: int):
    return catalogo_update(
        request,
        model=Prelaciones,
        form_class=PrelacionesForm,
        template_name="gestion_administrativa/crud_base.html",
        pk=pk,
        titulo="Editar Prelación",
    )



def prelaciones_delete(request, pk: int):
    return catalogo_delete(request, model=Prelaciones, pk=pk)

# ============================================================
# 10) ASIGNATURA
# ============================================================

def asignatura_list(request):
    return catalogo_list_create(
        request,
        model=Asignatura,
        form_class=AsignaturaForm,
        template_name="gestion_administrativa/crud_base.html",
        titulo="Asignaturas",
    )


def asignatura_update(request, pk: int):
    return catalogo_update(
        request,
        model=Asignatura,
        form_class=AsignaturaForm,
        template_name="gestion_administrativa/crud_base.html",
        pk=pk,
        titulo="Editar Asignatura",
    )


def periodo_list(request):
    """
    Listado + creación de Períodos Académicos
    """
    return catalogo_list_create(
        request,
        model=Periodo_Academico,
        form_class=PeriodoAcademicoForm,
        template_name="gestion_administrativa/crud_base.html",
        titulo="Períodos Académicos",
    )


def periodo_update(request, pk: int):
    """
    Edición de Período Académico
    """
    return catalogo_update(
        request,
        model=Periodo_Academico,
        form_class=PeriodoAcademicoForm,
        template_name="gestion_administrativa/crud_base.html",
        pk=pk,
        titulo="Editar Período Académico",
    )


def periodo_delete(request, pk: int):
    """
    Eliminación de Período Académico
    """
    return catalogo_delete(
        request,
        model=Periodo_Academico,
        pk=pk,
    )

def asignatura_delete(request, pk: int):
    return catalogo_delete(request, model=Asignatura, pk=pk)


def consulta_list(request, clave: str):
    """
    Consulta reutilizable (solo lectura) para:
    estatus, carreras, menciones, tipos-materia, asignaturas, periodos, tipos-contrato, pisos, aulas

    Soporta:
    - q (búsqueda)
    - orden (campo)
    - dir (asc/desc)
    - page (paginación 15)
    """

    # ===========================
    # 1) Registro de "componentes" consultables
    # ===========================
    # columnas: encabezados para tabla
    # fields: campos del modelo que renderizamos en cada fila (también usados para ordenar)
    # search: campos por los que se filtra con q (pueden ser relaciones __)
    CONSULTAS = {
        "estatus": {
            "titulo": "Consulta - Estatus",
            "model": estatu,
            "columns": ["ID", "Nombre"],
            "fields": ["id_estatu", "nombre"],
            "search": ["nombre"],
        },
        "carreras": {
            "titulo": "Consulta - Carreras",
            "model": Carrera,
            "columns": ["ID", "Nombre", "Descripción"],
            "fields": ["id_carrera", "nombre", "descripcion"],
            "search": ["nombre", "descripcion"],
        },
        "menciones": {
            "titulo": "Consulta - Menciones",
            "model": Mencion,
            "columns": ["ID", "Carrera", "Nombre", "Descripción"],
            "fields": ["id_mencion", "id_carrera__nombre", "nombre", "descripcion"],
            "search": ["id_carrera__nombre", "nombre", "descripcion"],
        },
        "tipos-materia": {
            "titulo": "Consulta - Tipos de Materia",
            "model": Tipo_Materia,
            "columns": ["ID", "Nombre"],
            "fields": ["id_tipo_materia", "nombre"],
            "search": ["nombre"],
        },
        "asignaturas": {
            "titulo": "Consulta - Asignaturas",
            "model": Asignatura,
            "columns": ["ID", "Código", "Mención", "Tipo Materia", "Nombre", "UC"],
            "fields": [
                "id_asignatura",
                "codigo",
                "id_mencion__nombre",
                "id_tipo_materia__nombre",
                "nombre",
                "unidades_credito",
            ],
            "search": [
                "codigo",
                "nombre",
                "id_mencion__nombre",
                "id_tipo_materia__nombre",
            ],
        },
        "periodos": {
            "titulo": "Consulta - Períodos Académicos",
            "model": Periodo_Academico,
            "columns": ["ID", "Nombre", "Inicio", "Fin", "Estatus"],
            "fields": ["id_periodo", "nombre", "fecha_inicio", "fecha_fin", "id_estatu__nombre"],
            "search": ["nombre", "id_estatu__nombre"],
        },
        "tipos-contrato": {
            "titulo": "Consulta - Tipos de Contrato",
            "model": Tipo_Contrato,
            "columns": ["ID", "Nombre", "Descripción"],
            "fields": ["id_tipo_Contrato", "nombre", "descripcion"],
            "search": ["nombre", "descripcion"],
        },
        "pisos": {
            "titulo": "Consulta - Pisos",
            "model": Piso,
            "columns": ["ID", "Nombre"],
            "fields": ["id_piso", "nombre"],
            "search": ["nombre"],
        },
        "aulas": {
            "titulo": "Consulta - Aulas",
            "model": aula,
            "columns": ["ID", "Piso", "Nombre", "Capacidad", "Estatus"],
            "fields": ["id_aula", "id_piso__nombre", "nombre", "capacidad", "estatus"],
            "search": ["id_piso__nombre", "nombre"],
        },
    }

    if clave not in CONSULTAS:
        messages.error(request, "Componente no válido para consulta.")
        return redirect(reverse("gestion_administrativa:consulta", args=["estatus"]))

    conf = CONSULTAS[clave]
    model = conf["model"]
    titulo = conf["titulo"]
    columnas = conf["columns"]
    fields = conf["fields"]
    search_fields = conf["search"]

    # Construye columnas clicables: label + campo real para ordenar
    columnas_click = []
    for label, field in zip(columnas, fields):
        columnas_click.append({"label": label, "orden": field})

    # Por si algún componente tuviera más labels que fields (no debería), los dejamos sin orden
    if len(columnas) > len(fields):
        for label in columnas[len(fields):]:
            columnas_click.append({"label": label, "orden": ""})


    # ===========================
    # 2) Params GET
    # ===========================
    q = (request.GET.get("q") or "").strip()
    orden = (request.GET.get("orden") or (fields[0] if fields else "id")).strip()
    direccion = (request.GET.get("dir") or "desc").strip().lower()
    page = request.GET.get("page", "1")

    # ===========================
    # 3) Query base + optimizaciones de FK
    # ===========================
    qs = model.objects.all()

    # select_related si hay campos __ (FK)
    fk_roots = {f.split("__", 1)[0] for f in fields + search_fields if "__" in f}
    if fk_roots:
        qs = qs.select_related(*fk_roots)

    # ===========================
    # 4) Filtro (q) sobre campos configurados
    # ===========================
    if q:
        cond = Q()
        for sf in search_fields:
            cond |= Q(**{f"{sf}__icontains": q})
        qs = qs.filter(cond)

    # ===========================
    # 5) Orden seguro (solo campos permitidos)
    # ===========================
    ordenables = []
    for f in fields:
        # Para ordenar en ORM, solo permitimos los mismos fields (incluye __)
        ordenables.append(f)

    if orden not in ordenables:
        orden = fields[0] if fields else "pk"

    if direccion == "asc":
        qs = qs.order_by(orden)
    else:
        qs = qs.order_by(f"-{orden}")

    # ===========================
    # 6) Paginación robusta (evita EmptyPage/min_page)
    # ===========================
    paginator = Paginator(qs, 15)
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        # Si piden page < 1 -> 1; si piden page > max -> última
        try:
            page_int = int(page)
        except Exception:
            page_int = 1
        if page_int < 1:
            page_obj = paginator.page(1)
        else:
            page_obj = paginator.page(paginator.num_pages)

    # ===========================
    # 7) Preparar filas para el template
    # ===========================
    filas = []
    for obj in page_obj.object_list:
        celdas = []
        for f in fields:
            # Soporta relaciones __
            value = obj
            for part in f.split("__"):
                value = getattr(value, part, None)
                if value is None:
                    break
            celdas.append(value)
        filas.append({"obj": obj, "celdas": celdas})

    context = {
        "titulo": titulo,
        "clave": clave,
        "columnas": columnas_click,  # <-- antes era columnas
        "filas": filas,
        "page_obj": page_obj,
        "ordenables": ordenables,
        "q_actual": q,
        "orden_actual": orden,
        "dir_actual": direccion,
    }

    return render(request, "gestion_administrativa/consulta_base.html", context)
