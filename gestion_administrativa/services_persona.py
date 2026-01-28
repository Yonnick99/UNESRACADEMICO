# gestion_administrativa/services_persona.py
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.crypto import get_random_string
from seguridad.models import PerfilUsuario

User = get_user_model()

def _generar_username(nombre: str, apellido: str, cedula: int) -> str:
    # primera letra nombre + primera letra apellido + cedula
    n = (nombre or "").strip().lower()
    a = (apellido or "").strip().lower()
    return f"{(n[0] if n else 'x')}{(a[0] if a else 'x')}{cedula}"

def _username_disponible(base: str) -> str:
    username = base
    i = 1
    while User.objects.filter(username=username).exists():
        i += 1
        username = f"{base}_{i}"
    return username

@transaction.atomic
def crear_user_y_perfil_desde_persona(persona):
    if hasattr(persona, "perfil_usuario"):
        return persona.perfil_usuario.user, persona.perfil_usuario

    base = _generar_username(persona.nombre, persona.apellido, persona.cedula)
    username = _username_disponible(base)

    temp_password = str(persona.cedula)

    user = User.objects.create_user(
        username=username,
        email=(persona.correo or ""),
        password=temp_password,
        first_name=persona.nombre,
        last_name=persona.apellido,
    )

    perfil = PerfilUsuario.objects.create(
        user=user,
        persona=persona,
        activo=True,
    )
    return user, perfil
