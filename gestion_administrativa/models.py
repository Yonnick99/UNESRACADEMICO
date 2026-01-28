# models.py
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q, F


class Carrera (models.Model):
    id_carrera = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=120)
    descripcion = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = "Carrera"

    def __str__(self):
        return f"{self.nombre}"

class Mencion(models.Model):
    id_mencion = models.AutoField(primary_key=True,)
    id_carrera = models.ForeignKey(
        Carrera,
        on_delete=models.RESTRICT,
        db_column="id_carrera",
        related_name="Mencion_set",
        
    )
    nombre = models.CharField(max_length=45)
    descripcion = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = "Mencion"

    def __str__(self):
        return f"{self.id_carrera.nombre} - {self.nombre} "

class estatu(models.Model):
    id_estatu = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=45, unique=True)

    class Meta:
        db_table = "estatu"
        permissions = [
            ("ver_componentes", "Puede ver componentes (Gestión Administrativa)"),
            ("crear_componentes", "Puede crear componentes (Gestión Administrativa)"),
            ("editar_componentes", "Puede editar componentes (Gestión Administrativa)"),
            ("eliminar_componentes", "Puede eliminar componentes (Gestión Administrativa)"),
        ]
        
    def __str__(self):
        return f"{self.nombre} (ID: {self.id_estatu})"

class Tipo_Materia(models.Model):
    id_tipo_materia = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=45, unique=True)

    class Meta:
        db_table = "Tipo_Materia"

    def __str__(self):
        return f"{self.nombre}"

class Asignatura(models.Model):
    id_asignatura = models.AutoField(primary_key=True)
    id_mencion = models.ForeignKey(
        Mencion,
        on_delete=models.RESTRICT,
        db_column="id_mencion",
        related_name="Asignatura_set",
    )
    id_tipo_materia = models.ForeignKey(
        Tipo_Materia,
        on_delete=models.RESTRICT,
        db_column="id_tipo_materia",
        related_name="Asignatura_set",
    )
    codigo = models.CharField(max_length=20, unique=True, null=True, blank=True)
    nombre = models.CharField(max_length=120)
    unidades_credito = models.IntegerField(validators=[MinValueValidator(1)])

    class Meta:
        db_table = "Asignatura"

class Persona(models.Model):
    SEXO_FEMENINO = "F"
    SEXO_MASCULINO = "M"
    SEXO_INDEFINIDO = "I"

    SEXO_CHOICES = [
        (SEXO_FEMENINO, "FEMENINO"),
        (SEXO_MASCULINO, "MASCULINO"),
        (SEXO_INDEFINIDO, "INDEFINIDO"),
    ]

    id_persona = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=255)
    apellido = models.CharField(max_length=255)
    cedula = models.IntegerField(unique=True)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    direccion = models.CharField(max_length=255, null=True, blank=True)
    telefono = models.CharField(max_length=20, null=True, blank=True)
    correo = models.EmailField(max_length=255, unique=True, null=True, blank=True)
    sexo = models.CharField(max_length=1, choices=SEXO_CHOICES, default=SEXO_INDEFINIDO,)
    fecha_ingreso = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "Persona"

class Tipo_Contrato(models.Model):
    id_tipo_Contrato = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=45, unique=True)
    descripcion = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = "Tipo_Contrato"

class Piso(models.Model):
    id_piso = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=45)

    class Meta:
        db_table = "Piso"

class aula(models.Model):
    id_aula = models.AutoField(primary_key=True)
    id_piso = models.ForeignKey(
        Piso,
        on_delete=models.RESTRICT,
        db_column="id_piso",
        related_name="aula_set",
    )
    nombre = models.CharField(max_length=45)
    capacidad = models.IntegerField(validators=[MinValueValidator(1)])
    estatus = models.BooleanField(default=True)

    class Meta:
        db_table = "aula"
        constraints = [
            models.UniqueConstraint(fields=["id_piso", "nombre"], name="uq_aula")
        ]

class Periodo_Academico(models.Model):
    id_periodo = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=45, unique=True)
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)
    id_estatu = models.ForeignKey(
        estatu,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="id_estatu",
        related_name="Periodo_Academico_set",
    )

    class Meta:
        db_table = "Periodo_Academico"

