from django.core.management.base import BaseCommand
from django.db import transaction, models
from usuarios.models import Proyecto, Evento
from espacios.models import Stand, AsignacionStand, Recinto
import datetime

class Command(BaseCommand):
    help = 'Asigna stands automáticamente a proyectos aprobados sin stand para un evento específico'

    def add_arguments(self, parser):
        parser.add_argument(
            '--evento', type=int, required=False, default=None,
            help='ID del evento para asignar stands (opcional, default: evento activo)'
        )

    def handle(self, *args, **options):
        evento_id = options.get('evento')
        if evento_id:
            try:
                evento = Evento.objects.get(pk=evento_id)
            except Evento.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'No se encontró el evento con ID {evento_id}.'))
                return
        else:
            evento = Evento.objects.filter(estatus='activo').first() or Evento.objects.first()
            if not evento:
                recinto, _ = Recinto.objects.get_or_create(
                    pk=1,
                    defaults={'nombre': 'Auditorio UTEQ'}
                )
                evento, _ = Evento.objects.get_or_create(
                    nombre='Evento Principal ConEvent',
                    defaults={
                        'fecha_inicio': datetime.date.today(),
                        'fecha_fin': datetime.date.today(),
                        'estatus': 'activo',
                        'recinto': recinto
                    }
                )

        # Proyectos aprobados sin stand asignado (del evento o no asignados a evento aún)
        proyectos_sin_stand = Proyecto.objects.filter(
            estatus='aprobado'
        ).filter(
            models.Q(evento=evento) | models.Q(evento__isnull=True)
        ).exclude(
            asignacionstand__activa=True
        ).order_by('carrera__clave', 'titulo')

        self.stdout.write(f'Proyectos sin stand ({evento.nombre}): {proyectos_sin_stand.count()}')

        if not proyectos_sin_stand.exists():
            self.stdout.write(self.style.WARNING(
                'No hay proyectos aprobados sin stand. '
                'Verifica que los proyectos tengan estatus="aprobado".'
            ))
            from django.db.models import Count
            estatus = Proyecto.objects.values('estatus').annotate(total=Count('id'))
            for e in estatus:
                self.stdout.write(f'  estatus={e["estatus"]}: {e["total"]} proyectos')
            return

        # Stands disponibles ordenados en el recinto del evento
        stands_disponibles = Stand.objects.filter(esta_activo=True)
        if evento and evento.recinto:
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
            for proyecto in proyectos_sin_stand:
                if proyecto.evento is None:
                    proyecto.evento = evento
                    proyecto.save(update_fields=['evento'])

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
