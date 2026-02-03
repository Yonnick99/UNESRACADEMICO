# seguridad/views.py
from collections import defaultdict

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.text import capfirst
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required

from gestion_administrativa.models import Persona
from seguridad.models import PerfilUsuario
from seguridad.decorators import requiere_rol as role_required

from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse

from seguridad.forms import PerfilPersonaUpdateForm, CambioPasswordForm
from participante.models import Estudiante
from profesor.models import Facilitador_has_Contrato, Facilitador

# ==========================================================
# CONFIG: redirecciones por rol (names reales que diste)
# ==========================================================
ROLE_REDIRECTS = {
    "Master": "seguridad:inicio_master",
    "Administrador": "seguridad:inicio_administrativo",
    "Profesor": "seguridad:inicio_profesor",
    "Participante": "seguridad:inicio_participante",
}


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

APP_ES = {
    "gestion_administrativa": "Gestión Administrativa",
    "participante": "Participantes",
    "profesor": "Profesores",
    "seguridad": "Seguridad",
}

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
    Construye label + help para UI:
    - add/change/delete/view -> "Crear/Editar/Eliminar/Ver <Modelo>"
    - custom -> overrides o fallback al name
    """
    app_label = perm.content_type.app_label
    codename = perm.codename
    key = f"{app_label}.{codename}"

    if key in CUSTOM_LABELS:
        label = CUSTOM_LABELS[key]
    else:
        parts = codename.split("_", 1)
        if len(parts) == 2 and parts[0] in ACCION_ES:
            accion = ACCION_ES[parts[0]]
            modelo = _title_model(perm.content_type)
            label = f"{accion} {modelo}"
        else:
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
# ==========================================================
def roles_permisos(request):
    roles = Group.objects.all().order_by("name")
    rol_name = (request.GET.get("rol") or request.POST.get("rol") or "").strip()

    rol = Group.objects.filter(name=rol_name).first() if rol_name else None
    if not rol and roles.exists():
        rol = roles.first()

    if not rol:
        return render(request, "seguridad/roles_permisos.html", {
            "roles": roles,
            "rol": None,
            "perms_por_app": {},
            "rol_perm_ids": set(),
        })

    if request.method == "POST":
        perm_ids = request.POST.getlist("perms")
        perm_ids = [int(x) for x in perm_ids if str(x).isdigit()]

        try:
            with transaction.atomic():
                rol.permissions.set(Permission.objects.filter(id__in=perm_ids))
            messages.success(request, f"Permisos actualizados para el rol: {rol.name}.")
        except Exception as e:
            messages.error(request, f"No se pudieron actualizar los permisos: {e}")

        return redirect(f"{request.path}?rol={rol.name}")

    perms = Permission.objects.select_related("content_type").order_by(
        "content_type__app_label", "codename"
    )

    perms_por_app = defaultdict(list)
    for p in perms:
        app = p.content_type.app_label
        label, _help = _perm_label_and_help(p)
        perms_por_app[app].append({
            "id": p.id,
            "codename": p.codename,
            "name": label,
        })

    rol_perm_ids = set(rol.permissions.values_list("id", flat=True))

    return render(request, "seguridad/roles_permisos.html", {
        "roles": roles,
        "rol": rol,
        "perms_por_app": dict(perms_por_app),
        "rol_perm_ids": rol_perm_ids,
    })


# ==========================================================
# 2) Usuarios -> Roles (User -> Group)
# ==========================================================
def usuarios_roles(request):
    roles = Group.objects.all().order_by("name")

    persona_id = (request.GET.get("persona_id") or request.POST.get("persona_id") or "").strip()

    persona = None
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


# ---------------------------------------------------------------------
# Redirecciones por rol (AJUSTADAS A TUS URLS ACTUALES)
# ---------------------------------------------------------------------
ROLE_REDIRECTS = {
    "Master": "seguridad:inicio_master",
    "Administrador": "seguridad:inicio_administrativo",
    "Profesor": "seguridad:inicio_profesor",
    "Participante": "seguridad:inicio_participante",
}

SESSION_KEY_ROL_ACTIVO = "rol_activo"


def _roles_usuario(user):
    """Lista de nombres de grupos/roles del usuario."""
    return list(user.groups.values_list("name", flat=True))


def _set_rol_activo(request, rol: str):
    """Guarda el rol activo en sesión."""
    request.session[SESSION_KEY_ROL_ACTIVO] = rol
    request.session.modified = True


def _clear_rol_activo(request):
    """Limpia el rol activo de sesión."""
    if SESSION_KEY_ROL_ACTIVO in request.session:
        del request.session[SESSION_KEY_ROL_ACTIVO]
        request.session.modified = True


def _redirect_por_rol(request, rol: str):
    """Redirige al home según rol."""
    destino = ROLE_REDIRECTS.get(rol)
    if not destino:
        return redirect("seguridad:menu_rol")
    return redirect(destino)


# ==========================================================
# Helpers de roles (ROL ACTIVO en sesión)
# ==========================================================

ROL_SESSION_KEY = "rol_activo"

# ✅ Ajusta aquí los nombres reales de tus grupos (si cambiaste "Administrativo" por "Administrador")
ROLE_REDIRECTS = {
    "Master": "seguridad:inicio_master",
    "Administrativo": "seguridad:inicio_administrativo",   # si aún existe
    "Administrador": "seguridad:inicio_administrativo",    # si ya lo cambiaste
    "Profesor": "seguridad:inicio_profesor",
    "Participante": "seguridad:inicio_participante",
}

def _roles_usuario(user):
    # lista de nombres de grupos/roles
    return list(user.groups.values_list("name", flat=True))

def _set_rol_activo(request, rol: str):
    request.session[ROL_SESSION_KEY] = rol

def _clear_rol_activo(request):
    request.session.pop(ROL_SESSION_KEY, None)

def _redirect_por_rol(request, rol: str):
    """
    Redirige a la ruta configurada para el rol.
    Si no existe mapeo, envía al menú para evitar loops.
    """
    destino = ROLE_REDIRECTS.get(rol)
    if not destino:
        messages.error(request, f"No hay ruta configurada para el rol: {rol}.")
        return redirect("seguridad:menu_rol")

    return redirect(destino)


# ==========================================================
# LOGIN
# ==========================================================

def login_view(request):
    """
    Login:
    - Valida credenciales + user activo
    - Valida PerfilUsuario activo (si existe)
    - Respeta ?next si es seguro
    - Si no hay next: decide por roles:
        * 1 rol -> set rol_activo y redirige
        * >1 rol -> menu_rol
        * 0 rol -> warning y logout
    """
    # Si ya está autenticado, no repitas login: decide por roles
    if request.user.is_authenticated:
        roles = _roles_usuario(request.user)

        if len(roles) == 1:
            _set_rol_activo(request, roles[0])
            return _redirect_por_rol(request, roles[0])

        if len(roles) > 1:
            return redirect("seguridad:menu_rol")

        messages.warning(request, "Tu usuario no tiene roles asignados. Contacta al administrador.")
        _clear_rol_activo(request)
        logout(request)
        return redirect("seguridad:login")

    # POST: intentar login
    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        password = (request.POST.get("password") or "").strip()

        if not username or not password:
            messages.error(request, "Debes ingresar usuario y contraseña.")
            return render(request, "seguridad/login.html", {"username": username})

        user = authenticate(request, username=username, password=password)
        if user is None:
            messages.error(request, "Credenciales inválidas.")
            return render(request, "seguridad/login.html", {"username": username})

        if not user.is_active:
            messages.error(request, "Este usuario está inactivo.")
            return render(request, "seguridad/login.html", {"username": username})

        perfil = PerfilUsuario.objects.filter(user=user).select_related("persona").first()
        if perfil and not perfil.activo:
            messages.error(request, "El perfil del usuario está inactivo. Contacte al administrador.")
            return render(request, "seguridad/login.html", {"username": username})

        # OK: login
        login(request, user)
        _clear_rol_activo(request)  # limpiamos por si venía de sesiones viejas

        # 1) next (si existe y es seguro)
        nxt = request.POST.get("next") or request.GET.get("next")
        if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
            return redirect(nxt)

        # 2) sin next: decidir por roles
        roles = _roles_usuario(user)

        if len(roles) == 1:
            _set_rol_activo(request, roles[0])
            return _redirect_por_rol(request, roles[0])

        if len(roles) > 1:
            return redirect("seguridad:menu_rol")

        messages.warning(request, "Tu usuario no tiene roles asignados. Contacta al administrador.")
        _clear_rol_activo(request)
        logout(request)
        return redirect("seguridad:login")

    # GET
    return render(request, "seguridad/login.html")


# ==========================================================
# LOGOUT
# ==========================================================

def logout_view(request):
    _clear_rol_activo(request)
    if request.user.is_authenticated:
        logout(request)
        messages.info(request, "Sesión cerrada.")
    return redirect("seguridad:login")


# ==========================================================
# MENU DE SELECCIÓN DE ROL
# url: /seguridad/login/menu  (según tu urls.py)
# ==========================================================

@login_required
def menu_rol(request):
    roles = _roles_usuario(request.user)

    # Si no tiene roles, lo sacamos
    if len(roles) == 0:
        messages.warning(request, "Tu usuario no tiene roles asignados. Contacta al administrador.")
        _clear_rol_activo(request)
        logout(request)
        return redirect("seguridad:login")

    # Si solo tiene 1 rol, no debería ver el menú
    if len(roles) == 1:
        _set_rol_activo(request, roles[0])
        return _redirect_por_rol(request, roles[0])

    # POST: el usuario eligió rol
    if request.method == "POST":
        rol_sel = (request.POST.get("rol") or "").strip()

        if rol_sel not in roles:
            messages.error(request, "Rol inválido.")
            return redirect("seguridad:menu_rol")

        _set_rol_activo(request, rol_sel)
        return _redirect_por_rol(request, rol_sel)

    # GET: render HTML del menú
    return render(request, "seguridad/menu_rol.html", {"roles": roles})

# ==========================================================
# INICIOS POR ROL (prueba con HttpResponse)
# ==========================================================



@login_required
@role_required("Master")
def home_master(request):
    # Master usa el mismo home que Administrador
    return render(request, "seguridad/home_administrativo.html")


@login_required
@role_required("Administrador")
def home_administrador(request):
    # Administrador usa el mismo home que Master
    return render(request, "seguridad/home_administrativo.html")


@login_required
@role_required("Profesor")
def home_profesor(request):
    return render(request, "seguridad/home_profesor.html")


@login_required
@role_required("Participante")
def home_participante(request):
    return render(request, "seguridad/home_participante.html")

@login_required
def perfil_view(request):
    """
    Perfil:
    - Muestra datos básicos de Persona (solo lectura)
    - Permite editar: telefono, correo, direccion
    - Muestra resumen por tipo:
        * Estudiante: carreras registradas + UC aprobadas/reprobadas/cursadas/faltantes
        * Profesor: contrato activo (si existe)
        * Administrador/Master: roles del usuario
    """
    perfil = getattr(request.user, "perfil_usuario", None)
    if not perfil or not perfil.activo:
        messages.error(request, "No tienes un perfil activo asociado. Contacta al administrador.")
        return redirect("login")

    persona = perfil.persona

    # ---------------------------
    # POST: guardar datos editables
    # ---------------------------
    if request.method == "POST":
        form = PerfilPersonaUpdateForm(request.POST, instance=persona)
        if form.is_valid():
            form.save()
            messages.success(request, "Datos actualizados correctamente.")
            return redirect(reverse("seguridad:perfil"))
        else:
            messages.error(request, "Revisa los campos del formulario.")
    else:
        form = PerfilPersonaUpdateForm(instance=persona)

    # ---------------------------
    # Resumen por "perfiles académicos"
    # (NO depende del rol_activo; es informativo)
    # ---------------------------

    # Estudiantes: puede tener varios registros (por persona)
    estudiantes_qs = (
        Estudiante.objects
        .select_related("id_carrera", "id_mencion")
        .filter(id_persona=persona)
        .order_by("-id_estudiante")
    )

    carreras = []
    resumen_uc = None
    if estudiantes_qs.exists():
        for e in estudiantes_qs:
            carreras.append({
                "carrera": getattr(e.id_carrera, "nombre", "—"),
                "mencion": getattr(e.id_mencion, "nombre", "—"),
                "activo": e.activo if hasattr(e, "activo") else True,
                "fecha_fin": getattr(e, "fecha_fin", None),
            })

        # Tomamos el último registro como referencia de UC (puedes ajustar si quieres sumar)
        e0 = estudiantes_qs.first()
        faltantes = max(0, (e0.unidades_cred_reglamentaria or 0) - (e0.unidades_cred_aprobadas or 0))
        resumen_uc = {
            "aprobadas": e0.unidades_cred_aprobadas,
            "reprobadas": e0.unidades_cred_reprobadas,
            "cursadas": e0.unidades_cred_cursadas,
            "reglamentaria": e0.unidades_cred_reglamentaria,
            "faltantes": faltantes,
        }

    # Profesores: contrato activo del facilitador activo (si existe)
    fac = (
        Facilitador.objects
        .select_related("id_persona")
        .filter(id_persona=persona, activo=True, fecha_fin__isnull=True)
        .order_by("-id_facilitador")
        .first()
    )

    contrato_activo = None
    if fac:
        contrato_activo = (
            Facilitador_has_Contrato.objects
            .select_related("id_contrato", "id_estatu")
            .filter(id_facilitador=fac, fecha_fin__isnull=True)
            .order_by("-fecha_inicio")
            .first()
        )

    # Roles del usuario (para Admin/Master o informativo)
    roles = list(request.user.groups.values_list("name", flat=True))

    context = {
        "persona": persona,
        "form": form,
        "roles": roles,

        "carreras": carreras,
        "resumen_uc": resumen_uc,

        "facilitador": fac,
        "contrato_activo": contrato_activo,
    }
    return render(request, "seguridad/perfil.html", context)


@login_required
def cambiar_password_view(request):
    """
    Cambiar contraseña:
    - POST valida contraseña actual y nueva
    - Guarda contraseña
    - CIERRA SESIÓN y manda a login
    """
    if request.method == "POST":
        form = CambioPasswordForm(request.user, request.POST)
        if form.is_valid():
            new_password = form.cleaned_data["new_password1"]
            request.user.set_password(new_password)
            request.user.save()

            # IMPORTANTE: cerramos sesión como pediste
            from django.contrib.auth import logout
            logout(request)

            messages.success(request, "Contraseña actualizada. Inicia sesión nuevamente.")
            return redirect("login")
        else:
            messages.error(request, "Revisa los datos del cambio de contraseña.")
            return render(request, "seguridad/cambiar_password.html", {"form": form})

    # GET
    form = CambioPasswordForm(request.user)
    return render(request, "seguridad/cambiar_password.html", {"form": form})