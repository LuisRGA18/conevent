from django.core.management.base import BaseCommand
from usuarios.models import Proyecto
from decimal import Decimal

class Command(BaseCommand):
    help = 'Recalcula el promedio de calificaciones de todos los proyectos'

    def handle(self, *args, **options):
        proyectos = Proyecto.objects.all()
        for proyecto in proyectos:
            evaluaciones = proyecto.evaluaciones.filter(
                calificacion_final__isnull=False
            )
            if evaluaciones.exists():
                total = sum(e.calificacion_final for e in evaluaciones)
                count = evaluaciones.count()
                promedio = round(Decimal(str(total)) / Decimal(str(count)), 2)
                Proyecto.objects.filter(pk=proyecto.pk).update(
                    calificacion_final=promedio
                )
                self.stdout.write(
                    f'{proyecto.titulo}: {count} eval. -> promedio {promedio}'
                )
        self.stdout.write(self.style.SUCCESS('Recálculo completado.'))
