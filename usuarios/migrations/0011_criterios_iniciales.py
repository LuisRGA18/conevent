from django.db import migrations

def update_and_create_criterios(apps, schema_editor):
    CriterioEvaluacion = apps.get_model('usuarios', 'CriterioEvaluacion')
    
    # Update existing criteria weights
    CriterioEvaluacion.objects.filter(nombre='Innovación').update(peso=0.30)
    CriterioEvaluacion.objects.filter(nombre='Exposición').update(peso=0.25)
    CriterioEvaluacion.objects.filter(nombre='Viabilidad').update(peso=0.20)
    
    # Create the new criterion
    CriterioEvaluacion.objects.get_or_create(
        nombre='Funcionalidad Técnica',
        defaults={
            'descripcion': 'Nivel de desarrollo, funcionamiento real del prototipo y solidez técnica de la solución implementada.',
            'peso': 0.25,
            'activo': True
        }
    )

def reverse_criterios(apps, schema_editor):
    CriterioEvaluacion = apps.get_model('usuarios', 'CriterioEvaluacion')
    
    # Delete the new criterion
    CriterioEvaluacion.objects.filter(nombre='Funcionalidad Técnica').delete()
    
    # Restore old weights
    CriterioEvaluacion.objects.filter(nombre='Innovación').update(peso=0.40)
    CriterioEvaluacion.objects.filter(nombre='Exposición').update(peso=0.30)
    CriterioEvaluacion.objects.filter(nombre='Viabilidad').update(peso=0.30)

class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0010_proyecto_qr_evaluacion_externa'),
    ]

    operations = [
        migrations.RunPython(update_and_create_criterios, reverse_criterios),
    ]
