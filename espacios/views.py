from django.shortcuts import render
from django.http import JsonResponse
from .models import Stand

def lista_stands_json(request):
    """
    Retorna la lista de stands y sus asignaciones actuales en formato JSON.
    Útil para consumirse por el frontend o por APIs.
    """
    stands = Stand.objects.filter(esta_activo=True)
    datos = []
    for stand in stands:
        proyecto_info = None
        if hasattr(stand, 'asignacion'):
            p = stand.asignacion.proyecto
            proyecto_info = {
                'id': p.id,
                'titulo': p.titulo,
                'carrera': p.carrera.nombre if p.carrera else "Sin carrera",
                'categoria': p.get_categoria_display(),
                'creado_por': p.creado_por.get_full_name() or p.creado_por.username
            }
        datos.append({
            'id': stand.id,
            'numero': stand.numero,
            'zona': stand.zona,
            'zona_display': stand.get_zona_display(),
            'capacidad': stand.capacidad_proyectos,
            'proyecto': proyecto_info
        })
    return JsonResponse({'stands': datos}, safe=False)
