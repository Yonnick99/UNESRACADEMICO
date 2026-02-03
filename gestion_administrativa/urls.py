# gestion_administrativa/urls.py
from django.urls import path
from . import views, views_persona

app_name = "gestion_administrativa"

urlpatterns = [

    
    # =========================
    # Gestion PERSONa
    # =========================

    path("personas/", views_persona.persona_list_create, name="persona"),
    path("personas/<int:pk>/editar/", views_persona.persona_update, name="persona_editar"),
    path("personas/<int:pk>/eliminar/", views_persona.persona_delete, name="persona_eliminar"),
    
    # =========================
    # CONSULTA GENERAL
    # =========================
    
    path("consulta/<str:clave>/", views.consulta_list, name="consulta"),
    
    # =========================
    # PISOS
    # =========================
    path("pisos/", views.piso_list, name="piso"),
    path("pisos/<int:pk>/editar/", views.piso_update, name="piso_editar"),
    path("pisos/<int:pk>/eliminar/", views.piso_delete, name="piso_eliminar"),

    # =========================
    # AULAS
    # =========================
    path("aulas/", views.aula_list, name="aula"),
    path("aulas/<int:pk>/editar/", views.aula_update, name="aula_editar"),
    path("aulas/<int:pk>/eliminar/", views.aula_delete, name="aula_eliminar"),

    # =========================
    # ESTATUS
    # =========================
    path("estatus/", views.estatu_list, name="estatu"),
    path("estatus/<int:pk>/editar/", views.estatu_update, name="estatu_editar"),
    path("estatus/<int:pk>/eliminar/", views.estatu_delete, name="estatu_eliminar"),

    # =========================
    # CARRERAS
    # =========================
    path("carreras/", views.carrera_list, name="carrera"),
    path("carreras/<int:pk>/editar/", views.carrera_update, name="carrera_editar"),
    path("carreras/<int:pk>/eliminar/", views.carrera_delete, name="carrera_eliminar"),

    # =========================
    # MENCIONES
    # =========================
    path("menciones/", views.mencion_list, name="mencion"),
    path("menciones/<int:pk>/editar/", views.mencion_update, name="mencion_editar"),
    path("menciones/<int:pk>/eliminar/", views.mencion_delete, name="mencion_eliminar"),

    # =========================
    # ASIGNATURAS
    # =========================
    path("asignaturas/", views.asignatura_list, name="asignatura"),
    path("asignaturas/<int:pk>/editar/", views.asignatura_update, name="asignatura_editar"),
    path("asignaturas/<int:pk>/eliminar/", views.asignatura_delete, name="asignatura_eliminar"),

    # =========================
    # PERÍODOS ACADÉMICOS
    # =========================
    path("periodos/", views.periodo_list, name="periodo"),
    path("periodos/<int:pk>/editar/", views.periodo_update, name="periodo_editar"),
    path("periodos/<int:pk>/eliminar/", views.periodo_delete, name="periodo_eliminar"),

    # =========================
    # TIPOS DE MATERIA
    # =========================
    path("tipos-materia/", views.tipo_materia_list, name="tipo_materia"),
    path("tipos-materia/<int:pk>/editar/", views.tipo_materia_update, name="tipo_materia_editar"),
    path("tipos-materia/<int:pk>/eliminar/", views.tipo_materia_delete, name="tipo_materia_eliminar"),

    path("prelaciones/", views.prelaciones_list, name="prelaciones"),
    path("prelaciones/<int:pk>/editar/", views.prelaciones_update, name="prelaciones_editar"),
    path("prelaciones/<int:pk>/eliminar/", views.prelaciones_delete, name="prelaciones_eliminar"),

    # =========================
    # TIPOS DE MATERIA
    # =========================
    path("periodos/", views.periodo_list, name="periodo"),
    path("periodos/<int:pk>/editar/", views.periodo_update, name="periodo_academico_editar"),
    path("periodos/<int:pk>/eliminar/", views.periodo_delete, name="periodo_academico_eliminar"),

    # =========================
    # TIPOS DE CONTRATO
    # =========================
    path("tipos-contrato/", views.tipo_contrato_list, name="tipo_contrato"),
    path("tipos-contrato/<int:pk>/editar/", views.tipo_contrato_update, name="tipo_contrato_editar"),
    path("tipos-contrato/<int:pk>/eliminar/", views.tipo_contrato_delete, name="tipo_contrato_eliminar"),


]
