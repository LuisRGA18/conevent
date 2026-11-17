from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Pobla stands para todas las plantas de un recinto'

    def add_arguments(self, parser):
        parser.add_argument(
            '--recinto', type=int, default=1,
            help='ID del recinto a poblar (default: 1 Auditorio)'
        )

    def handle(self, *args, **options):
        from espacios.models import Recinto, Stand
        try:
            recinto = Recinto.objects.get(pk=options['recinto'])
        except Recinto.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"No existe el recinto con ID {options['recinto']}"))
            return

        for planta in recinto.plantas.all():
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
            self.stdout.write(self.style.SUCCESS(f'{planta.nombre}: {creados} stands verificados/creados'))
