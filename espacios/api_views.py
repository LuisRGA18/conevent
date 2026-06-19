from rest_framework import viewsets, permissions
from rest_framework.permissions import BasePermission
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Stand, AsignacionStand
from .serializers import StandSerializer, AsignacionStandSerializer

class IsAdminUserRole(BasePermission):
    """
    Permiso personalizado que permite el acceso de escritura solo a administradores.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.rol == 'ADMIN'

class StandViewSet(viewsets.ModelViewSet):
    serializer_class = StandSerializer
    
    def get_queryset(self):
        return Stand.objects.all().select_related(
            'asignacion__proyecto__carrera',
            'asignacion__proyecto__evaluador_asignado',
            'asignacion__proyecto__creado_por'
        )
    
    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsAdminUserRole()]

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def mapa(self, request):
        stands = self.get_queryset().filter(esta_activo=True)
        data = []
        for s in stands:
            stand_data = {
                'id': s.id,
                'numero': s.numero,
                'zona': s.zona,
                'zona_display': s.get_zona_display(),
                'pos_fila': s.pos_fila,
                'pos_col': s.pos_col,
                'esta_activo': s.esta_activo,
                'proyecto_asignado': None
            }
            
            asignacion = None
            try:
                asignacion = s.asignacion
            except Stand.asignacion.RelatedObjectDoesNotExist:
                pass
                
            if asignacion:
                proyecto = asignacion.proyecto
                evaluador_nombre = ""
                if proyecto.evaluador_asignado:
                    evaluador_nombre = proyecto.evaluador_asignado.get_full_name() or proyecto.evaluador_asignado.username
                
                creador_nombre = proyecto.creado_por.get_full_name() or proyecto.creado_por.username
                
                stand_data['proyecto_asignado'] = {
                    'id': proyecto.id,
                    'titulo': proyecto.titulo,
                    'categoria': proyecto.categoria,
                    'carrera_clave': proyecto.carrera.clave if proyecto.carrera else 'S/C',
                    'carrera_nombre': proyecto.carrera.nombre if proyecto.carrera else 'Sin Carrera',
                    'lider_nombre': creador_nombre,
                    'evaluador_nombre': evaluador_nombre,
                }
            data.append(stand_data)
        return Response(data)

class AsignacionStandViewSet(viewsets.ModelViewSet):
    queryset = AsignacionStand.objects.all()
    serializer_class = AsignacionStandSerializer
    
    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsAdminUserRole()]
