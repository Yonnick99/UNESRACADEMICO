# profesor/urls.py
from django.urls import path
from . import views

app_name = "profesor"

urlpatterns = [
    # CRUD Facilitador (+ contrato al crear)
    path("facilitadores/", views.facilitador_list_create, name="facilitador"),
    path("facilitadores/<int:pk>/editar/", views.facilitador_update, name="facilitador_editar"),
    path("facilitadores/<int:pk>/eliminar/", views.facilitador_delete, name="facilitador_eliminar"),

    # AJAX buscador por cédula (autocomplete)
     #path("ajax/personas-cedula/", views.ajax_buscar_persona_por_cedula, name="ajax_personas_cedula"),
    path("ajax/personas-cedula/", views.ajax_personas_cedula, name="ajax_personas_cedula"),
    

]
