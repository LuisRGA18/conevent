import io
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from usuarios.models import Proyecto

@login_required(login_url='/auth/login/')
def dashboard_view(request):
    """
    Renderiza la página del dashboard visual con gráficos y KPIs.
    Solo accesible para docentes (EVALUADOR) y coordinadores (ADMIN).
    """
    if request.user.rol not in ['ADMIN', 'EVALUADOR']:
        messages.error(request, "No tienes permiso para acceder a esta sección.")
        return redirect('index')
    return render(request, 'reportes/dashboard.html')

@login_required(login_url='/auth/login/')
def exportar_calificaciones_pdf_view(request):
    """
    Genera un archivo PDF con la tabla consolidada de calificaciones de proyectos.
    Solo accesible para administradores (ADMIN).
    """
    if request.user.rol != 'ADMIN':
        messages.error(request, "Acceso denegado. Solo administradores pueden exportar calificaciones en PDF.")
        return redirect('index')
        
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="calificaciones_conevent.pdf"'
    
    # Usar hoja horizontal (landscape) para acomodar todas las columnas
    doc = SimpleDocTemplate(
        response, pagesize=landscape(letter),
        rightMargin=36, leftMargin=36,
        topMargin=36, bottomMargin=36
    )
    story = []
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'PDFTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        alignment=1,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=4
    )
    
    subtitle_style = ParagraphStyle(
        'PDFSubTitle',
        parent=styles['Normal'],
        fontSize=10,
        leading=12,
        alignment=1,
        textColor=colors.HexColor('#475569'),
        spaceAfter=15
    )
    
    cell_style = ParagraphStyle(
        'PDFCell',
        parent=styles['Normal'],
        fontSize=7,
        leading=9,
    )
    
    cell_header_style = ParagraphStyle(
        'PDFCellHeader',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        fontName='Helvetica-Bold',
        textColor=colors.white
    )
    
    # Título del Evento
    story.append(Paragraph("CONEVENT — UTEQ", title_style))
    fecha_str = timezone.now().strftime("%d/%m/%Y %H:%M")
    story.append(Paragraph(f"Reporte Oficial de Calificaciones Finales · Generado el: {fecha_str}", subtitle_style))
    story.append(Spacer(1, 10))
    
    # Definición de anchos de columnas (Usable horizontal = 720)
    col_widths = [45, 140, 90, 70, 80, 110, 80, 45, 60]
    
    table_data = []
    # Fila de cabecera
    table_data.append([
        Paragraph("Código", cell_header_style),
        Paragraph("Título del Proyecto", cell_header_style),
        Paragraph("Carrera", cell_header_style),
        Paragraph("Categoría", cell_header_style),
        Paragraph("Líder / Creador", cell_header_style),
        Paragraph("Integrantes", cell_header_style),
        Paragraph("Evaluador", cell_header_style),
        Paragraph("Nota", cell_header_style),
        Paragraph("Estatus", cell_header_style),
    ])
    
    proyectos = Proyecto.objects.all().select_related('carrera', 'creado_por').prefetch_related('miembros', 'evaluadores')
    
    cat_map = dict(Proyecto.CATEGORIA_CHOICES)
    estatus_map = dict(Proyecto.ESTATUS_CHOICES)
    
    for p in proyectos:
        integrantes_list = [m.nombre_completo for m in p.miembros.all()]
        integrantes_str = ", ".join(integrantes_list)
        
        creador_str = f"{p.creado_por.first_name} {p.creado_por.last_name}" if p.creado_por.first_name else p.creado_por.username
        evaluador_str = ", ".join([f"{ev.first_name} {ev.last_name}" if ev.first_name else ev.username for ev in p.evaluadores.all()])
            
        calif_str = f"{p.calificacion:.2f}" if p.calificacion is not None else 'N/A'
        
        table_data.append([
            Paragraph(p.codigo, cell_style),
            Paragraph(p.titulo, cell_style),
            Paragraph(p.carrera.clave if p.carrera else 'S/C', cell_style),
            Paragraph(cat_map.get(p.categoria, p.categoria).capitalize(), cell_style),
            Paragraph(creador_str, cell_style),
            Paragraph(integrantes_str, cell_style),
            Paragraph(evaluador_str, cell_style),
            Paragraph(calif_str, cell_style),
            Paragraph(estatus_map.get(p.estatus, p.estatus), cell_style),
        ])
        
    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e293b')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')])
    ]))
    
    story.append(t)
    doc.build(story)
    return response
