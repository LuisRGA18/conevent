# DOCUMENTO DE EVIDENCIA TÉCNICA — MÓDULO DE EVALUACIÓN EXTERNA Y RÚBRICAS DINÁMICAS
**Proyecto:** ConEvent (SIGEA — Sistema Inteligente de Gestión de Eventos Académicos)  
**Dominio de Producción:** [https://conevent.duckdns.org](https://conevent.duckdns.org)  
**Tareas de Cronograma Validadas:** Filas 25, 26, 27, 28 y 29  
**Estado Anterior:** 0% — **Estado Actual:** 100% COMPLETADO Y OPERATIVO EN PRODUCCIÓN  

---

## 1. Resumen del Esquema de Evaluación
El módulo de evaluación académica de ConEvent resuelve dos requerimientos primordiales para ferias y concursos universitarios:
1. **Evaluación Formal de Docentes (Rúbricas Dinámicas RF-11):** Permite configurar rúbricas con ponderaciones porcentuales estrictas por evento (de 3 a 10 criterios), evaluando con escala cualitativa oficial UTEQ que se traduce en calificaciones decimales automáticas.
2. **Evaluación Abierta de Visitantes Externos:** Proporciona un mecanismo ligero y libre de registro mediante códigos QR físicos colocados en cada stand, facilitando que jueces de la industria, egresados y visitantes califiquen y dejen retroalimentación en tiempo real.

---

## 2. Modelo de Datos y Permisos por Rol (Filas 26 y 27 del Cronograma)

### 2.1 Modelos de Datos en `usuarios/models.py`
La estructura relacional desacopla los criterios globales para volverlos dependientes de cada `Evento`:

```python
# usuarios/models.py

class CriterioEvaluacion(models.Model):
    evento = models.ForeignKey('Evento', on_delete=models.CASCADE, related_name='criterios')
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    ponderacion = models.DecimalField(max_digits=5, decimal_places=2, help_text="Porcentaje de 0 a 100")
    orden = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['orden', 'id']


class Evaluacion(models.Model):
    proyecto = models.ForeignKey('Proyecto', on_delete=models.CASCADE, related_name='evaluaciones')
    evaluador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='evaluaciones_realizadas')
    calificacion_final = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    observaciones = models.TextField(blank=True, null=True)
    fecha_evaluacion = models.DateTimeField(auto_now_add=True)
    completada = models.BooleanField(default=False)

    class Meta:
        unique_together = ('proyecto', 'evaluador')


class DetalleEvaluacion(models.Model):
    CUALITATIVA_CHOICES = [
        ('AU', 'Autónomo (10)'),
        ('DE', 'Destacado (9)'),
        ('SA', 'Satisfactorio (8)'),
        ('NA', 'No Aprobatorio (6)'),
    ]
    VALORES_NUMERICOS = {'AU': 10.0, 'DE': 9.0, 'SA': 8.0, 'NA': 6.0}

    evaluacion = models.ForeignKey(Evaluacion, on_delete=models.CASCADE, related_name='detalles')
    criterio = models.ForeignKey(CriterioEvaluacion, on_delete=models.CASCADE, related_name='detalles_evaluacion')
    calificacion_cualitativa = models.CharField(max_length=2, choices=CUALITATIVA_CHOICES)
    calificacion_numerica = models.DecimalField(max_digits=4, decimal_places=2, editable=False)

    def save(self, *args, **kwargs):
        self.calificacion_numerica = self.VALORES_NUMERICOS.get(self.calificacion_cualitativa, 0.0)
        super().save(*args, **kwargs)
        self.evaluacion.recalcular_calificacion()


class EvaluacionExterna(models.Model):
    ESCALA_CHOICES = [
        ('AU', 'AU - Autónomo (10)'),
        ('DE', 'DE - Destacado (9)'),
        ('SA', 'SA - Satisfactorio (8)'),
        ('NA', 'NA - No Acreditado (6)'),
    ]
    proyecto = models.ForeignKey('Proyecto', on_delete=models.CASCADE, related_name='evaluaciones_externas')
    nombre_visitante = models.CharField(max_length=150)
    empresa_procedencia = models.CharField(max_length=150)
    correo_contacto = models.EmailField()
    telefono_contacto = models.CharField(max_length=20, blank=True)
    calificacion = models.CharField(max_length=2, choices=ESCALA_CHOICES)
    comentario = models.TextField(blank=True)
    codigo_acceso_usado = models.CharField(max_length=20)
    fecha = models.DateTimeField(auto_now_add=True)
```

### 2.2 Control de Acceso por Rol `EVALUADOR`
En `usuarios/views.py`:
```python
@login_required(login_url='/auth/login/')
def evaluar_proyecto_view(request, proyecto_id):
    if not (request.user.es_evaluador or request.user.es_admin):
        messages.error(request, "Acceso denegado. Solo docentes evaluadores pueden asentar calificaciones.")
        return redirect('index')
```

---

## 3. Rúbricas Dinámicas por Evento (RF-11) e Interfaz (Filas 28 y 29 del Cronograma)

### 3.1 Poblado Automático de Criterios Base al Crear Evento
Al crearse un nuevo evento (`crear_evento_view` en `usuarios/views.py`), el sistema inicializa automáticamente la rúbrica con los 3 criterios institucionales estándar:
```python
# usuarios/views.py
if form.is_valid():
    evento = form.save()
    # Inicializar rúbrica predeterminada (Suma = 100%)
    CriterioEvaluacion.objects.create(
        evento=evento, nombre="Presentación y Exposición",
        ponderacion=Decimal('25.0'), orden=1
    )
    CriterioEvaluacion.objects.create(
        evento=evento, nombre="Funcionalidad Técnica",
        ponderacion=Decimal('25.0'), orden=2
    )
    CriterioEvaluacion.objects.create(
        evento=evento, nombre="Innovación y Propuesta de Valor",
        ponderacion=Decimal('50.0'), orden=3
    )
```

### 3.2 FormSet Parametrizable de 3 a 10 Criterios
Desde el panel del administrador se habilita la adición y edición dinámica de criterios con validación de suma al 100%:
$$\sum_{i=1}^{n} \text{Ponderación}_i = 100.00\% \quad (3 \le n \le 10)$$

### 3.3 Campo de Observaciones Opcional
En `usuarios/models.py` y el formulario de evaluación, el campo `observaciones` está configurado con `blank=True, null=True`, permitiendo calificar de forma ágil sin obligar al evaluador a escribir texto si el desempeño fue estándar.

### 3.4 Generación de Códigos QR para Evaluación Externa
En `usuarios/views.py`:
- `qr_externo_view`: Genera el gráfico QR PNG dinámico que apunta a `https://conevent.duckdns.org/proyectos/<id>/evaluar-externo/`.
- `qr_externo_lote_view`: Renderiza una hoja imprimible de gafetes para stands con los identificadores del proyecto y sus códigos QR listos para exhibición.

---

## 4. Guía de Capturas Recomendadas para Auditoría

| No. | Elemento a Evidenciar | Procedimiento / URL | Justificación Técnica |
|:---:|:----------------------|:-------------------|:----------------------|
| **1** | Interfaz de Rúbrica Dinámica | Iniciar sesión como docente $\rightarrow$ `/auth/mis-evaluaciones/<id>/evaluar/` | Demuestra la presentación de los criterios específicos del evento y selector cualitativo (AU, DE, SA, NA). |
| **2** | Cálculo Automático de Promedio | Enviar evaluación $\rightarrow$ Verificar la tarjeta del proyecto calificado en `/dashboard/`. | Evidencia el cálculo ponderado en base 10 sin discrepancias decimales. |
| **3** | Formulario de Evaluación Externa Móvil | Escanear QR o abrir en navegador de incógnito: `/proyectos/1/evaluar-externo/` | Comprueba el formulario público para visitantes y jueces externos. |
| **4** | Gafetes QR en Lote para Impresión | `https://conevent.duckdns.org/proyectos/qr-externo/lote/` | Muestra la grilla de gafetes institucionales generados con la librería `qrcode`. |
