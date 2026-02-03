# profesor/models.py
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.db.models import Q, F

class Facilitador(models.Model):
    id_facilitador = models.AutoField(primary_key=True)

    # Persona permanece en gestion_administrativa
    id_persona = models.ForeignKey(
        "gestion_administrativa.Persona",
        on_delete=models.RESTRICT,
        db_column="id_persona",
        related_name="facilitadores",
    )

    # Estatu permanece en gestion_administrativa
    id_estatu = models.ForeignKey(
        "gestion_administrativa.estatu",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="id_estatu",
        related_name="facilitadores",
    )
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateField(default=timezone.now, verbose_name="Fecha de Registro")
    fecha_fin = models.DateField(null=True, blank=True)
    class Meta:
        db_table = "Facilitador"
        permissions = [
            ("ver_secciones", "Puede ver sus secciones/ofertas asignadas"),
            ("cargar_notas", "Puede cargar notas"),
            ("solicitar_cambio_nota", "Puede solicitar cambio de nota"),
            ("seleccionar_asignaturas", "Puede seleccionar asignaturas a dictar"),
            ("gestionar_disponibilidad", "Puede registrar disponibilidad (día/hora)"),
            ("ver_lista_participantes", "Puede ver e imprimir lista de participantes por materia"),
        ]

    def __str__(self):
        return f"Facilitador #{self.id_facilitador}"


class Facilitador_has_Contrato(models.Model):
    id_facilitador_contrato = models.BigAutoField(primary_key=True)

    id_facilitador = models.ForeignKey(
        "profesor.Facilitador",
        on_delete=models.RESTRICT,
        db_column="id_facilitador",             
        related_name="contratos",
    )

    # Tipo_Contrato permanece en gestion_administrativa
    id_contrato = models.ForeignKey(
        "gestion_administrativa.Tipo_Contrato",
        on_delete=models.RESTRICT,
        db_column="id_tipo_Contrato",
        related_name="facilitadores_contrato",
    )

    id_estatu = models.ForeignKey(
        "gestion_administrativa.estatu",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="id_estatu",
        related_name="facilitador_contratos",
    )

    horas_academicas = models.IntegerField(null=True, blank=True)
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "Facilitador_has_Contrato"
        constraints = [
            models.UniqueConstraint(
                fields=["id_facilitador", "id_contrato", "fecha_inicio"],
                name="uq_phc",
            )
        ]

    def __str__(self):
        return f"{self.id_facilitador_id} - {self.id_contrato_id} ({self.fecha_inicio})"


class Asignaturas_has_Facilitador(models.Model):
    id_asignaturas_has_Facilitador = models.AutoField(primary_key=True)

    # Asignatura permanece en gestion_administrativa
    id_asignatura = models.ForeignKey(
        "gestion_administrativa.Asignatura",
        on_delete=models.RESTRICT,
        db_column="id_asignatura",
        related_name="facilitadores_asignados",
    )

    id_facilitador = models.ForeignKey(
        "profesor.Facilitador",
        on_delete=models.RESTRICT,
        db_column="id_facilitador",
        related_name="asignaturas_asignadas",
    )

    cupos = models.IntegerField(default=30, validators=[MinValueValidator(1)])
    presencial = models.BooleanField(default=True)

    class Meta:
        db_table = "Asignaturas_has_Facilitador"

    def __str__(self):
        return f"{self.id_asignatura_id} - {self.id_facilitador_id}"


class FacilitadorDisponibilidad(models.Model):
    id = models.BigAutoField(primary_key=True)

    id_facilitador = models.OneToOneField(
        "profesor.Facilitador",
        on_delete=models.RESTRICT,
        db_column="id_facilitador",
        related_name="disponibilidad",
    )

    horas_lunes = models.PositiveIntegerField(default=0)
    horas_martes = models.PositiveIntegerField(default=0)
    horas_miercoles = models.PositiveIntegerField(default=0)
    horas_jueves = models.PositiveIntegerField(default=0)
    horas_viernes = models.PositiveIntegerField(default=0)

    # ✅ NUEVO
    horas_sabado = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "facilitador_disponibilidad"

    def __str__(self):
        return f"Disponibilidad Facilitador {self.id_facilitador.id}"