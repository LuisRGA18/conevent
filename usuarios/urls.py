from django.urls import path
from . import views

urlpatterns = [
    # ── Autenticación ──────────────────────────
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('registro/', views.registro_view, name='registro'),
    path('verificar-2fa/', views.verificar_2fa_view, name='verificar_2fa'),
    path('activar-cuenta/', views.activar_cuenta_view, name='activar_cuenta'),

    # ── Alumno ─────────────────────────────────
    path('mi-proyecto/', views.panel_alumno_view, name='mi_proyecto'),
    path('mi-proyecto/<int:pk>/editar/', views.editar_proyecto_view, name='editar_proyecto'),
    path('proyecto/registrar/', views.registrar_proyecto_view, name='registrar_proyecto'),
    path('proyecto/eliminar/<int:pk>/', views.eliminar_proyecto_view, name='eliminar_proyecto'),
    # 🟢 NUEVA RUTA AGREGADA:
    path('mis-calificaciones/', views.ver_calificacion_view, name='ver_calificacion'),

    # ── Evaluador ──────────────────────────────
    path('mis-evaluaciones/', views.proyectos_asignados_view, name='proyectos_asignados'),
    path('mis-evaluaciones/<int:pk>/evaluar/', views.evaluar_proyecto_view, name='evaluar_proyecto'),

    # ── Administrador ──────────────────────────
    path('panel-admin/', views.panel_admin_view, name='panel_admin'),
    path('panel-admin/estatus/<int:pk>/', views.cambiar_estatus_proyecto_view, name='cambiar_estatus_proyecto'),
    path('panel-admin/asignar/<int:pk>/', views.asignar_evaluador_view, name='asignar_evaluador'),
    path('panel-admin/comentario/<int:pk>/', views.guardar_comentario_admin_view, name='guardar_comentario_admin'),
]