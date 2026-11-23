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
                # Sección A: pasillo principal de 29m (filas 1-20, orillas: col 1 izq, col 2 der)
                # NOTA: Las filas 21-24 están ocupadas por el cubo de escaleras (omitiendo celdas PB-41 a PB-48)
                for fila in range(1, 21):
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

                # Sección B: extensión L de 16m x 6.67m (filas 25-37, orillas: col 1 sup, col 2 inf)
                # Sin celdas atravesando el centro del pasillo de tránsito ni el cubo de escaleras
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
                # Tramo recto alargado (filas 1-24, orillas col 1 y col 2)
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

                # Ensanchamiento final (filas 25-29)
                # NOTA: Se omiten celdas de la orilla derecha en la zona de llegada de escaleras (col 2 en filas 25-27, PA-52, 54, 56)
                # para dejar la franja libre de escaleras/acceso.
                for fila in range(25, 30):
                    # En muro izquierdo (col 1): stands normales
                    Stand.objects.create(
                        planta=planta,
                        numero=f"PA-{str(creados + 1).zfill(2)}",
                        zona='B',
                        pos_fila=fila,
                        pos_col=1,
                        esta_activo=True
                    )
                    creados += 1

                    # En muro derecho (col 2): sólo filas 28 y 29 (desobstruyendo filas 25-27 de escaleras)
                    if fila in [28, 29]:
                        Stand.objects.create(
                            planta=planta,
                            numero=f"PA-{str(creados + 1).zfill(2)}",
                            zona='B',
                            pos_fila=fila,
                            pos_col=2,
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
