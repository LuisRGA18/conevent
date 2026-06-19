from django.urls import path
from . import views

app_name = 'reportes'

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('exportar/calificaciones/pdf/', views.exportar_calificaciones_pdf_view, name='exportar_calificaciones_pdf'),
]
