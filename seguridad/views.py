# seguridad/views.py
from collections import defaultdict
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.http import JsonResponse
from django.urls.exceptions import NoReverseMatch
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import capfirst
from django.views.decorators.http import require_GET
from django.utils.http import url_has_allowed_host_and_scheme
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from gestion_administrativa.models import Persona
from seguridad.models import PerfilUsuario


# ==========================================================
# AJAX: buscar personas por cédula (mín. 5 dígitos)
# ==========================================================
@require_GET
def ajax_personas_cedula(request):
    q = (request.GET.get("q") or "").strip()

    if not q.isdigit() or len(q) < 5:
        return JsonResponse({"resultados": []})

    personas = (
        Persona.objects.filter(cedula__icontains=q)
        .order_by("cedula")[:10]
    )

    data = [{
        "id_persona": p.id_persona,
        "nombre": p.nombre,
        "apellido": p.apellido,
        "cedula": p.cedula,
    } for p in personas]

    return JsonResponse({"resultados": data})


# ==========================================================
# Labels amigables (opción 1)
# ==========================================================
ACCION_ES = {
    "add": "Crear",
    "change": "Editar",
    "delete": "Eliminar",
    "view": "Ver",
}

# Nombres amigables para cabeceras (opcional)
APP_ES = {
    "gestion_administrativa": "Gestión Administrativa",
    "participante": "Participantes",
    "profesor": "Profesores",
    "seguridad": "Seguridad",
}

# Override manual opcional para custom permissions
# key = "app_label.codename"
CUSTOM_LABELS = {
    "gestion_administrativa.ver_componentes": "Ver componentes",
    "gestion_administrativa.crear_componentes": "Crear componentes",
    "gestion_administrativa.editar_componentes": "Editar componentes",
    "gestion_administrativa.eliminar_componentes": "Eliminar componentes",

    "participante.inscribir": "Inscribir participante",
    "participante.ver_horario": "Ver horario",
    "participante.ver_record": "Ver récord académico",
    "participante.ver_constancia": "Generar constancia",
    "participante.ver_promedio": "Consultar promedio",

    "profesor.ver_secciones": "Ver secciones asignadas",
    "profesor.cargar_notas": "Cargar notas",
    "profesor.solicitar_cambio_nota": "Solicitar cambio de nota",
    "profesor.seleccionar_asignaturas": "Seleccionar asignaturas",
    "profesor.gestionar_disponibilidad": "Gestionar disponibilidad",
    "profesor.ver_lista_participantes": "Ver/imprimir lista de participantes",

    "seguridad.gestionar_usuarios": "Gestionar usuarios",
    "seguridad.asignar_roles": "Asignar roles",
    "seguridad.asignar_admin": "Asignar rol administrativo",
    "seguridad.ver_auditoria": "Ver auditoría",
    "seguridad.exportar_auditoria": "Exportar auditoría",
    "seguridad.ver_logs_acceso": "Ver logs de acceso",
}

CUSTOM_HELP = {
    "gestion_administrativa.editar_componentes": "Permite modificar registros en Gestión Administrativa.",
    "profesor.ver_lista_participantes": "Permite ver e imprimir la lista de participantes por materia.",
}


def _title_model(ct: ContentType) -> str:
    """Nombre amigable del modelo."""
    try:
        model_cls = ct.model_class()
        if model_cls and getattr(model_cls._meta, "verbose_name", None):
            return str(model_cls._meta.verbose_name).title()
    except Exception:
        pass
    return ct.model.replace("_", " ").title()


def _perm_label_and_help(perm: Permission) -> tuple[str, str]:
    """
    Construye label + help para UI.
    - add/change/delete/view -> "Crear/Editar/Eliminar/Ver <Modelo>"
    - custom -> overrides o fallback al name
    """
    app_label = perm.content_type.app_label
    codename = perm.codename
    key = f"{app_label}.{codename}"

    # 1) override manual
    if key in CUSTOM_LABELS:
        label = CUSTOM_LABELS[key]
    else:
        # 2) estándar Django: add_x / change_x / delete_x / view_x
        parts = codename.split("_", 1)
        if len(parts) == 2 and parts[0] in ACCION_ES:
            accion = ACCION_ES[parts[0]]
            modelo = _title_model(perm.content_type)
            label = f"{accion} {modelo}"
        else:
            # 3) fallback: name de django
            label = (perm.name or key).strip()
            if label.lower().startswith("can "):
                label = label[4:].strip()
            label = capfirst(label)

    help_txt = CUSTOM_HELP.get(key)
    if not help_txt:
        app_name = APP_ES.get(app_label, app_label.replace("_", " ").title())
        help_txt = f"Permiso de {app_name} ({key})."

    return label, help_txt