class Temp_Asignaturas_has_Facilitador_has_aula(models.Model):
    id_asignaturas_has_Facilitador_has_aula = models.AutoField(primary_key=True)

    id_asignaturas_has_facilitador = models.ForeignKey(
        'profesor.Asignaturas_has_Facilitador',
        on_delete=models.RESTRICT,
        db_column="id_asignaturas_has_facilitador",
        related_name="Temp_ofertas_set",
    )
    id_facilitador = models.ForeignKey(
        'profesor.Facilitador',
        on_delete=models.RESTRICT,
        db_column="id_facilitador",
        related_name="Temp_ofertas_set",
    )
    id_aula = models.ForeignKey(
        aula,
        on_delete=models.RESTRICT,
        db_column="id_aula",
        related_name="Temp_ofertas_set",
    )
    horario_inicio = models.DateTimeField()
    horario_fin = models.DateTimeField()
    id_periodo = models.ForeignKey(
        Periodo_Academico,
        on_delete=models.RESTRICT,
        db_column="id_periodo",
        related_name="Temp_ofertas_set",
    )
    seccion = models.CharField(max_length=20)

    class Meta:
        db_table = "Temp_Asignaturas_has_Facilitador_has_aula"
        constraints = [
            models.CheckConstraint(
                condition=Q(horario_fin__gt=F("horario_inicio")),
                name="ck_horario_temp",
            ),
            models.UniqueConstraint(
                fields=["id_asignaturas_has_facilitador", "id_periodo", "seccion"],
                name="uq_oferta_seccion",
            ),
        ]
        indexes = [
            models.Index(fields=["id_periodo"], name="idx_temp_periodo"),
            models.Index(
                fields=["id_asignaturas_has_facilitador"], name="idx_temp_asigprof"
            ),
        ]

    # IMPORTANTE:
    # Los constraints Postgres:
    #  - excl_aula_horario_periodo (EXCLUDE USING gist ... tsrange &&)
    #  - excl_facilitador_horario_periodo
    # deben crearse vía migración RunSQL (Django no lo modela nativamente).

class Prelaciones(models.Model):
    id_prelacion = models.AutoField(primary_key=True)
    id_asignatura = models.ForeignKey(
        Asignatura,
        on_delete=models.CASCADE,
        db_column="id_asignatura",
        related_name="Prelaciones_de_set",
    )
    id_asignatura_antecesora = models.ForeignKey(
        Asignatura,
        on_delete=models.RESTRICT,
        db_column="id_asignatura_antecesora",
        related_name="Prelaciones_antecesora_set",
    )

    class Meta:
        db_table = "Prelaciones"
        constraints = [
            models.UniqueConstraint(fields=["id_asignatura"], name="uq_prel_unica"),
            models.CheckConstraint(
                condition=~Q(id_asignatura=F("id_asignatura_antecesora")),
                name="ck_no_ciclo",
            ),
        ]



#class Estudiante(models.Model):
#    id_estudiante = models.AutoField(primary_key=True)
#    id_persona = models.ForeignKey(
#        Persona,
#        on_delete=models.RESTRICT,
#        db_column="id_persona",
#        related_name="Estudiante_set",
#    )
#    id_carrera = models.ForeignKey(
#        Carrera,
#        on_delete=models.SET_NULL,
#        null=True,
#        blank=True,
#        db_column="id_carrera",
#        related_name="Estudiante_set",
#    )
#    unidades_cred_aprobadas = models.IntegerField(default=0)
#    unidades_cred_cursadas = models.IntegerField(default=0)
#    unidades_cred_reprobadas = models.IntegerField(default=0)
#    id_estatu = models.ForeignKey(
#        estatu,
#        on_delete=models.SET_NULL,
#        null=True,
#        blank=True,
#        db_column="id_estatu",
#        related_name="Estudiante_set",
#    )
#    fecha_fin = models.DateField(null=True, blank=True)
#
#    class Meta:
#        db_table = "Estudiante"


#class Materia_Inscrita(models.Model):
#    id_materia_inscrita = models.BigAutoField(primary_key=True)
#
#    id_estudiante = models.ForeignKey(
#        Estudiante,
#        on_delete=models.RESTRICT,
#        db_column="id_estudiante",
#        related_name="Materia_Inscrita_set",
#    )
#    id_asignatura = models.ForeignKey(
#        Asignatura,
#        on_delete=models.RESTRICT,
#        db_column="id_asignatura",
#        related_name="Materia_Inscrita_set",
#    )
#    id_periodo = models.ForeignKey(
#        Periodo_Academico,
#        on_delete=models.RESTRICT,
#        db_column="id_periodo",
#        related_name="Materia_Inscrita_set",
#    )
#
#    seccion = models.CharField(max_length=20, null=True, blank=True)
#    horario_inicio = models.DateTimeField(null=True, blank=True)
#    horario_fin = models.DateTimeField(null=True, blank=True)
#
#    nota = models.DecimalField(
#        max_digits=3,
#        decimal_places=2,
#        null=True,
#        blank=True,
#        validators=[MinValueValidator(1.00), MaxValueValidator(5.00)],
#    )
#
#    class Meta:
#        db_table = "Materia_Inscrita"
#        constraints = [
#            models.UniqueConstraint(
#                fields=["id_estudiante", "id_asignatura", "id_periodo"],
#                name="uq_mi_est_asig_per",
#            ),
#            models.CheckConstraint(
#                condition=Q(nota__isnull=True) | (Q(nota__gte=1.00) & Q(nota__lte=5.00)),
#                name="ck_nota_rango",
#            ),
#            models.CheckConstraint(
#                condition=(
#                    Q(horario_inicio__isnull=True)
#                    | Q(horario_fin__isnull=True)
#                    | Q(horario_fin__gt=F("horario_inicio"))
#                ),
#                name="ck_horario_mi",
#            ),
#        ]
#        indexes = [
#            models.Index(fields=["id_estudiante", "id_periodo"], name="idx_mi_estudiante_periodo"),
#            models.Index(fields=["id_periodo"], name="idx_mi_periodo"),
#        ]


