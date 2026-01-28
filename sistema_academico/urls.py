from django.contrib import admin
from django.urls import path, include
from seguridad import views as seguridad_views
#from gestion_administrativa import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('seguridad/', include('seguridad.urls')),
    path('participante/', include('participante.urls')),
    path('facilitador/', include('profesor.urls')),
    path("home/GestionAdministrativa/", seguridad_views.home, name="home"),
    path('gestion_administrativa/', include('gestion_administrativa.urls')),
]
