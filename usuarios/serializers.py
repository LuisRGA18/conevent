from rest_framework import serializers
from .models import Usuario, Carrera, Proyecto, Integrante, CriterioEvaluacion, Evaluacion, DetalleEvaluacion
from espacios.serializers import AsignacionStandSerializer

class CarreraSerializer(serializers.ModelSerializer):
    class Meta:
        model = Carrera
        fields = ['id', 'nombre', 'clave']

class IntegranteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Integrante
        fields = ['id', 'nombre_completo', 'matricula', 'correo', 'es_lider']

class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'rol', 'matricula_empleado']
        read_only_fields = ['id']

class ProyectoSerializer(serializers.ModelSerializer):
    miembros = IntegranteSerializer(many=True, required=False)
    carrera_info = CarreraSerializer(source='carrera', read_only=True)
    carrera_id = serializers.PrimaryKeyRelatedField(
        queryset=Carrera.objects.all(), source='carrera', write_only=True, required=False, allow_null=True
    )
    codigo = serializers.ReadOnlyField()
    num_integrantes = serializers.ReadOnlyField()
    asignaciones_stands = AsignacionStandSerializer(many=True, read_only=True)
    creado_por_info = UsuarioSerializer(source='creado_por', read_only=True)
    evaluadores = serializers.StringRelatedField(many=True, read_only=True)
    evaluadores_info = UsuarioSerializer(source='evaluadores', many=True, read_only=True)

    class Meta:
        model = Proyecto
        fields = [
            'id', 'titulo', 'descripcion', 'carrera_info', 'carrera_id',
            'grupo', 'categoria', 'logo', 'creado_por_info', 'evaluadores', 
            'evaluadores_info', 'estatus', 'calificacion', 'codigo', 'num_integrantes',
            'miembros', 'asignaciones_stands', 'fecha_registro', 'fecha_actualizacion'
        ]
        read_only_fields = ['calificacion', 'estatus']

    def create(self, validated_data):
        miembros_data = validated_data.pop('miembros', [])
        request = self.context.get('request')
        if request and request.user and not validated_data.get('creado_por'):
            validated_data['creado_por'] = request.user
            
        proyecto = Proyecto.objects.create(**validated_data)
        for miembro_data in miembros_data:
            Integrante.objects.create(proyecto=proyecto, **miembro_data)
        return proyecto

    def update(self, instance, validated_data):
        miembros_data = validated_data.pop('miembros', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if miembros_data is not None:
            instance.miembros.all().delete()
            for miembro_data in miembros_data:
                Integrante.objects.create(proyecto=instance, **miembro_data)
        return instance

class CriterioEvaluacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CriterioEvaluacion
        fields = ['id', 'nombre', 'descripcion', 'peso', 'activo']

class DetalleEvaluacionSerializer(serializers.ModelSerializer):
    criterio_id = serializers.PrimaryKeyRelatedField(
        queryset=CriterioEvaluacion.objects.all(), source='criterio'
    )
    criterio_nombre = serializers.ReadOnlyField(source='criterio.nombre')
    
    class Meta:
        model = DetalleEvaluacion
        fields = ['id', 'criterio_id', 'criterio_nombre', 'calificacion_cualitativa', 'calificacion_numerica']
        read_only_fields = ['calificacion_numerica']

class EvaluacionSerializer(serializers.ModelSerializer):
    detalles = DetalleEvaluacionSerializer(many=True, required=False)
    evaluador_nombre = serializers.ReadOnlyField(source='evaluador.username')
    proyecto_titulo = serializers.ReadOnlyField(source='proyecto.titulo')
    
    class Meta:
        model = Evaluacion
        fields = [
            'id', 'proyecto', 'evaluador', 'evaluador_nombre', 'proyecto_titulo',
            'calificacion', 'comentarios_evaluador', 'estatus_sugerido', 
            'fecha_evaluacion', 'detalles'
        ]
        read_only_fields = ['calificacion', 'evaluador']

    def create(self, validated_data):
        detalles_data = validated_data.pop('detalles', [])
        request = self.context.get('request')
        if request and request.user:
            validated_data['evaluador'] = request.user
        
        evaluacion = Evaluacion.objects.create(**validated_data)
        for detalle_data in detalles_data:
            DetalleEvaluacion.objects.create(evaluacion=evaluacion, **detalle_data)
        
        evaluacion.recalcular_calificacion()
        return evaluacion

    def update(self, instance, validated_data):
        detalles_data = validated_data.pop('detalles', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if detalles_data is not None:
            instance.detalles.all().delete()
            for detalle_data in detalles_data:
                DetalleEvaluacion.objects.create(evaluacion=instance, **detalle_data)
            instance.recalcular_calificacion()
            
        return instance
