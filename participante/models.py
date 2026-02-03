# participante/models.py
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q, F
from django.utils import timezone

class Estudiante(models.Model):
    id_estudiante = models.AutoField(primary_key=True)
    id_persona = models.ForeignKey(
        "gestion_administrativa.Persona",
        on_delete=models.RESTRICT,
        db_column="id_persona",
        related_name="estudiantes",
    )
    
    id_carrera = models.ForeignKey(
        "gestion_administrativa.Carrera",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="id_carrera",
        related_name="estudiantes_compat",
    )

    id_mencion = models.ForeignKey(
        "gestion_administrativa.Mencion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="id_mencion",
        related_name="estudiantes",
    )
    unidades_cred_aprobadas = models.IntegerField(default=0)
    unidades_cred_cursadas = models.IntegerField(default=0)
    unidades_cred_reprobadas = models.IntegerField(default=0)
    unidades_cred_reglamentaria = models.IntegerField(default=175)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateField(default=timezone.now, verbose_name="Fecha de Registro")
    fecha_fin = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "Estudiante"
        permissions = [
            ("inscribir", "Puede realizar inscripción"),
            ("ver_horario", "Puede ver su horario"),
            ("ver_record", "Puede ver su récord académico"),
            ("ver_constancia", "Puede generar/descargar constancia de estudio"),
            ("ver_promedio", "Puede consultar promedio"),
        ]
    constraints = [
        models.UniqueConstraint(
            fields=["id_persona", "id_mencion"],
            condition=Q(activo=True, fecha_fin__isnull=True),
            name="uq_estudiante_persona_mencion_activa",
        )
    ]

    def __str__(self):
        return f"Estudiante #{self.id_estudiante}"


class Estudiantes_has_Carreras(models.Model):
    id = models.AutoField(primary_key=True)

    id_estudiante = models.ForeignKey(
        "participante.Estudiante",
        on_delete=models.RESTRICT,
        db_column="id_estudiante",
        related_name="carreras",
    )

    id_carrera = models.ForeignKey(
        "gestion_administrativa.Carrera",
        on_delete=models.RESTRICT,
        db_column="id_carrera",
        related_name="estudiantes_por_carrera",
    )
    id_mencion = models.ForeignKey(
        "gestion_administrativa.Mencion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="id_mencion",
        related_name="estudiante_carreras",
    )

    id_estatu = models.ForeignKey(
        "gestion_administrativa.estatu",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="id_estatu",
        related_name="estudiante_carreras",
    )

    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "Estudiantes_has_Carreras"
        constraints = [
            models.UniqueConstraint(
                fields=["id_estudiante", "id_carrera"],
                name="uq_estudiante_carrera",
            )
        ]

    def __str__(self):
        return f"{self.id_estudiante_id} - {self.id_carrera_id}"


class Materia_Inscrita(models.Model):
    id_materia_inscrita = models.BigAutoField(primary_key=True)

    id_estudiante = models.ForeignKey(
        "participante.Estudiante",
        on_delete=models.RESTRICT,
        db_column="id_estudiante",
        related_name="inscripciones",
    )

    id_asignatura = models.ForeignKey(
        "gestion_administrativa.Asignatura",
        on_delete=models.RESTRICT,
        db_column="id_asignatura",
        related_name="inscripciones",
    )

    id_periodo = models.ForeignKey(
        "gestion_administrativa.Periodo_Academico",
        on_delete=models.RESTRICT,
        db_column="id_periodo",
        related_name="inscripciones",
    )

    seccion = models.CharField(max_length=20, null=True, blank=True)
    horario_inicio = models.DateTimeField(null=True, blank=True)
    horario_fin = models.DateTimeField(null=True, blank=True)

    nota = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(1.00), MaxValueValidator(5.00)],
    )

    class Meta:
        db_table = "Materia_Inscrita"
        constraints = [
            models.UniqueConstraint(
                fields=["id_estudiante", "id_asignatura", "id_periodo"],
                name="uq_mi_est_asig_per",
            ),
            models.CheckConstraint(
                condition=Q(nota__isnull=True)
                | (Q(nota__gte=1.00) & Q(nota__lte=5.00)),
                name="ck_nota_rango",
            ),
            models.CheckConstraint(
                condition=(
                    Q(horario_inicio__isnull=True)
                    | Q(horario_fin__isnull=True)
                    | Q(horario_fin__gt=F("horario_inicio"))
                ),
                name="ck_horario_mi",
            ),
        ]
        indexes = [
            models.Index(fields=["id_estudiante", "id_periodo"], name="idx_mi_estudiante_periodo"),
            models.Index(fields=["id_periodo"], name="idx_mi_periodo"),
        ]

    def __str__(self):
        return f"{self.id_estudiante_id} - {self.id_asignatura_id} - {self.id_periodo_id}"


