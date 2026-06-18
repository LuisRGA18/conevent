from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from usuarios.api_views import (
    UserMeView, ProyectoViewSet, CarreraViewSet,
    UsuarioViewSet, CriterioEvaluacionViewSet, EvaluacionViewSet
)
from espacios.api_views import StandViewSet, AsignacionStandViewSet
from inventario.api_views import ItemInventarioViewSet, IncidenciaViewSet
from reportes.api_views import DashboardReportView, ExportCalificacionesCSVView

router = DefaultRouter()
router.register(r'proyectos', ProyectoViewSet, basename='proyecto')
router.register(r'carreras', CarreraViewSet, basename='carrera')
router.register(r'usuarios', UsuarioViewSet, basename='usuario')
router.register(r'criterios', CriterioEvaluacionViewSet, basename='criterio')
router.register(r'evaluaciones', EvaluacionViewSet, basename='evaluacion')
router.register(r'stands', StandViewSet, basename='stand')
router.register(r'asignaciones-stands', AsignacionStandViewSet, basename='asignacionstand')
router.register(r'inventario', ItemInventarioViewSet, basename='iteminventario')
router.register(r'incidencias', IncidenciaViewSet, basename='incidencia')

urlpatterns = [
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/me/', UserMeView.as_view(), name='user_me'),
    path('reportes/dashboard/', DashboardReportView.as_view(), name='reportes_dashboard'),
    path('reportes/exportar/calificaciones/', ExportCalificacionesCSVView.as_view(), name='reportes_exportar_calificaciones'),
    path('', include(router.urls)),
]
