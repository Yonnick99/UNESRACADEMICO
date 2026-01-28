from django.urls import path
from . import views

app_name = "seguridad"

urlpatterns = [
    path("roles/permisos/", views.roles_permisos, name="roles_permisos"),
    path("usuarios/roles/", views.usuarios_roles, name="usuarios_roles"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("inicio/", views.inicio_view, name="inicio"),
    path("home/", views.home, name="home"),
    # AJAX buscador por cédula (Persona)
    path("ajax/personas-cedula/", views.ajax_personas_cedula, name="ajax_personas_cedula"),
]
