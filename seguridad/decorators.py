from functools import wraps
from django.core.exceptions import PermissionDenied
from seguridad.utils import obtener_persona_desde_request
from seguridad.rbac import persona_tiene_rol, persona_tiene_alguno


def requiere_rol(nombre_rol):
    """
    Requiere un rol específico.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            persona = obtener_persona_desde_request(request)

            if not persona_tiene_rol(persona, nombre_rol):
                raise PermissionDenied(f"Se requiere el rol: {nombre_rol}")

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def requiere_algun_rol(roles):
    """
    Requiere al menos uno de los roles indicados.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            persona = obtener_persona_desde_request(request)

            if not persona_tiene_alguno(persona, roles):
                raise PermissionDenied(
                    f"Se requiere alguno de los roles: {', '.join(roles)}"
                )

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
