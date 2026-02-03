from django.urls import path
from . import views

app_name = "seguridad"

urlpatterns = [
    path("roles/permisos/", views.roles_permisos, name="roles_permisos"),
    path("usuarios/roles/", views.usuarios_roles, name="usuarios_roles"),   
    path("ajax/personas-cedula/", views.ajax_personas_cedula, name="ajax_personas_cedula"),

    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("login/menu/", views.menu_rol, name="menu_rol"),

    path("inicio/master/", views.home_master, name="inicio_master"),
    path("inicio/administrativo/", views.home_administrador, name="inicio_administrativo"),
    path("inicio/profesor/", views.home_profesor, name="inicio_profesor"),
    path("inicio/participante/", views.home_participante, name="inicio_participante"),
    
    path("perfil/", views.perfil_view, name="perfil"),
    path("perfil/password/", views.cambiar_password_view, name="cambiar_password"),


]

