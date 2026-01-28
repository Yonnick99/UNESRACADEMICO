# participante/urls.py
from django.urls import path
from . import views

app_name = "participante"

urlpatterns = [
    path("participante/", views.estudiante_list_create, name="estudiante"),
    path("participante/<int:pk>/editar/", views.estudiante_update, name="estudiante_editar"),
    path("participante/<int:pk>/eliminar/", views.estudiante_delete, name="estudiante_eliminar"),
    path("personas/buscar-cedula/", views.persona_buscar_por_cedula, name="persona_buscar_cedula"),
    path("ajax/menciones/<int:carrera_id>/", views.menciones_por_carrera, name="ajax_menciones_por_carrera"),

]
