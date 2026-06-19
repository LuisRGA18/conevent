from django.urls import path
from . import views

app_name = 'espacios'

urlpatterns = [
    path('api/listado/', views.lista_stands_json, name='lista_stands_json'),
    path('mapa/', views.mapa_auditorio_view, name='mapa_auditorio'),
]
