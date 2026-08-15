import csv
from django.http import HttpResponse
from django.db.models import Count, Avg
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, BasePermission
from usuarios.models import Usuario, Proyecto, Carrera, Evaluacion
from espacios.models import Stand, AsignacionStand
from inventario.models import Incidencia

class IsAdminOrEvaluador(BasePermission):
    """
    Permiso para asegurar que solo coordinadores/administradores y docentes evaluadores
    puedan acceder a las analíticas e informes consolidados.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.rol in ['ADMIN', 'EVALUADOR']

class DashboardReportView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrEvaluador]
    
    def get(self, request):
        # 1. Métricas generales
        total_usuarios = Usuario.objects.count()
        total_proyectos = Proyecto.objects.count()
        proyectos_evaluados = Proyecto.objects.filter(calificacion__isnull=False).count()
        proyectos_sin_evaluar = Proyecto.objects.filter(calificacion__isnull=True).count()
        total_stands = Stand.objects.count()
        stands_ocupados = AsignacionStand.objects.count()
        stands_libres = Stand.objects.filter(esta_activo=True, asignacion__isnull=True).count()
        total_incidencias = Incidencia.objects.count()
        incidencias_resueltas = Incidencia.objects.filter(resuelta=True).count()
        incidencias_activas = Incidencia.objects.filter(resuelta=False).count()
        
        metricas_generales = {
            'total_usuarios': total_usuarios,
            'total_proyectos': total_proyectos,
            'proyectos_evaluados': proyectos_evaluados,
            'proyectos_sin_evaluar': proyectos_sin_evaluar,
            'total_stands': total_stands,
            'stands_ocupados': stands_ocupados,
            'stands_libres': stands_libres,
            'total_incidencias': total_incidencias,
            'incidencias_resueltas': incidencias_resueltas,
            'incidencias_activas': incidencias_activas,
        }
        
        # 2. Proyectos por categoría
        proyectos_cat = Proyecto.objects.values('categoria').annotate(cantidad=Count('id')).order_by('-cantidad')
        cat_map = dict(Proyecto.CATEGORIA_CHOICES)
        proyectos_por_categoria = [
            {
                'categoria_key': item['categoria'],
                'categoria_nombre': cat_map.get(item['categoria'], item['categoria']),
                'cantidad': item['cantidad']
            }
            for item in proyectos_cat
        ]
        
        # 3. Proyectos por carrera
        proyectos_carr = Proyecto.objects.values('carrera__nombre', 'carrera__clave').annotate(cantidad=Count('id')).order_by('-cantidad')
        proyectos_por_carrera = [
            {
                'carrera_nombre': item['carrera__nombre'] or 'Sin Carrera',
                'carrera_clave': item['carrera__clave'] or 'S/C',
                'cantidad': item['cantidad']
            }
            for item in proyectos_carr
        ]
        
        # 4. Calificación promedio por carrera
        calif_carr = Proyecto.objects.filter(calificacion__isnull=False).values('carrera__nombre', 'carrera__clave').annotate(promedio=Avg('calificacion')).order_by('-promedio')
        calif_promedio_por_carrera = [
            {
                'carrera_nombre': item['carrera__nombre'] or 'Sin Carrera',
                'carrera_clave': item['carrera__clave'] or 'S/C',
                'promedio': round(float(item['promedio']), 2) if item['promedio'] is not None else 0.0
            }
            for item in calif_carr
        ]
        
        # 5. Top 5 Proyectos mejor calificados
        top_proy_qs = Proyecto.objects.filter(calificacion__isnull=False).order_by('-calificacion', 'titulo')[:5]
        top_proyectos = [
            {
                'id': p.id,
                'titulo': p.titulo,
                'carrera_clave': p.carrera.clave if p.carrera else 'S/C',
                'calificacion': float(p.calificacion) if p.calificacion is not None else 0.0
            }
            for p in top_proy_qs
        ]
        
        # 6. Distribución de stands por zona
        stands_qs = Stand.objects.values('zona').annotate(
            total=Count('id'),
            ocupados=Count('asignacion')
        )
        zona_map = dict(Stand.ZONA_CHOICES)
        stands_por_zona = [
            {
                'zona_key': item['zona'],
                'zona_nombre': zona_map.get(item['zona'], item['zona']),
                'total': item['total'],
                'ocupados': item['ocupados'],
                'libres': item['total'] - item['ocupados']
            }
            for item in stands_qs
        ]
        
        # 7. Incidencias de inventario por prioridad (activas)
        inc_qs = Incidencia.objects.filter(resuelta=False).values('prioridad').annotate(cantidad=Count('id'))
        prio_map = dict(Incidencia.PRIORIDAD_CHOICES)
        incidencias_por_prioridad = [
            {
                'prioridad_key': item['prioridad'],
                'prioridad_nombre': prio_map.get(item['prioridad'], item['prioridad']),
                'cantidad': item['cantidad']
            }
            for item in inc_qs
        ]
        
        data = {
            'metricas_generales': metricas_generales,
            'proyectos_por_categoria': proyectos_por_categoria,
            'proyectos_por_carrera': proyectos_por_carrera,
            'calif_promedio_por_carrera': calif_promedio_por_carrera,
            'top_proyectos': top_proyectos,
            'stands_por_zona': stands_por_zona,
            'incidencias_por_prioridad': incidencias_por_prioridad,
        }
        
        return Response(data, status=status.HTTP_200_OK)

class ExportCalificacionesCSVView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrEvaluador]
    
    def get(self, request):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="calificaciones_conevent.csv"'
        
        # Escribir el BOM de UTF-8 para compatibilidad nativa con Excel en español
        response.write('\ufeff'.encode('utf-8'))
        
        writer = csv.writer(response)
        writer.writerow([
            'Código', 'Título del Proyecto', 'Categoría', 'Carrera', 
            'Grupo', 'Líder / Creador', 'Integrantes', 
            'Evaluador Asignado', 'Calificación Final', 'Estatus'
        ])
        
        proyectos = Proyecto.objects.all().select_related('carrera', 'creado_por').prefetch_related('miembros', 'evaluadores')
        
        cat_map = dict(Proyecto.CATEGORIA_CHOICES)
        estatus_map = dict(Proyecto.ESTATUS_CHOICES)
        
        for p in proyectos:
            integrantes_list = [m.nombre_completo for m in p.miembros.all()]
            integrantes_str = "; ".join(integrantes_list)
            
            creador_str = f"{p.creado_por.first_name} {p.creado_por.last_name}" if p.creado_por.first_name else p.creado_por.username
            evaluador_str = "; ".join([f"{ev.first_name} {ev.last_name}" if ev.first_name else ev.username for ev in p.evaluadores.all()])
            
            writer.writerow([
                p.codigo,
                p.titulo,
                cat_map.get(p.categoria, p.categoria),
                p.carrera.nombre if p.carrera else 'Sin Carrera',
                p.grupo,
                creador_str,
                integrantes_str,
                evaluador_str,
                float(p.calificacion) if p.calificacion is not None else 'N/A',
                estatus_map.get(p.estatus, p.estatus)
            ])
            
        return response
