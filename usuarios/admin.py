from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, Carrera, Proyecto, Integrante, Evaluacion

@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'rol', 'matricula_empleado', 'is_staff')
    list_filter = ('rol', 'is_staff', 'is_superuser', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('Información de ConEvent', {'fields': ('rol', 'matricula_empleado')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Información de ConEvent', {'fields': ('rol', 'matricula_empleado')}),
    )

@admin.register(Carrera)
class CarreraAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'clave')
    search_fields = ('nombre', 'clave')

class IntegranteInline(admin.TabularInline):
    model = Integrante
    extra = 1

@admin.register(Proyecto)
class ProyectoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'titulo', 'creado_por', 'carrera', 'grupo', 'estatus', 'calificacion')
    list_filter = ('estatus', 'carrera', 'categoria')
    search_fields = ('titulo', 'descripcion', 'creado_por__username', 'creado_por__first_name')
    inlines = [IntegranteInline]
    raw_id_fields = ('creado_por',)
    filter_horizontal = ('evaluadores',)

@admin.register(Integrante)
class IntegranteAdmin(admin.ModelAdmin):
    list_display = ('nombre_completo', 'matricula', 'proyecto', 'correo', 'es_lider')
    list_filter = ('es_lider', 'proyecto__carrera')
    search_fields = ('nombre_completo', 'matricula', 'proyecto__titulo')

from .models import Usuario, Carrera, Proyecto, Integrante, Evaluacion, CriterioEvaluacion, DetalleEvaluacion

class DetalleEvaluacionInline(admin.TabularInline):
    model = DetalleEvaluacion
    extra = 0
    readonly_fields = ('calificacion_numerica',)

@admin.register(Evaluacion)
class EvaluacionAdmin(admin.ModelAdmin):
    list_display = ('proyecto', 'evaluador', 'calificacion', 'estatus_sugerido', 'fecha_evaluacion')
    list_filter = ('estatus_sugerido', 'fecha_evaluacion')
    search_fields = ('proyecto__titulo', 'evaluador__username')
    inlines = [DetalleEvaluacionInline]

@admin.register(CriterioEvaluacion)
class CriterioEvaluacionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'peso', 'activo')
    list_filter = ('activo',)
    search_fields = ('nombre', 'descripcion')
