from django.core.management.base import BaseCommand
from django.db import transaction
from usuarios.models import Proyecto
from espacios.models import Stand, AsignacionStand

class Command(BaseCommand):
    help = 'Asigna stands automáticamente a proyectos aprobados sin stand'

    def handle(self, *args, **options):
        # Proyectos aprobados sin stand asignado
        proyectos_sin_stand = Proyecto.objects.filter(
            estatus='aprobado'
        ).exclude(
            asignaciones_stands__activa=True
        ).order_by('carrera__clave', 'titulo')

        self.stdout.write(f'Proyectos sin stand: {proyectos_sin_stand.count()}')

        if not proyectos_sin_stand.exists():
            self.stdout.write(self.style.WARNING(
                'No hay proyectos aprobados sin stand. '
                'Verifica que los proyectos tengan estatus="aprobado".'
            ))
            # Mostrar estatus actuales para diagnóstico
            from django.db.models import Count
            estatus = Proyecto.objects.values('estatus').annotate(total=Count('id'))
            for e in estatus:
                self.stdout.write(f'  estatus={e["estatus"]}: {e["total"]} proyectos')
            return

        # Stands disponibles ordenados geométricamente
        stands_disponibles = Stand.objects.filter(
            esta_activo=True
        ).exclude(
            asignacion__activa=True
        ).order_by('zona', 'pos_fila', 'pos_col')

        self.stdout.write(f'Stands disponibles: {stands_disponibles.count()}')

        if not stands_disponibles.exists():
            self.stdout.write(self.style.ERROR('No hay stands disponibles.'))
            return

        stands_list = list(stands_disponibles)
        stand_index = 0
        asignados = 0
        omitidos = 0

        with transaction.atomic():
            for proyecto in proyectos_sin_stand:
                mesas = proyecto.mesas_requeridas or 1

                # Verificar autorización para 3 mesas
                if mesas == 3 and not proyecto.mesas_autorizadas:
                    self.stdout.write(self.style.WARNING(
                        f'OMITIDO: {proyecto.titulo} solicita 3 mesas sin autorización.'
                    ))
                    omitidos += 1
                    continue

                # Verificar que hay suficientes stands contiguos
                if stand_index + mesas > len(stands_list):
                    self.stdout.write(self.style.ERROR(
                        f'No hay suficientes stands para {proyecto.titulo} ({mesas} mesas).'
                    ))
                    break

                # Asignar stands contiguos
                for i in range(mesas):
                    stand = stands_list[stand_index + i]
                    AsignacionStand.objects.create(
                        stand=stand,
                        proyecto=proyecto,
                        activa=True
                    )
                    self.stdout.write(f'  Stand {stand.numero} -> {proyecto.titulo}')

                stand_index += mesas
                asignados += 1

        self.stdout.write(self.style.SUCCESS(
            f'\nCompletado: {asignados} proyectos asignados, {omitidos} omitidos.'
        ))
