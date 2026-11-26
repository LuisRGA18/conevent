# DOCUMENTO DE EVIDENCIA TÉCNICA — MÓDULO DE REPORTES, ANALÍTICA HISTÓRICA Y API REST
**Proyecto:** ConEvent (SIGEA — Sistema Inteligente de Gestión de Eventos Académicos)  
**Dominio de Producción:** [https://conevent.duckdns.org](https://conevent.duckdns.org)  
**Tareas de Cronograma Validadas:** Filas 34, 35, 36, 37, 38 y 39  
**Estado Anterior:** 0% — **Estado Actual:** 100% COMPLETADO Y OPERATIVO EN PRODUCCIÓN  

---

## 1. Resumen del Módulo de Analítica
El módulo de analítica y reportes de ConEvent consolida el flujo de datos generado durante los certámenes académicos para ofrecer métricas inmediatas de avance a los coordinadores, generar constancias y actas institucionales en formato PDF formal, y proveer una capa de interoperabilidad RESTful orientada a integraciones futuras con otros sistemas de la UTEQ.

---

## 2. Dashboard y Métricas en Tiempo Real (Filas 35 y 37 del Cronograma)

### 2.1 Vista Central del Dashboard (`index_view` en `usuarios/views.py`)
La vista `/dashboard/` procesa dinámicamente las métricas del evento activo mediante agregaciones del ORM de Django:

```python
# usuarios/views.py (index_view)
evento_activo = None
if evento_activo_id:
    evento_activo = Evento.objects.filter(id=evento_activo_id).first()

# Métricas consolidadas
total_proyectos = Proyecto.objects.filter(evento=evento_activo).count()
proyectos_aprobados = Proyecto.objects.filter(evento=evento_activo, estatus='aprobado').count()
proyectos_evaluados = Proyecto.objects.filter(evento=evento_activo, evaluaciones__completada=True).distinct().count()
stands_ocupados = AsignacionStand.objects.filter(stand__planta__recinto=evento_activo.recinto, activa=True).count()

# Desglose porcentual
avance_evaluaciones = (proyectos_evaluados / proyectos_aprobados * 100) if proyectos_aprobados > 0 else 0
```

### 2.2 Segmentación por Roles (RBAC)
- **ADMIN:** Visualiza métricas globales del evento, alertas de stands pendientes de asignación, solicitudes de cambio de mesa y desglose por división académica.
- **EVALUADOR:** Visualiza los proyectos asignados a su carga docente, estado de rúbricas completadas y pendientes por calificar.
- **ALUMNO:** Visualiza el estatus de aprobación de su proyecto, stand asignado en el mapa y la calificación asentada por el jurado.

---

## 3. Exportación e Impresión de Reportes (Fila 36 del Cronograma)

### 3.1 Motor de Generación PDF con ReportLab en `reportes/views.py`
En lugar de depender de la función de impresión del navegador, ConEvent integra un motor documental en el servidor utilizando la librería `reportlab`:

```python
# reportes/views.py
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

@login_required(login_url='/auth/login/')
def exportar_calificaciones_pdf_view(request):
    if request.user.rol != 'ADMIN':
        messages.error(request, "Acceso denegado. Solo administradores pueden exportar calificaciones.")
        return redirect('index')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="calificaciones_conevent.pdf"'

    # Hoja horizontal (landscape) para dar cabida a columnas amplias
    doc = SimpleDocTemplate(
        response, pagesize=landscape(letter),
        rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
    )
    story = []
    # Encabezado institucional UTEQ y metadatos
    # ...
    # Tabla con datos de Proyecto, Carrera, Integrantes, Evaluador y Promedio Final
    tabla = Table(data, colWidths=[50, 180, 100, 140, 130, 70])
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0b3c5d')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
    ]))
    story.append(tabla)
    doc.build(story)
    return response
```

---

## 4. API REST Documentada (Fila 38 del Cronograma)

### 4.1 Configuración de Django REST Framework (DRF)
En `conevent/settings.py` y `conevent/urls.py` se estructuró la capa de servicios desacoplados bajo `/api/`:

```python
# conevent/settings.py
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
}
```

### 4.2 Endpoints Clave
- `GET /api/stands/mapa/?recinto=<id>&evento=<id>`: Provee la topología de plantas y ubicación espacial de mesas con su metadata en formato JSON.
- `GET /api/token/` y `POST /api/token/refresh/`: Emisión y refresco seguro de tokens JWT para clientes móviles o externos.
- `GET /proyectos/<id>/qr-externo/`: Despacho binario de imagen QR PNG para integración con impresoras de etiquetas o gafetes.

---

## 5. Guía de Capturas Recomendadas para Auditoría

| No. | Elemento a Evidenciar | Procedimiento / URL | Justificación Técnica |
|:---:|:----------------------|:-------------------|:----------------------|
| **1** | Dashboard de Control y KPIs | `https://conevent.duckdns.org/dashboard/` | Valida el conteo en tiempo real de proyectos, porcentajes de avance y distribución. |
| **2** | Reporte Oficial en PDF | `https://conevent.duckdns.org/reportes/exportar/calificaciones-pdf/` | Demuestra la generación binaria de documentos oficiales con ReportLab. |
| **3** | Respuesta del Endpoint JSON | `https://conevent.duckdns.org/api/stands/mapa/?recinto=2` | Muestra la carga útil JSON con la geometría de plantas y stands del Edificio K. |
| **4** | Módulo de Inventario con QR | `https://conevent.duckdns.org/inventario/` | Evidencia el registro de mobiliario físico y la gestión de incidencias. |
