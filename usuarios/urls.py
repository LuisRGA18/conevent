from django.urls import path
from . import views

urlpatterns = [
    # ── Autenticación ──────────────────────────
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('registro/', views.registro_view, name='registro'),

    # ── Alumno ─────────────────────────────────
    path('mi-proyecto/', views.mi_proyecto_view, name='mi_proyecto'),
    path('mi-proyecto/<int:pk>/editar/', views.editar_proyecto_view, name='editar_proyecto'),

    # ── Evaluador ──────────────────────────────
    path('mis-evaluaciones/', views.proyectos_asignados_view, name='proyectos_asignados'),
    path('mis-evaluaciones/<int:pk>/evaluar/', views.evaluar_proyecto_view, name='evaluar_proyecto'),

    # ── Administrador ──────────────────────────
    path('admin-panel/', views.panel_admin_view, name='panel_admin'),
    path('admin-panel/<int:pk>/asignar/', views.asignar_evaluador_view, name='asignar_evaluador'),
]