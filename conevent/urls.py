from django.contrib import admin
from django.urls import path, include
from usuarios import views as usuarios_views

urlpatterns = [
    path('admin/', admin.site.urls),
    # Conectamos las urls de la app usuarios
    path('auth/', include('usuarios.urls')),
    # Ruta temporal para el index/dashboard cuando inicias sesión con éxito
    path('', usuarios_views.index_view, name='index'),
]