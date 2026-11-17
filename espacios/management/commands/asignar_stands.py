from django.core.management.base import BaseCommand
from django.db import transaction
from usuarios.models import Proyecto, Evento
from espacios.models import Stand, AsignacionStand

class Command(BaseCommand):
    help = 'Asigna stands automáticamente a proyectos aprobados sin stand para un evento específico'

    def add_arguments(self, parser):
        parser.add_argument(
            '--evento', type=int, required=True,
            help='ID del evento para asignar stands'
        )

    def handle(self, *args, **options):
        evento_id = options['evento']
        try:
            evento = Evento.objects.get(pk=evento_id)
        except Evento.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'No se encontró el evento con ID {evento_id}.'))
            return

        # Proyectos aprobados sin stand asignado del evento
        proyectos = Proyecto.objects.filter(
            evento_id=evento_id,
            estatus='aprobado'
        ).exclude(
            asignacionstand__activa=True
        ).order_by('carrera__clave', 'titulo')

        self.stdout.write(f'Proyectos sin stand ({evento.nombre}): {proyectos.count()}')

        if not proyectos.exists():
            self.stdout.write(self.style.WARNING(
                'No hay proyectos aprobados sin stand. '
                'Verifica que los proyectos tengan estatus="aprobado".'
            ))
            return

        # Stands disponibles en el recinto del evento
        stands_disponibles = Stand.objects.filter(
            esta_activo=True
        )
        if evento.recinto:
            stands_recinto = stands_disponibles.filter(planta__recinto=evento.recinto)
            if stands_recinto.exists():
                stands_disponibles = stands_recinto

        stands_disponibles = stands_disponibles.exclude(
            asignacion__activa=True
        ).order_by('planta__nivel', 'pos_fila', 'pos_col')

        self.stdout.write(f'Stands disponibles en {evento.recinto.nombre if evento.recinto else "Recinto"}: {stands_disponibles.count()}')

        if not stands_disponibles.exists():
            self.stdout.write(self.style.ERROR('No hay stands disponibles.'))
            return

        stands_list = list(stands_disponibles)
        stand_index = 0
        asignados = 0
        omitidos = 0

        with transaction.atomic():
            for proyecto in proyectos:
                mesas = proyecto.mesas_requeridas or 1

                # Verificar autorización para 3 mesas
                if mesas == 3 and not proyecto.mesas_autorizadas:
                    self.stdout.write(self.style.WARNING(
                        f'OMITIDO: {proyecto.titulo} solicita 3 mesas sin autorizacion.'
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
