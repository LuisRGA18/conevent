from rest_framework import serializers
from .models import Stand, AsignacionStand, CargaDocente

class StandSerializer(serializers.ModelSerializer):
    zona_display = serializers.CharField(source='get_zona_display', read_only=True)
    
    class Meta:
        model = Stand
        fields = ['id', 'numero', 'zona', 'zona_display', 'capacidad_proyectos', 'descripcion', 'esta_activo']

class AsignacionStandSerializer(serializers.ModelSerializer):
    stand_info = StandSerializer(source='stand', read_only=True)
    proyecto_titulo = serializers.CharField(source='proyecto.titulo', read_only=True)
    
    class Meta:
        model = AsignacionStand
        fields = ['id', 'stand', 'stand_info', 'proyecto', 'proyecto_titulo', 'fecha_asignacion', 'comentarios']