# ==========================================================
# 1) Permisos por Rol (Group -> Permission)
# (ALINEADO con tu HTML roles_permisos.html)
# ==========================================================
def roles_permisos(request):
    roles = Group.objects.all().order_by("name")

    # El HTML usa 'rol' por nombre del grupo (r.name)
    rol_name = (request.GET.get("rol") or request.POST.get("rol") or "").strip()

    rol = None
    if rol_name:
        rol = Group.objects.filter(name=rol_name).first()
    if not rol and roles.exists():
        rol = roles.first()

    # Si no hay roles, render vacío
    if not rol:
        return render(request, "seguridad/roles_permisos.html", {
            "roles": roles,
            "rol": None,
            "perms_por_app": {},
            "rol_perm_ids": set(),
            "perm_meta": {},
            "app_es": APP_ES,
        })

    # POST: guardar permisos del rol
    if request.method == "POST":
        perm_ids = request.POST.getlist("perms")  # lista de IDs Permission
        perm_ids = [int(x) for x in perm_ids if str(x).isdigit()]

        try:
            with transaction.atomic():
                rol.permissions.set(Permission.objects.filter(id__in=perm_ids))
            messages.success(request, f"Permisos actualizados para el rol: {rol.name}.")
        except Exception as e:
            messages.error(request, f"No se pudieron actualizar los permisos: {e}")

        return redirect(f"{request.path}?rol={rol.name}")

    # GET: construir permisos por app para el template
    perms = Permission.objects.select_related("content_type").order_by(
        "content_type__app_label",
        "codename"
    )

    perms_por_app = defaultdict(list)
    perm_meta = {}  # (opcional futuro) por si luego quieres usar label/help distinto

    for p in perms:
        app = p.content_type.app_label

        label, help_txt = _perm_label_and_help(p)

        # IMPORTANTE:
        # Tu HTML usa p.id, p.codename, p.name
        # Entonces le pasamos dicts y dejamos p.name como label amigable
        perms_por_app[app].append({
            "id": p.id,
            "codename": p.codename,
            "name": label,      # <- aquí va traducido/amigable
        })

        perm_meta[p.id] = {
            "label": label,
            "help": help_txt,
            "key": f"{app}.{p.codename}",
        }

    rol_perm_ids = set(rol.permissions.values_list("id", flat=True))

    return render(request, "seguridad/roles_permisos.html", {
        "roles": roles,
        "rol": rol,
        "perms_por_app": dict(perms_por_app),
        "rol_perm_ids": rol_perm_ids,
        "perm_meta": perm_meta,   # no lo usa tu HTML actual, pero queda listo
        "app_es": APP_ES,         # opcional futuro para headers amigables
    })


# ==========================================================
# 2) Usuarios -> Roles (User -> Group)
# ==========================================================
def usuarios_roles(request):
    """
    GET:
      - sin persona_id: muestra pantalla vacía (solo buscador)
      - con persona_id: carga PerfilUsuario -> user y lista roles

    POST:
      - asigna roles (groups) al user asociado a la persona
    """
    roles = Group.objects.all().order_by("name")

    persona_id = (request.GET.get("persona_id") or request.POST.get("persona_id") or "").strip()

    persona = None
    perfil = None
    user = None

    if persona_id:
        try:
            persona = Persona.objects.get(pk=int(persona_id))
        except Exception:
            messages.error(request, "Persona inválida o no encontrada.")
            return render(request, "seguridad/usuarios_roles.html", {
                "roles": roles,
                "persona": None,
                "user": None,
            })

        perfil = PerfilUsuario.objects.filter(persona=persona).select_related("user").first()
        user = perfil.user if perfil and perfil.user_id else None

    if request.method == "POST":
        if not persona:
            messages.error(request, "Debes seleccionar una persona.")
            return redirect(request.path)

        if not user:
            messages.error(request, "Esta persona no tiene usuario asociado (PerfilUsuario → user).")
            return redirect(f"{request.path}?persona_id={persona.id_persona}")

        roles_sel = request.POST.getlist("roles")  # names de Group

        with transaction.atomic():
            grupos = Group.objects.filter(name__in=roles_sel)
            user.groups.set(grupos)

        messages.success(request, f"Roles actualizados para el usuario: {user.username}.")
        return redirect(f"{request.path}?persona_id={persona.id_persona}")

    return render(request, "seguridad/usuarios_roles.html", {
        "roles": roles,
        "persona": persona,
        "user": user,
    })


