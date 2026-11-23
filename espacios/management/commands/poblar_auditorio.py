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
            # Eliminar stands existentes de esta planta
            Stand.objects.filter(planta=planta).delete()
            creados = 0

            if recinto.pk == 1:
                # Auditorio — distribución grid estándar 7x10
                zonas = {range(1, 5): 'A', range(5, 9): 'B', range(9, 11): 'C'}
                for fila in range(1, planta.filas + 1):
                    zona = next((z for r, z in zonas.items() if fila in r), 'C')
                    for col in range(1, planta.columnas + 1):
                        num = (fila - 1) * planta.columnas + col
                        Stand.objects.create(
                            planta=planta,
                            numero=f"{zona}-{str(num).zfill(2)}",
                            zona=zona,
                            pos_fila=fila,
                            pos_col=col,
                            esta_activo=True
                        )
                        creados += 1

            elif recinto.pk == 2 and planta.nivel == 0:
                # Edificio K — Planta Baja (L invertida orientada a la izquierda)
                # Sección A: pasillo principal de 29m (filas 1-24, 2 columnas en orillas: izquierda y derecha)
                for fila in range(1, 25):
                    for col in [1, 2]:
                        Stand.objects.create(
                            planta=planta,
                            numero=f"PB-{str(creados + 1).zfill(2)}",
                            zona='A',
                            pos_fila=fila,
                            pos_col=col,
                            esta_activo=True
                        )
                        creados += 1
                # Sección B: extensión L de 16m x 6.67m (filas 25-37, 2 columnas en orillas perimetrales: superior e inferior)
                # Sin celdas atravesando el centro del pasillo de tránsito
                for fila in range(25, 38):
                    for col in [1, 2]:
                        Stand.objects.create(
                            planta=planta,
                            numero=f"PB-{str(creados + 1).zfill(2)}",
                            zona='B',
                            pos_fila=fila,
                            pos_col=col,
                            esta_activo=True
                        )
                        creados += 1

            elif recinto.pk == 2 and planta.nivel == 1:
                # Edificio K — Planta Alta (rectángulo con ensanchamiento)
                # Tramo recto alargado (filas 1-24, 2 columnas en orillas: izq col 1, der col 2)
                for fila in range(1, 25):
                    for col in [1, 2]:
                        Stand.objects.create(
                            planta=planta,
                            numero=f"PA-{str(creados + 1).zfill(2)}",
                            zona='A',
                            pos_fila=fila,
                            pos_col=col,
                            esta_activo=True
                        )
                        creados += 1
                # Ensanchamiento final (filas 25-29, EXCLUSIVAMENTE en muros perimetrales: izq col 1, der col 2)
                # Se eliminan stands flotantes en el centro para dejar libre el tránsito
                for fila in range(25, 30):
                    for col in [1, 2]:
                        Stand.objects.create(
                            planta=planta,
                            numero=f"PA-{str(creados + 1).zfill(2)}",
                            zona='B',
                            pos_fila=fila,
                            pos_col=col,
                            esta_activo=True
                        )
                        creados += 1
                # Fila de cierre del fondo (fila 30, 6 stands horizontales sobre muro posterior)
                for col in range(1, 7):
                    Stand.objects.create(
                        planta=planta,
                        numero=f"PA-{str(creados + 1).zfill(2)}",
                        zona='C',
                        pos_fila=30,
                        pos_col=col,
                        esta_activo=True
                    )
                    creados += 1

            self.stdout.write(
                self.style.SUCCESS(f'{planta.nombre}: {creados} stands creados')
            )
