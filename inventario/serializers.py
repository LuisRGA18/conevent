from rest_framework import serializers
from .models import ItemInventario, Incidencia
from espacios.serializers import StandSerializer

class ItemInventarioSerializer(serializers.ModelSerializer):
    stand_info = StandSerializer(source='stand_asignado', read_only=True)
    
    class Meta:
        model = ItemInventario
        fields = ['id', 'uuid', 'nombre', 'descripcion', 'estado', 'stand_asignado', 'stand_info', 'fecha_registro']
        read_only_fields = ['uuid', 'fecha_registro']

class IncidenciaSerializer(serializers.ModelSerializer):
    item_info = ItemInventarioSerializer(source='item', read_only=True)
    reportado_por_username = serializers.ReadOnlyField(source='reportado_por.username')
    
    class Meta:
        model = Incidencia
        fields = [
            'id', 'item', 'item_info', 'titulo', 'descripcion', 'prioridad',
            'reportado_por', 'reportado_por_username', 'resuelta', 
            'comentarios_resolucion', 'fecha_reporte', 'fecha_resolucion'
        ]
        read_only_fields = ['reportado_por', 'fecha_reporte', 'fecha_resolucion']
