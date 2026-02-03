from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from seguridad import views as seguridad_views
#from gestion_administrativa import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path("login/", seguridad_views.login_view, name="login"),
    path("login/menu/", seguridad_views.menu_rol, name="menu_rol"),
    #path("logout/", seguridad_views.logout_view, name="logout"),
    #path("logout/", seguridad_views.logout_view, name="logout"),
    path("", lambda request: redirect("login")),
    path('seguridad/', include('seguridad.urls')),
    path('participante/', include('participante.urls')),
    path('facilitador/', include('profesor.urls')),
    path('gestion_administrativa/', include('gestion_administrativa.urls')),


]
