from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import ItemInventario, Incidencia

def detalle_item_view(request, item_uuid):
    """
    Vista de detalle para un elemento de inventario escaneado por QR.
    Permite visualizar el estado e incidencias, además de reportar nuevos problemas.
    """
    item = get_object_or_404(ItemInventario, uuid=item_uuid)
    incidencias_activas = item.incidencias.filter(resuelta=False)
    incidencias_resueltas = item.incidencias.filter(resuelta=True)
    
    if request.method == 'POST':
        titulo = request.POST.get('titulo', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        prioridad = request.POST.get('prioridad', 'media')
        
        if not titulo or not descripcion:
            messages.error(request, "Por favor, completa el título y descripción del problema.")
        else:
            Incidencia.objects.create(
                item=item,
                titulo=titulo,
                descripcion=descripcion,
                prioridad=prioridad,
                reportado_por=request.user if request.user.is_authenticated else None
            )
            messages.success(request, "¡Incidencia reportada con éxito! Los organizadores la atenderán.")
            return redirect('inventario:detalle_item', item_uuid=item.uuid)
            
    return render(request, 'inventario/detalle_item.html', {
        'item': item,
        'incidencias_activas': incidencias_activas,
        'incidencias_resueltas': incidencias_resueltas,
    })
