from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from usuarios.models import Proyecto, Carrera
from espacios.models import Stand, AsignacionStand
from inventario.models import ItemInventario, Incidencia

User = get_user_model()

class ReportesAPITestCase(APITestCase):
    def setUp(self):
        # 1. Crear usuarios
        self.admin = User.objects.create_user(
            username='admin.test',
            email='admin@uteq.edu.mx',
            password='Password123!',
            rol='ADMIN'
        )
        self.docente = User.objects.create_user(
            username='prof.test',
            email='prof@uteq.edu.mx',
            password='Password123!',
            rol='EVALUADOR'
        )
        self.alumno = User.objects.create_user(
            username='alumno.test',
            email='alumno@uteq.edu.mx',
            password='Password123!',
            rol='ALUMNO'
        )
        
        # 2. Crear carrera y proyecto
        self.carrera = Carrera.objects.create(
            nombre='Ingeniería en Tecnologías de la Información',
            clave='ITI'
        )
        self.proyecto = Proyecto.objects.create(
            titulo='Proyecto Invernadero Automatizado',
            descripcion='Monitoreo de humedad y temperatura.',
            carrera=self.carrera,
            grupo='ITI08',
            categoria='hardware',
            creado_por=self.alumno,
            calificacion=9.50
        )
        
        # 3. Crear stand y asignación
        self.stand = Stand.objects.create(
            numero='A-12',
            zona='gimnasio',
            esta_activo=True
        )
        self.asignacion = AsignacionStand.objects.create(
            stand=self.stand,
            proyecto=self.proyecto,
            comentarios='Requiere conexión eléctrica bifásica'
        )
        
        # 4. Crear item de inventario e incidencia
        self.item = ItemInventario.objects.create(
            nombre='Mesa plegable',
            estado='bueno',
            stand_asignado=self.stand
        )
        self.incidencia = Incidencia.objects.create(
            item=self.item,
            titulo='Pata floja',
            descripcion='La mesa se tambalea.',
            prioridad='media',
            reportado_por=self.alumno,
            resuelta=False
        )

    def test_dashboard_report_requires_auth(self):
        # Intentar consultar sin token
        response = self.client.get('/api/reportes/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_dashboard_report_for_student_fails(self):
        # Autenticar como alumno
        login_response = self.client.post('/api/token/', {
            'username': 'alumno.test',
            'password': 'Password123!'
        })
        token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Consultar dashboard (debe denegar por ser alumno)
        response = self.client.get('/api/reportes/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_dashboard_report_for_admin_succeeds(self):
        # Autenticar como admin
        login_response = self.client.post('/api/token/', {
            'username': 'admin.test',
            'password': 'Password123!'
        })
        token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Consultar dashboard
        response = self.client.get('/api/reportes/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar estructura de datos
        self.assertIn('metricas_generales', response.data)
        self.assertIn('proyectos_por_categoria', response.data)
        self.assertIn('proyectos_por_carrera', response.data)
        self.assertIn('calif_promedio_por_carrera', response.data)
        self.assertIn('top_proyectos', response.data)
        self.assertIn('stands_por_zona', response.data)
        self.assertIn('incidencias_por_prioridad', response.data)
        
        # Verificar valores concretos
        mg = response.data['metricas_generales']
        self.assertEqual(mg['total_proyectos'], 1)
        self.assertEqual(mg['proyectos_evaluados'], 1)
        self.assertEqual(mg['stands_ocupados'], 1)
        self.assertEqual(mg['incidencias_activas'], 1)

    def test_export_csv_succeeds(self):
        # Autenticar como docente
        login_response = self.client.post('/api/token/', {
            'username': 'prof.test',
            'password': 'Password123!'
        })
        token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Solicitar descarga CSV
        response = self.client.get('/api/reportes/exportar/calificaciones/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertTrue(response['Content-Disposition'].startswith('attachment; filename='))
        
        # Decodificar el contenido (saltando el BOM UTF-8)
        content = response.content.decode('utf-8-sig')
        self.assertIn('Proyecto Invernadero Automatizado', content)
        self.assertIn('ITI', content)
        self.assertIn('9.5', content)

    def test_visual_dashboard_view_permissions(self):
        # 1. Alumno intenta entrar (debe redirigir/fallar)
        self.client.login(username='alumno.test', password='Password123!')
        response = self.client.get('/reportes/dashboard/')
        self.assertEqual(response.status_code, 302) # Redirige con error
        
        # 2. Docente intenta entrar (debe ser exitoso)
        self.client.login(username='prof.test', password='Password123!')
        response = self.client.get('/reportes/dashboard/')
        self.assertEqual(response.status_code, 200)
        
        # 3. Admin intenta entrar (debe ser exitoso)
        self.client.login(username='admin.test', password='Password123!')
        response = self.client.get('/reportes/dashboard/')
        self.assertEqual(response.status_code, 200)

    def test_exportar_calificaciones_pdf_permissions(self):
        # 1. Docente intenta entrar (debe redirigir/fallar)
        self.client.login(username='prof.test', password='Password123!')
        response = self.client.get('/reportes/exportar/calificaciones/pdf/')
        self.assertEqual(response.status_code, 302) # Redirige por no tener permisos de admin
        
        # 2. Admin intenta entrar (debe generar el PDF)
        self.client.login(username='admin.test', password='Password123!')
        response = self.client.get('/reportes/exportar/calificaciones/pdf/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response['Content-Disposition'].startswith('attachment; filename='))
