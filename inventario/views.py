from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Case, When
import qrcode
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
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
        if not request.user.is_authenticated:
            return redirect(f"/auth/login/?next={request.path}")
            
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
                reportado_por=request.user,
                resuelta=False
            )
            messages.success(request, "¡Incidencia reportada con éxito! Los organizadores la atenderán.")
            return redirect('inventario:detalle_item', item_uuid=item.uuid)
            
    return render(request, 'inventario/detalle_item.html', {
        'item': item,
        'incidencias_activas': incidencias_activas,
        'incidencias_resueltas': incidencias_resueltas,
    })

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

@login_required(login_url='/auth/login/')
def incidencias_activas_view(request):
    """
    Panel de incidencias activas en el evento.
    Solo accesible para administradores (rol ADMIN).
    """
    if request.user.rol != 'ADMIN':
        messages.error(request, "Acceso denegado. Solo administradores pueden ver este panel.")
        return redirect('index')
        
    if request.method == 'POST':
        incidencia_id = request.POST.get('incidencia_id')
        comentario = request.POST.get('comentarios_resolucion', '').strip()
        incidencia = get_object_or_404(Incidencia, id=incidencia_id)
        
        incidencia.resuelta = True
        incidencia.comentarios_resolucion = comentario
        incidencia.fecha_resolucion = timezone.now()
        incidencia.save()
        
        from usuarios.models import LogActividad
        LogActividad.objects.create(
            usuario=request.user,
            tipo='resolucion_incidencia',
            descripcion=f"Incidencia '{incidencia.titulo}' (ID: {incidencia.id}) en ítem '{incidencia.item.nombre}' resuelta. Comentario: {comentario}",
            ip=get_client_ip(request)
        )
        
        messages.success(request, f"La incidencia '{incidencia.titulo}' ha sido marcada como resuelta.")
        return redirect('inventario:incidencias_activas')
        
    # Ordenar por prioridad (alta -> 0, media -> 1, baja -> 2)
    incidencias = Incidencia.objects.filter(resuelta=False).order_by(
        Case(
            When(prioridad='alta', then=0),
            When(prioridad='media', then=1),
            When(prioridad='baja', then=2),
            default=3
        ),
        '-fecha_reporte'
    ).select_related('item__stand_asignado', 'reportado_por')
    
    return render(request, 'inventario/incidencias_activas.html', {
        'incidencias': incidencias
    })

@login_required(login_url='/auth/login/')
def generar_qr_view(request, item_id):
    """
    Genera un archivo de imagen PNG con el código QR para un elemento de inventario.
    Solo accesible para el rol ADMIN.
    """
    if request.user.rol != 'ADMIN':
        return HttpResponse("Acceso denegado", status=403)
        
    item = get_object_or_404(ItemInventario, id=item_id)
    url = request.build_absolute_uri(item.url_qr)
    
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    response = HttpResponse(content_type="image/png")
    img.save(response, "PNG")
    return response

@login_required(login_url='/auth/login/')
def generar_qr_lote_pdf_view(request):
    """
    Genera un archivo PDF con todos los códigos QR del inventario en una cuadrícula.
    Solo accesible para el rol ADMIN.
    """
    if request.user.rol != 'ADMIN':
        return HttpResponse("Acceso denegado", status=403)
        
    items = ItemInventario.objects.all().order_by('nombre').select_related('stand_asignado')
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="qr_codes_lote.pdf"'
    
    doc = SimpleDocTemplate(
        response, pagesize=letter,
        rightMargin=36, leftMargin=36,
        topMargin=36, bottomMargin=36
    )
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        alignment=1,
        spaceAfter=15
    )
    item_label_style = ParagraphStyle(
        'ItemLabelStyle',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        alignment=1
    )
    
    story.append(Paragraph("Códigos QR de Inventario - ConEvent", title_style))
    story.append(Spacer(1, 10))
    
    data = []
    row = []
    
    for item in items:
        url = request.build_absolute_uri(item.url_qr)
        
        qr = qrcode.QRCode(version=1, box_size=3, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        buf = BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        
        from reportlab.platypus import Image as RLImage
        rl_img = RLImage(buf, width=110, height=110)
        
        stand_num = item.stand_asignado.numero if item.stand_asignado else "Sin stand"
        label_text = f"<b>{item.nombre}</b><br/>Stand: {stand_num}<br/><font size='5'>{item.uuid}</font>"
        label_p = Paragraph(label_text, item_label_style)
        
        cell_table = Table([[rl_img], [label_p]], colWidths=[120])
        cell_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 1),
            ('TOPPADDING', (0,0), (-1,-1), 1),
        ]))
        
        row.append(cell_table)
        
        if len(row) == 4:
            data.append(row)
            row = []
            
    if row:
        while len(row) < 4:
            row.append("")
        data.append(row)
        
    if data:
        t = Table(data, colWidths=[135, 135, 135, 135])
        t.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(t)
    else:
        story.append(Paragraph("No hay ítems registrados en el inventario.", styles['Normal']))
        
    doc.build(story)
    return response


@login_required(login_url='/auth/login/')
def gestionar_inventario_view(request):
    from espacios.models import Stand
    if request.user.rol != 'ADMIN':
        messages.error(request, "Acceso denegado. Solo administradores pueden ver este panel.")
        return redirect('index')
        
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        estado = request.POST.get('estado', 'bueno').strip()
        stand_id = request.POST.get('stand_asignado', '').strip()
        
        if not nombre or not estado:
            messages.error(request, "El nombre del mobiliario y el estado son obligatorios.")
        else:
            stand_obj = None
            if stand_id:
                stand_obj = Stand.objects.filter(id=stand_id).first()
                
            ItemInventario.objects.create(
                nombre=nombre,
                descripcion=descripcion,
                estado=estado,
                stand_asignado=stand_obj
            )
            messages.success(request, f"¡Mobiliario '{nombre}' registrado con éxito!")
            return redirect('inventario:gestionar_inventario')

    items = ItemInventario.objects.all().order_by('nombre').select_related('stand_asignado')
    stands = Stand.objects.filter(esta_activo=True).order_by('numero')
    estado_choices = ItemInventario.ESTADO_CHOICES
    
    return render(request, 'inventario/gestionar_inventario.html', {
        'items': items,
        'stands': stands,
        'estado_choices': estado_choices,
    })


@login_required(login_url='/auth/login/')
def cambiar_estado_item_view(request, item_id):
    if request.user.rol != 'ADMIN':
        return HttpResponse("Acceso denegado", status=403)
        
    if request.method == 'POST':
        item = get_object_or_404(ItemInventario, id=item_id)
        nuevo_estado = request.POST.get('estado', '').strip()
        if nuevo_estado in ['bueno', 'regular', 'malo']:
            item.estado = nuevo_estado
            item.save()
            messages.success(request, f"Estatus de '{item.nombre}' cambiado a: {item.get_estado_display()}.")
        else:
            messages.error(request, "Estatus no válido.")
            
    return redirect('inventario:gestionar_inventario')

