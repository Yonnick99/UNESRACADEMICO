from django.core.exceptions import PermissionDenied

def obtener_persona_desde_request(request):
    """
    Retorna la Persona asociada al usuario autenticado.
    """
    if not hasattr(request.user, "perfil"):
        raise PermissionDenied("El usuario no tiene un perfil asociado.")

    if not request.user.perfil.activo:
        raise PermissionDenied("El perfil del usuario está inactivo.")

    return request.user.perfil.persona
