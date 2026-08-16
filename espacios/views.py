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
        return redirect('index')
        
    if request.method == 'POST':
        from django.core.management import call_command
        from io import StringIO
        
        out = StringIO()
        try:
            call_command('asignar_stands', stdout=out)
            resultado = out.getvalue()
            messages.success(request, f'Asignación completada. {resultado}')
        except Exception as e:
            messages.error(request, f'Error en asignación: {str(e)}')
            
    return redirect('espacios:gestionar_stands')


@login_required(login_url='/auth/login/')
def asignar_stand_manual_view(request, stand_pk):
    from usuarios.models import Proyecto
    from .models import AsignacionStand
    
    if request.user.rol != 'ADMIN':
        return redirect('index')
        
    stand = get_object_or_404(Stand, pk=stand_pk)
    
    if request.method == 'POST':
        proyecto_id = request.POST.get('proyecto_id')
        
        if proyecto_id:
            proyecto = get_object_or_404(Proyecto, pk=proyecto_id)
            mesas = proyecto.mesas_requeridas or 1
            
            # Verificar autorización para 3 mesas
            if mesas == 3 and not proyecto.mesas_autorizadas:
                messages.error(request, 
                    f'El proyecto {proyecto.titulo} solicita 3 mesas pero '
                    f'no tiene autorización del admin.')
                return redirect('espacios:gestionar_stands')
            
            # Liberar stands anteriores del proyecto
            AsignacionStand.objects.filter(
                proyecto=proyecto, activa=True
            ).update(activa=False, stand=None)
            
            # Liberar el stand seleccionado
            AsignacionStand.objects.filter(
                stand=stand, activa=True
            ).update(activa=False, stand=None)
            
            if mesas == 1:
                # Asignar solo este stand
                AsignacionStand.objects.create(
                    stand=stand, proyecto=proyecto, activa=True
                )
                messages.success(request, 
                    f'Stand {stand.numero} asignado a {proyecto.titulo}.')
            else:
                # Para 2 o 3 mesas, asignar stands contiguos desde este
                stands_contiguos = Stand.objects.filter(
                    esta_activo=True,
                    pos_fila=stand.pos_fila,
                    pos_col__gte=stand.pos_col
                ).exclude(
                    asignacion__activa=True
                ).order_by('pos_col')[:mesas]
                
                if stands_contiguos.count() < mesas:
                    messages.error(request,
                        f'No hay {mesas} stands contiguos disponibles desde '
                        f'{stand.numero}. Elige otro stand de inicio.')
                    return redirect('espacios:gestionar_stands')
                
                numeros = []
                for s in stands_contiguos:
                    AsignacionStand.objects.create(
                        stand=s, proyecto=proyecto, activa=True
                    )
                    numeros.append(s.numero)
                
                messages.success(request,
                    f'Stands {", ".join(numeros)} asignados a {proyecto.titulo} '
                    f'({mesas} mesas).')
        else:
            AsignacionStand.objects.filter(stand=stand, activa=True).update(activa=False, stand=None)
            messages.success(request, f'Stand {stand.numero} liberado.')
        
        return redirect('espacios:gestionar_stands')
    
    proyectos_disponibles = Proyecto.objects.exclude(
        asignaciones_stands__activa=True
    ).exclude(estatus='rechazado').order_by('carrera__clave', 'titulo')
    
    asignacion_actual = AsignacionStand.objects.filter(
        stand=stand, activa=True
    ).first()
    
    proyectos_list = list(proyectos_disponibles)
    if asignacion_actual and asignacion_actual.proyecto not in proyectos_list:
        proyectos_list.insert(0, asignacion_actual.proyecto)
    
    return render(request, 'espacios/asignar_stand_manual.html', {
        'stand': stand,
        'proyectos': proyectos_list,
        'asignacion_actual': asignacion_actual,
    })
