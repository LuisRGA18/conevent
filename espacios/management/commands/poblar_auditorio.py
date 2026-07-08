from django.core.management.base import BaseCommand
from espacios.models import Stand

class Command(BaseCommand):
    help = 'Pobla el auditorio principal con stands estándar en las filas 1 a 10 con coordenadas correctas.'

    def handle(self, *args, **options):
        created_count = 0
        for fila in range(1, 11):
            # Zona A: filas 1-4, Zona B: filas 5-8, Zona C: filas 9-10
            if 1 <= fila <= 4:
                zona_letra = 'A'
                base_idx = (fila - 1) * 7
            elif 5 <= fila <= 8:
                zona_letra = 'B'
                base_idx = (fila - 5) * 7
            else:
                zona_letra = 'C'
                base_idx = (fila - 9) * 7
                
            for col in range(1, 8):
                numero_identificador = f"{zona_letra}-{base_idx + col:02d}"
                stand, created = Stand.objects.get_or_create(
                    numero=numero_identificador,
                    defaults={
                        'zona': 'auditorio',
                        'pos_fila': fila,
                        'pos_col': col,
                        'capacidad_proyectos': 1,
                        'esta_activo': True,
                        'descripcion': f'Stand estándar {numero_identificador} en fila {fila}, columna {col}'
                    }
                )
                if created:
                    created_count += 1
                    
        self.stdout.write(self.style.SUCCESS(f"Se crearon {created_count} stands nuevos en el auditorio principal."))
