from seguridad.models import PersonaRol

def obtener_roles_persona(persona):
    """
    Retorna una lista de nombres de roles activos de la persona.
    """
    return list(
        PersonaRol.objects.filter(
            id_persona=persona,
            activo=True
        ).select_related("id_rol")
         .values_list("id_rol__nombre", flat=True)
    )


def persona_tiene_rol(persona, nombre_rol):
    """
    Verifica si la persona tiene un rol activo específico.
    """
    return PersonaRol.objects.filter(
        id_persona=persona,
        id_rol__nombre=nombre_rol,
        activo=True
    ).exists()


def persona_tiene_alguno(persona, roles):
    """
    roles: iterable de nombres de rol
    """
    return PersonaRol.objects.filter(
        id_persona=persona,
        id_rol__nombre__in=roles,
        activo=True
    ).exists()
