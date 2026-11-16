from django.core.management.base import BaseCommand
from espacios.models import Recinto, Planta, Stand

class Command(BaseCommand):
    help = 'Pobla stands para todas las plantas de un recinto'

    def add_arguments(self, parser):
        parser.add_argument(
            '--recinto', type=int, default=1,
            help='ID del recinto a poblar (default: 1 Auditorio)'
        )

    def handle(self, *args, **options):
        recinto_id = options.get('recinto') or 1
        recinto, _ = Recinto.objects.get_or_create(
            pk=recinto_id,
            defaults={
                'nombre': 'Auditorio UTEQ' if recinto_id == 1 else f'Recinto {recinto_id}',
                'descripcion': 'Auditorio principal — 11.7m x 30m',
                'direccion': 'Av. Pie de la Cuesta No. 2501, UTEQ, Querétaro'
            }
        )

        plantas = list(recinto.plantas.all())
        if not plantas:
            p = Planta.objects.create(
                recinto=recinto,
                nombre='Planta Única',
                nivel=0,
                filas=10,
                columnas=7,
                descripcion='Distribución 7x10 — 70 stands'
            )
            plantas = [p]

        for planta in plantas:
            creados = 0
            for fila in range(1, planta.filas + 1):
                for col in range(1, planta.columnas + 1):
                    zona = 'A' if fila <= 4 else 'B' if fila <= 7 else 'C'
                    numero = f"{zona}-{str((fila-1)*planta.columnas + col).zfill(2)}"
                    Stand.objects.get_or_create(
                        planta=planta,
                        pos_fila=fila,
                        pos_col=col,
                        defaults={
                            'numero': numero,
                            'zona': zona,
                            'esta_activo': True
                        }
                    )
                    creados += 1
            self.stdout.write(
                f'{planta.nombre}: {creados} stands creados'
            )