#class Estudiantes_has_Carreras(models.Model):
#    id = models.AutoField(primary_key=True)
#    id_estudiante = models.ForeignKey(
#        Estudiante,
#        on_delete=models.RESTRICT,
#        db_column="id_estudiante",
#        related_name="Estudiantes_has_Carreras_set",
#    )
#    id_carrera = models.ForeignKey(
#        Carrera,
#        on_delete=models.RESTRICT,
#        db_column="id_carrera",
#        related_name="Estudiantes_has_Carreras_set",
#    )
#    id_estatu = models.ForeignKey(
#        estatu,
#        on_delete=models.SET_NULL,
#        null=True,
#        blank=True,
#        db_column="id_estatu",
#        related_name="Estudiantes_has_Carreras_set",
#    )
#    fecha_inicio = models.DateField(null=True, blank=True)
#    fecha_fin = models.DateField(null=True, blank=True)
#    activo = models.BooleanField(default=True)
#
#    class Meta:
#        db_table = "Estudiantes_has_Carreras"
#        constraints = [
#            models.UniqueConstraint(
#                fields=["id_estudiante", "id_carrera"],
#                name="uq_estudiante_carrera",
#            )
#        ]










#class Facilitador(models.Model):
#    id_facilitador = models.AutoField(primary_key=True)
#    id_persona = models.ForeignKey(
#        Persona,
#        on_delete=models.RESTRICT,
#        db_column="id_persona",
#        related_name="Facilitador_set",
#    )
#    id_estatu = models.ForeignKey(
#        estatu,
#        on_delete=models.SET_NULL,
#        null=True,
#        blank=True,
#        db_column="id_estatu",
#        related_name="Facilitador_set",
#    )
#
#    class Meta:
#        db_table = "Facilitador"


#class Facilitador_has_Contrato(models.Model):
#    id_facilitador_contrato = models.BigAutoField(primary_key=True)
#    id_facilitador = models.ForeignKey(
#        Facilitador,
#        on_delete=models.RESTRICT,
#        db_column="id_facilitador",
#        related_name="Facilitador_has_Contrato_set",
#    )
#    id_contrato = models.ForeignKey(
#        Tipo_Contrato,
#        on_delete=models.RESTRICT,
#        db_column="id_tipo_Contrato",
#        related_name="Facilitador_has_Contrato_set",
#    )
#    id_estatu = models.ForeignKey(
#        estatu,
#        on_delete=models.SET_NULL,
#        null=True,
#        blank=True,
#        db_column="id_estatu",
#        related_name="Facilitador_has_Contrato_set",
#    )
#    horas_academicas = models.IntegerField(null=True, blank=True)
#    fecha_inicio = models.DateField(null=True, blank=True)
#    fecha_fin = models.DateField(null=True, blank=True)
#
#    class Meta:
#        db_table = "Facilitador_has_Contrato"
#        constraints = [
#            models.UniqueConstraint(
#                fields=["id_facilitador", "id_contrato", "fecha_inicio"],
#                name="uq_phc",
#            )
#        ]

#class Asignaturas_has_Facilitador(models.Model):
#    id_asignaturas_has_Facilitador = models.AutoField(primary_key=True)
#    id_asignatura = models.ForeignKey(
#        Asignatura,
#        on_delete=models.RESTRICT,
#        db_column="id_asignatura",
#        related_name="Asignaturas_has_Facilitador_set",
#    )
#    id_facilitador = models.ForeignKey(
#        Facilitador,
#        on_delete=models.RESTRICT,
#        db_column="id_facilitador",
#        related_name="Asignaturas_has_Facilitador_set",
#    )
#    cupos = models.IntegerField(default=30, validators=[MinValueValidator(1)])
#    presencial = models.BooleanField(default=True)
#
#    class Meta:
#        db_table = "Asignaturas_has_Facilitador"



