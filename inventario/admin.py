from django.contrib import admin
from django.utils.html import format_html
import django.utils.timezone
from .models import ItemInventario, Incidencia

@admin.register(ItemInventario)
class ItemInventarioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'estado', 'stand_asignado', 'fecha_registro', 'ver_codigo_qr')
    list_filter = ('estado', 'stand_asignado__zona')
    search_fields = ('nombre', 'descripcion', 'uuid')
    readonly_fields = ('uuid', 'ver_codigo_qr_grande')

    def ver_codigo_qr(self, obj):
        # Generar código QR miniatura usando un servicio público confiable de QR
        # En producción se configuraría la IP/Dominio real
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=100x100&data=http://127.0.0.1:8000{obj.url_qr}"
        return format_html('<img src="{}" width="40" height="40" style="border: 1px solid #ccc; border-radius: 4px;" />', qr_url)
    ver_codigo_qr.short_description = "Vista QR"

    def ver_codigo_qr_grande(self, obj):
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=http://127.0.0.1:8000{obj.url_qr}"
        return format_html(
            '<div>'
            '<img src="{}" width="200" height="200" style="border: 1px solid #ccc; border-radius: 8px; margin-bottom: 10px;" /><br>'
            '<a href="{}" target="_blank" class="button" style="padding: 5px 15px; background: #417690; color: white; text-decoration: none; border-radius: 4px; font-weight: bold;">Imprimir / Escanear QR</a>'
            '</div>', 
            qr_url, obj.url_qr
        )
    ver_codigo_qr_grande.short_description = "Código QR para Inventario"


@admin.register(Incidencia)
class IncidenciaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'item', 'prioridad', 'resuelta', 'reportado_por', 'fecha_reporte')
    list_filter = ('prioridad', 'resuelta', 'fecha_reporte')
    search_fields = ('titulo', 'descripcion', 'item__nombre', 'comentarios_resolucion')
    list_editable = ('resuelta', 'prioridad')
    raw_id_fields = ('item', 'reportado_por')
    readonly_fields = ('fecha_reporte',)

    def save_model(self, request, obj, form, change):
        # Asignar usuario logueado si no se ha definido reportado_por
        if not obj.pk and not obj.reportado_por:
            obj.reportado_por = request.user
        
        # Registrar marca de tiempo al marcar como resuelta
        if obj.resuelta and not obj.fecha_resolucion:
            obj.fecha_resolucion = django.utils.timezone.now()
        elif not obj.resuelta:
            obj.fecha_resolucion = None
            
        super().save_model(request, obj, form, change)