# (si estabas usando esto en otra parte, lo dejamos)
ROLES_FIJOS = ["Master", "Administrativo", "Profesor", "Participante"]
APPS_PERMITIDAS = ["gestion_administrativa", "participante", "profesor", "seguridad"]

def _roles_queryset():
    return Group.objects.filter(name__in=ROLES_FIJOS).order_by("name")



def _redirect_next_login(request, fallback_url: str):
    nxt = request.GET.get("next") or request.POST.get("next")
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        return redirect(nxt)
    return redirect(fallback_url)


def login_view(request):
    """
    Login con Django auth (username/password).
    - Valida user activo
    - Valida PerfilUsuario activo si existe
    - Redirige a next o a seguridad:inicio
    """
    if request.user.is_authenticated:
        return redirect("seguridad:inicio")

    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        password = (request.POST.get("password") or "").strip()

        if not username or not password:
            messages.error(request, "Debes ingresar usuario y contraseña.")
            return render(request, "seguridad/login.html", {
                "username": username,
            })

        user = authenticate(request, username=username, password=password)

        if user is None:
            messages.error(request, "Credenciales inválidas.")
            return render(request, "seguridad/login.html", {
                "username": username,
            })

        if not user.is_active:
            messages.error(request, "Este usuario está inactivo.")
            return render(request, "seguridad/login.html", {
                "username": username,
            })

        # Validar PerfilUsuario si existe
        perfil = PerfilUsuario.objects.filter(user=user).select_related("persona").first()
        if perfil and not perfil.activo:
            messages.error(request, "El perfil del usuario está inactivo. Contacte al administrador.")
            return render(request, "seguridad/login.html", {
                "username": username,
            })

        login(request, user)
        messages.success(request, "Sesión iniciada correctamente.")

        # 1) si hay next, lo respetamos
        nxt = request.GET.get("next") or request.POST.get("next")
        if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
            return redirect(nxt)

        # 2) si no hay next, redirigir por rol (grupo)
        fallback = reverse("seguridad:inicio")
        return _redirect_by_role(user, fallback)

    # GET
    return render(request, "seguridad/login.html")


def logout_view(request):
    if request.user.is_authenticated:
        logout(request)
        messages.info(request, "Sesión cerrada.")
    return redirect("seguridad:login")


@login_required
def inicio_view(request):
    """
    Landing simple post-login.
    Luego lo puedes convertir en dashboard y/o redirección por grupos.
    """
    # ejemplo: mostrar grupos
    grupos = list(request.user.groups.values_list("name", flat=True))
    return render(request, "seguridad/inicio.html", {
        "grupos": grupos,
    })

# Prioridad de roles (si un usuario tiene varios)
ROLE_PRIORITY = ["Master", "Administrativo", "Profesor", "Participante"]

# A dónde enviar según rol
ROLE_REDIRECTS = {
    "Master": "gestion_administrativa:home",        # <-- ajusta si tu home tiene otro name
    "Administrativo": "gestion_administrativa:home",# <-- ajusta si tu home tiene otro name
    "Profesor": "profesor:facilitador",             # pantalla facilitadores
    "Participante": "participante:estudiante",      # pantalla estudiantes
}

def _safe_reverse(name: str, fallback: str) -> str:
    try:
        return reverse(name)
    except NoReverseMatch:
        return fallback

def _redirect_by_role(user, fallback_url: str):
    """
    Decide el destino por rol según prioridad.
    Si no encuentra ruta válida, cae al fallback_url.
    """
    user_groups = set(user.groups.values_list("name", flat=True))

    for role in ROLE_PRIORITY:
        if role in user_groups:
            route_name = ROLE_REDIRECTS.get(role)
            if route_name:
                return redirect(_safe_reverse(route_name, fallback_url))

    return redirect(fallback_url)


@login_required
def home(request):
    return render(request, "seguridad/home_administrativo.html")