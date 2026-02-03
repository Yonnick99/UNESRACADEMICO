from django.conf import settings
from django.db import models


# ============================================================
# 1) Roles y permisos (BBDD existente)
# ============================================================

class Roles(models.Model):
    id_rol = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=45, unique=True)

    class Meta:
        db_table = "Roles"

    def __str__(self):
        return f"{self.nombre} (ID: {self.id_rol})"


class Permisos(models.Model):
    id_permiso = models.AutoField(primary_key=True)
    codigo = models.CharField(max_length=80, unique=True)
    descripcion = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = "Permisos"

    def __str__(self):
        return self.codigo


class RolesHasPermisos(models.Model):
    id_rol = models.ForeignKey(
        Roles,
        on_delete=models.CASCADE,
        db_column="id_rol",
        related_name="roles_permisos",
    )
    id_permiso = models.ForeignKey(
        Permisos,
        on_delete=models.CASCADE,
        db_column="id_permiso",
        related_name="roles_permisos",
    )

    class Meta:
        db_table = "Roles_has_Permisos"
        constraints = [
            models.UniqueConstraint(fields=["id_rol", "id_permiso"], name="pk_rhp")
        ]

    def __str__(self):
        return f"{self.id_rol_id} -> {self.id_permiso_id}"


# ============================================================
# 2) Asignación de roles a personas (BBDD existente)
# ============================================================

class PersonaHasRoles(models.Model):
    id_persona = models.ForeignKey(
        "gestion_administrativa.Persona",
        on_delete=models.CASCADE,
        db_column="id_persona",
        related_name="roles_asignados",
    )
    id_rol = models.ForeignKey(
        Roles,
        on_delete=models.RESTRICT,
        db_column="id_rol",
        related_name="personas_asignadas",
    )

    activo = models.BooleanField(default=True)
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "Persona_has_Roles"
        constraints = [
            models.UniqueConstraint(fields=["id_persona", "id_rol"], name="pk_phr")
        ]

    def __str__(self):
        return f"{self.id_persona.nombre} - {self.id_rol.nombre} ({'Activo' if self.activo else 'Inactivo'})"


# ============================================================
# 3) Auditoría (BBDD existente)
# ============================================================

class Auditoria(models.Model):
    id_auditoria = models.BigAutoField(primary_key=True)
    id_persona = models.ForeignKey(
        "gestion_administrativa.Persona",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="id_persona",
        related_name="auditorias",
    )
    accion = models.CharField(max_length=80)
    entidad = models.CharField(max_length=80, null=True, blank=True)
    llave = models.CharField(max_length=120, null=True, blank=True)
    valor_anterior = models.TextField(null=True, blank=True)
    valor_nuevo = models.TextField(null=True, blank=True)
    fecha_evento = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "Auditoria"
        indexes = [models.Index(fields=["fecha_evento"], name="idx_audit_fecha")]

    def __str__(self):
        return f"{self.accion} - {self.entidad} ({self.fecha_evento})"


# ============================================================
# 4) Perfil de usuario (TABLA NUEVA – Django la gestiona)
# ============================================================


class PerfilUsuario(models.Model):
    id = models.BigAutoField(primary_key=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_column="user_id",
        related_name="perfil_usuario",
    )
    persona = models.OneToOneField(
        "gestion_administrativa.Persona",
        on_delete=models.CASCADE,
        db_column="persona_id",
        related_name="perfil_usuario",
    )

    class Meta:
        db_table = "perfil_usuario"
        permissions = [
            ("gestionar_usuarios", "Puede gestionar usuarios"),
            ("asignar_roles", "Puede asignar roles"),
            ("asignar_admin", "Puede asignar el rol Administrativo (solo Master)"),
            ("ver_auditoria", "Puede ver auditoría"),
            ("exportar_auditoria", "Puede exportar auditoría"),
            ("ver_logs_acceso", "Puede ver logs de acceso"),
        ]

    def __str__(self):
        return f"PerfilUsuario #{self.id} ({self.user})"
