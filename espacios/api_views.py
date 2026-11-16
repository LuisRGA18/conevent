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
            'asignacion__proyecto__creado_por'
        ).prefetch_related(
            'asignacion__proyecto__evaluadores'
        )
    
    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsAdminUserRole()]

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def mapa(self, request):
        evento_id = request.session.get('evento_activo_id')
        from usuarios.models import Evento
        from django.shortcuts import get_object_or_404

        if not evento_id:
            evento = Evento.objects.filter(estatus='activo').first() or Evento.objects.first()
            if not evento:
                import datetime
                from espacios.models import Recinto, Planta
                recinto, _ = Recinto.objects.get_or_create(pk=1, defaults={'nombre': 'Auditorio UTEQ'})
                if not recinto.plantas.exists():
                    Planta.objects.create(recinto=recinto, nombre='Planta Única', nivel=0, filas=10, columnas=7)
                evento, _ = Evento.objects.get_or_create(
                    pk=1,
                    defaults={
                        'nombre': 'Evento Auditorio',
                        'estatus': 'activo',
                        'recinto': recinto,
                        'fecha_inicio': datetime.date.today(),
                        'fecha_fin': datetime.date.today()
                    }
                )
        else:
            evento = get_object_or_404(Evento, pk=evento_id)
        
        recinto = evento.recinto
        plantas = recinto.plantas.prefetch_related(
            'stands__asignacionstand_set__proyecto__carrera',
            'stands__asignacionstand_set__proyecto__creado_por',
            'stands__asignacionstand_set__proyecto__evaluadores'
        ).all()
        
        resultado = []
        for planta in plantas:
            stands_data = []
            for stand in planta.stands.filter(esta_activo=True):
                asignacion = stand.asignacionstand_set.filter(activa=True).first()
                proy_data = None
                if asignacion and asignacion.proyecto:
                    proy = asignacion.proyecto
                    evaluadores_list = [ev.get_full_name() or ev.username for ev in proy.evaluadores.all()]
                    eval_str = ", ".join(evaluadores_list) if evaluadores_list else "No asignado aún"
                    creador_nombre = proy.creado_por.get_full_name() or proy.creado_por.username if proy.creado_por else "Desconocido"
                    proy_data = {
                        'id': proy.id,
                        'titulo': proy.titulo,
                        'categoria': proy.categoria,
                        'carrera_clave': proy.carrera.clave if proy.carrera else 'S/C',
                        'carrera_nombre': proy.carrera.nombre if proy.carrera else 'Sin Carrera',
                        'lider_nombre': creador_nombre,
                        'evaluador_nombre': eval_str,
                        'evaluadores': evaluadores_list,
                    }
                stands_data.append({
                    'id': stand.pk,
                    'numero': stand.numero,
                    'zona': stand.zona,
                    'pos_fila': stand.pos_fila,
                    'pos_col': stand.pos_col,
                    'proyecto': proy_data,
                    'proyecto_asignado': proy_data,
                })
            resultado.append({
                'planta_id': planta.pk,
                'planta_nombre': planta.nombre,
                'nivel': planta.nivel,
                'filas': planta.filas,
                'columnas': planta.columnas,
                'stands': stands_data
            })
        
        return Response(resultado)

class AsignacionStandViewSet(viewsets.ModelViewSet):
    queryset = AsignacionStand.objects.all()
    serializer_class = AsignacionStandSerializer
    
    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsAdminUserRole()]
