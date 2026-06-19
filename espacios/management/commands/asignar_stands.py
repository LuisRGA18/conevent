from django.core.management.base import BaseCommand
from usuarios.models import Proyecto
from espacios.models import Stand, AsignacionStand

class Command(BaseCommand):
    help = "Asigna automáticamente stands a proyectos aprobados agrupándolos contiguamente por carrera"

    def handle(self, *args, **options):
        # 1. Obtener proyectos aprobados que no tienen stand asignado
        # Usamos select_related('carrera') para evitar múltiples consultas y ordenar por carrera
        proyectos = Proyecto.objects.filter(
            estatus='aprobado',
            asignaciones_stands__isnull=True
        ).select_related('carrera').order_by('carrera_id', 'titulo')

        if not proyectos.exists():
            self.stdout.write(self.style.SUCCESS("No hay proyectos aprobados pendientes de asignación de stand."))
            return

        # 2. Obtener stands activos y libres
        # Ordenamos por zona, fila y columna para asegurar posiciones contiguas consecutivas
        stands_libres = Stand.objects.filter(
            esta_activo=True,
            asignacion__isnull=True
        ).order_by('zona', 'pos_fila', 'pos_col')

        if not stands_libres.exists():
            self.stdout.write(self.style.ERROR("No hay stands disponibles libres para asignación."))
            return

        self.stdout.write(f"Proyectos pendientes por asignar: {proyectos.count()}")
        self.stdout.write(f"Stands disponibles: {stands_libres.count()}")

        # 3. Asignación secuencial (zipper) para garantizar la contigüidad
        asignados = 0
        exceso_proyectos = False

        for proy, stand in zip(proyectos, stands_libres):
            AsignacionStand.objects.create(
                stand=stand,
                proyecto=proy,
                comentarios="Asignación automática por carrera"
            )
            carrera_clave = proy.carrera.clave if proy.carrera else "S/C"
            self.stdout.write(
                self.style.SUCCESS(
                    f"Asignado: '{proy.titulo}' [{carrera_clave}] -> Stand {stand.numero} (Zona: {stand.get_zona_display()}, Fila: {stand.pos_fila}, Col: {stand.pos_col})"
                )
            )
            asignados += 1

        self.stdout.write(self.style.SUCCESS(f"\nProceso completado. Se realizaron {asignados} asignaciones con éxito."))

        if proyectos.count() > stands_libres.count():
            pendientes = proyectos.count() - stands_libres.count()
            self.stdout.write(
                self.style.WARNING(
                    f"ADVERTENCIA: {pendientes} proyectos no pudieron ser asignados por falta de stands libres."
                )
            )
