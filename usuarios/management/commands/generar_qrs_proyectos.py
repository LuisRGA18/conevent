from django.core.management.base import BaseCommand
from usuarios.models import Proyecto
from usuarios.views import generar_qr_externo_proyecto
from decouple import config

class Command(BaseCommand):
    help = 'Genera los códigos QR de evaluación externa para los proyectos que no lo tienen de forma retroactiva.'

    def handle(self, *args, **options):
        base_url = config('SITE_URL', default='http://127.0.0.1:8000')
        
        # Consultar proyectos que tengan el campo qr_evaluacion_externa vacío
        proyectos = Proyecto.objects.filter(qr_evaluacion_externa='').distinct() | Proyecto.objects.filter(qr_evaluacion_externa__isnull=True).distinct()
        
        # Filtrar duplicados reales que puedan surgir del OR de QuerySets
        proyectos = list(set(proyectos))
        
        self.stdout.write(f"Se encontraron {len(proyectos)} proyectos sin código QR.")
        
        count = 0
        for p in proyectos:
            try:
                generar_qr_externo_proyecto(p, base_url)
                count += 1
                self.stdout.write(self.style.SUCCESS(f"QR generado con éxito para el proyecto {p.id} ({p.titulo})"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error generando QR para el proyecto {p.id}: {str(e)}"))
                
        self.stdout.write(self.style.SUCCESS(f"Proceso completado. Se generaron {count} códigos QR."))
