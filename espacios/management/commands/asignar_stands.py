from django.core.management.base import BaseCommand
from django.db import transaction
from usuarios.models import Proyecto
from espacios.models import Stand, AsignacionStand

class Command(BaseCommand):
    help = "Asigna automáticamente stands a proyectos aprobados agrupándolos contiguamente por carrera"

    def handle(self, *args, **options):
        # 1. Obtener proyectos aprobados que no tienen stand asignado
        # Ordenamos por carrera para garantizar la agrupación contigua
        proyectos = Proyecto.objects.filter(
            estatus='aprobado',
            asignaciones_stands__isnull=True
        ).select_related('carrera').order_by('carrera_id', 'titulo')

        if not proyectos.exists():
            self.stdout.write(self.style.SUCCESS("No hay proyectos aprobados pendientes de asignación de stand."))
            return

        # 2. Obtener stands activos y libres
        # Ordenamos por zona, fila y columna para asegurar posiciones consecutivas
        stands_libres = list(Stand.objects.filter(
            esta_activo=True,
            asignacion__isnull=True
        ).order_by('zona', 'pos_fila', 'pos_col'))

        if not stands_libres:
            self.stdout.write(self.style.ERROR("No hay stands disponibles libres para asignación."))
            return

        self.stdout.write(f"Proyectos pendientes por asignar: {proyectos.count()}")
        self.stdout.write(f"Stands disponibles: {len(stands_libres)}")

        # 3. Asignación secuencial respetando mesas_requeridas y contigüidad
        asignados = 0
        pendientes_por_error = 0

        for proy in proyectos:
            # Si solicita 3 mesas y no está autorizado, omitir e imprimir advertencia
            if proy.mesas_requeridas == 3 and not proy.mesas_autorizadas:
                self.stdout.write(
                    self.style.WARNING(
                        f"ADVERTENCIA: Proyecto '{proy.titulo}' solicita 3 mesas pero no tiene autorización. Omitido."
                    )
                )
                pendientes_por_error += 1
                continue

            N = proy.mesas_requeridas
            found = False

            # Buscar una secuencia de N stands contiguos (misma zona, misma pos_fila, pos_col consecutivas)
            for i in range(len(stands_libres) - N + 1):
                slice_stands = stands_libres[i : i + N]
                
                # Verificar misma zona
                if not all(s.zona == slice_stands[0].zona for s in slice_stands):
                    continue
                # Verificar misma fila
                if not all(s.pos_fila == slice_stands[0].pos_fila for s in slice_stands):
                    continue
                # Verificar columnas consecutivas
                if not all(slice_stands[k].pos_col == slice_stands[0].pos_col + k for k in range(N)):
                    continue

                # Si es válido, se realiza la asignación atómica
                with transaction.atomic():
                    for s in slice_stands:
                        AsignacionStand.objects.create(
                            stand=s,
                            proyecto=proy,
                            comentarios=f"Asignación automática ({N} mesas)"
                        )

                # Quitar stands de la lista de libres
                for s in slice_stands:
                    stands_libres.remove(s)

                carrera_clave = proy.carrera.clave if proy.carrera else "S/C"
                nums_stands = ", ".join([s.numero for s in slice_stands])
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Asignado: '{proy.titulo}' [{carrera_clave}] -> Stands [{nums_stands}]"
                    )
                )
                asignados += 1
                found = True
                break

            if not found:
                self.stdout.write(
                    self.style.WARNING(
                        f"ADVERTENCIA: No se encontró un bloque de {N} stands contiguos libres en la misma fila para '{proy.titulo}'."
                    )
                )
                pendientes_por_error += 1

        self.stdout.write(self.style.SUCCESS(f"\nProceso completado. Se realizaron {asignados} asignaciones con éxito."))
        if pendientes_por_error > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"ADVERTENCIA: {pendientes_por_error} proyectos no pudieron ser asignados."
                )
            )
