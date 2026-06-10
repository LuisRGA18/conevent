from django.contrib import admin
from .models import Stand, AsignacionStand

@admin.register(Stand)
class StandAdmin(admin.ModelAdmin):
    list_display = ('numero', 'zona', 'capacidad_proyectos', 'esta_activo', 'get_proyecto_asignado')
    list_filter = ('zona', 'esta_activo')
    search_fields = ('numero', 'descripcion')
    list_editable = ('esta_activo',)

    def get_proyecto_asignado(self, obj):
        if hasattr(obj, 'asignacion'):
            return obj.asignacion.proyecto.titulo
        return "Sin asignar"
    get_proyecto_asignado.short_description = "Proyecto Asignado"


@admin.register(AsignacionStand)
class AsignacionStandAdmin(admin.ModelAdmin):
    list_display = ('stand', 'proyecto', 'fecha_asignacion')
    list_filter = ('stand__zona', 'fecha_asignacion')
    search_fields = ('proyecto__titulo', 'stand__numero', 'comentarios')
    raw_id_fields = ('proyecto',)
