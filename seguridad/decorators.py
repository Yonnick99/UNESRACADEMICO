# seguridad/decorators.py
from functools import wraps

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse


def requiere_rol(rol_requerido: str):
    """
    Decorador para controlar acceso por ROL ACTIVO (guardado en sesión).

    Reglas:
    - Debe estar autenticado (si no, redirige a login)
    - Debe existir request.session["rol_activo"]
    - El rol activo debe coincidir con rol_requerido
    - (Extra) El usuario debe pertenecer a ese grupo (por seguridad)
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # 1) autenticación
            if not request.user.is_authenticated:
                return redirect("login")

            # 2) rol activo en sesión
            rol_activo = request.session.get("rol_activo")
            if not rol_activo:
                messages.warning(request, "Debes seleccionar un rol para continuar.")
                # tu menú está en /seguridad/login/menu
                return redirect(reverse("seguridad:menu_rol"))

            # 3) comparar rol activo con requerido
            if rol_activo != rol_requerido:
                # Si intentan entrar a otra ruta sin cambiar rol
                messages.error(request, f"Acceso denegado. Rol requerido: {rol_requerido}.")
                raise PermissionDenied("Rol activo no autorizado para esta vista.")

            # 4) el usuario debe pertenecer al grupo requerido (defensa extra)
            if not request.user.groups.filter(name=rol_requerido).exists():
                messages.error(request, "Acceso denegado. Tu usuario no posee el rol requerido.")
                raise PermissionDenied("El usuario no pertenece al rol requerido.")

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
