from django.urls import path
from . import views

app_name = 'espacios'

urlpatterns = [
    path('mapa/', views.mapa_auditorio_view, name='mapa_auditorio'),
    path('gestionar/', views.gestionar_stands_view, name='gestionar_stands'),
    path('gestionar/toggle/<int:stand_id>/', views.toggle_stand_view, name='toggle_stand'),
    path('gestionar/asignar-automatico/', views.asignar_stands_automatico_view, name='asignar_stands_automatico'),
    path('stands/<int:stand_pk>/asignar/', views.asignar_stand_manual_view, name='asignar_stand_manual'),
]
