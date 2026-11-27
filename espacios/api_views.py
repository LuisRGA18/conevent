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
        from usuarios.models import Evento
        from espacios.models import Recinto, Planta
        from django.shortcuts import get_object_or_404
        import datetime

        evento_id = request.GET.get('evento') or request.session.get('evento_activo_id')
        recinto_id = request.GET.get('recinto')

        recinto = None
        evento = None

        if recinto_id:
            try:
                recinto = Recinto.objects.get(pk=recinto_id)
            except (Recinto.DoesNotExist, ValueError):
                pass

        if not recinto and evento_id:
            try:
                evento = Evento.objects.select_related('recinto').get(pk=evento_id)
                recinto = evento.recinto
            except (Evento.DoesNotExist, ValueError):
                pass

        if not recinto:
            evento = Evento.objects.filter(estatus__in=['PUBLICADO', 'activo']).select_related('recinto').first() or Evento.objects.select_related('recinto').first()
            if evento and evento.recinto:
                recinto = evento.recinto
            else:
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

        plantas = recinto.plantas.prefetch_related(
            'stands__asignacionstand_set__proyecto__carrera',
            'stands__asignacionstand_set__proyecto__creado_por',
            'stands__asignacionstand_set__proyecto__evaluadores'
        ).order_by('nivel', 'id').all()
        
        resultado = []
        for planta in plantas:
            stands_data = []
            for stand in planta.stands.filter(esta_activo=True).order_by('pos_fila', 'pos_col', 'numero'):
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
                'recinto_id': recinto.pk,
                'recinto_nombre': recinto.nombre,
                'planta_id': planta.pk,
                'planta_nombre': planta.nombre,
                'nivel': planta.nivel,
                'filas': planta.filas,
                'columnas': planta.columnas,
                'geometria': planta.descripcion,
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
