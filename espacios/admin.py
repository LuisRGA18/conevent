from django.contrib import admin
from .models import Recinto, Planta, Stand, AsignacionStand

@admin.register(Recinto)
class RecintoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'direccion')
    search_fields = ('nombre', 'direccion')


@admin.register(Planta)
class PlantaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'recinto', 'nivel', 'filas', 'columnas')
    list_filter = ('recinto', 'nivel')
    search_fields = ('nombre', 'recinto__nombre')


@admin.register(Stand)
class StandAdmin(admin.ModelAdmin):
    list_display = ('numero', 'planta', 'zona', 'esta_activo', 'get_proyecto_asignado')
    list_filter = ('planta__recinto', 'planta', 'esta_activo')
    search_fields = ('numero', 'zona')
    list_editable = ('esta_activo',)

    def get_proyecto_asignado(self, obj):
        asig = obj.asignacion
        if asig and asig.proyecto:
            return asig.proyecto.titulo
        return "Sin asignar"
    get_proyecto_asignado.short_description = "Proyecto Asignado"


@admin.register(AsignacionStand)
class AsignacionStandAdmin(admin.ModelAdmin):
    list_display = ('stand', 'proyecto', 'activa', 'fecha_asignacion')
    list_filter = ('activa', 'fecha_asignacion')
    search_fields = ('proyecto__titulo', 'stand__numero', 'comentarios')
    raw_id_fields = ('proyecto',)
