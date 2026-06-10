import uuid
from django.db import models
from django.conf import settings

class ItemInventario(models.Model):
    ESTADO_CHOICES = [
        ('bueno', 'Excelente / Bueno'),
        ('regular', 'Regular / Desgastado'),
        ('malo', 'Dañado / Requiere cambio'),
    ]

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, verbose_name="Código UUID (para QR)")
    nombre = models.CharField(max_length=100, verbose_name="Nombre del mobiliario/equipo")
    descripcion = models.TextField(blank=True, verbose_name="Descripción o número de serie")
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='bueno', verbose_name="Estado físico")
    
    # Ubicación física del ítem (a qué stand está asignado actualmente)
    stand_asignado = models.ForeignKey(
        'espacios.Stand',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='items_inventario',
        verbose_name="Stand asignado"
    )
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de registro")

    class Meta:
        verbose_name = "Mobiliario / Item de Inventario"
        verbose_name_plural = "Mobiliarios / Items de Inventario"
        ordering = ['nombre', '-fecha_registro']

    def __str__(self):
        return f"{self.nombre} (Stand {self.stand_asignado.numero if self.stand_asignado else 'Sin Stand'})"

    @property
    def url_qr(self):
        return f"/inventario/item/{self.uuid}/"


class Incidencia(models.Model):
    PRIORIDAD_CHOICES = [
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta / Crítica'),
    ]

    item = models.ForeignKey(
        ItemInventario, 
        on_delete=models.CASCADE, 
        related_name='incidencias', 
        verbose_name="Mobiliario afectado"
    )
    titulo = models.CharField(max_length=150, verbose_name="Título del problema")
    descripcion = models.TextField(verbose_name="Detalle de la incidencia")
    prioridad = models.CharField(max_length=10, choices=PRIORIDAD_CHOICES, default='media', verbose_name="Prioridad")
    
    reportado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='incidencias_reportadas',
        verbose_name="Reportado por"
    )
    
    resuelta = models.BooleanField(default=False, verbose_name="¿Incidencia resuelta?")
    comentarios_resolucion = models.TextField(blank=True, verbose_name="Comentarios de resolución")
    
    fecha_reporte = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de reporte")
    fecha_resolucion = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de resolución")

    class Meta:
        verbose_name = "Incidencia de Inventario"
        verbose_name_plural = "Incidencias de Inventario"
        ordering = ['resuelta', '-fecha_reporte']

    def __str__(self):
        estado_inc = "Resuelta" if self.resuelta else "Activa"
        return f"{self.titulo} - {self.item.nombre} ({estado_inc})"
