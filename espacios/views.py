from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.management import call_command
from django.http import HttpResponse
from .models import Stand

@login_required(login_url='/auth/login/')
def mapa_auditorio_view(request):
    """
    Vista que renderiza el mapa interactivo del auditorio.
    """
    return render(request, 'espacios/mapa_auditorio.html')

@login_required(login_url='/auth/login/')
def gestionar_stands_view(request):
    if request.user.rol != 'ADMIN':
        messages.error(request, "Acceso denegado. Solo administradores pueden ver este panel.")
        return redirect('index')
        
    if request.method == 'POST':
        numero = request.POST.get('numero', '').strip()
        zona = request.POST.get('zona', '').strip()
        pos_fila = request.POST.get('pos_fila', '').strip()
        pos_col = request.POST.get('pos_col', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        
        if not numero or not zona or not pos_fila or not pos_col:
            messages.error(request, "Todos los campos con (*) son obligatorios.")
        elif Stand.objects.filter(numero=numero).exists():
            messages.error(request, f"Ya existe un stand con el número {numero}.")
        else:
            try:
                Stand.objects.create(
                    numero=numero,
                    zona=zona,
                    pos_fila=int(pos_fila),
                    pos_col=int(pos_col),
                    descripcion=descripcion,
                    esta_activo=True
                )
                messages.success(request, f"¡Stand {numero} creado con éxito!")
                return redirect('espacios:gestionar_stands')
            except ValueError:
                messages.error(request, "Fila y Columna deben ser números enteros positivos.")

    stands = Stand.objects.all().order_by('zona', 'numero').select_related('asignacion__proyecto')
    zona_choices = Stand.ZONA_CHOICES
    
    return render(request, 'espacios/gestionar_stands.html', {
        'stands': stands,
        'zona_choices': zona_choices,
    })

@login_required(login_url='/auth/login/')
def toggle_stand_view(request, stand_id):
    if request.user.rol != 'ADMIN':
        return HttpResponse("Acceso denegado", status=403)
        
    stand = get_object_or_404(Stand, id=stand_id)
    stand.esta_activo = not stand.esta_activo
    stand.save()
    status_str = "activado" if stand.esta_activo else "desactivado"
    messages.success(request, f"El stand {stand.numero} ha sido {status_str} correctamente.")
    return redirect('espacios:gestionar_stands')

@login_required(login_url='/auth/login/')
def asignar_stands_automatico_view(request):
    if request.user.rol != 'ADMIN':
        return HttpResponse("Acceso denegado", status=403)
        
    if request.method == 'POST':
        try:
            call_command('asignar_stands')
            messages.success(request, "¡Algoritmo de asignación automática contigua ejecutado con éxito!")
        except Exception as e:
            messages.error(request, f"Error al ejecutar la asignación: {str(e)}")
            
    return redirect('espacios:gestionar_stands')
