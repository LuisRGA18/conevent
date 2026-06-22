from django.test import TestCase
from django.contrib.auth import get_user_model
from usuarios.models import Proyecto, Carrera
from .models import Stand, AsignacionStand

User = get_user_model()

class EspaciosTestCase(TestCase):
    def setUp(self):
        # Crear usuario
        self.user = User.objects.create_user(
            username='teststudent',
            email='test@uteq.edu.mx',
            password='Password123!',
            rol='ALUMNO'
        )
        # Crear carrera
        self.carrera = Carrera.objects.create(
            nombre='Ingeniería en Software',
            clave='ISW'
        )
        # Crear proyecto
        self.proyecto = Proyecto.objects.create(
            titulo='Proyecto Test de Software',
            descripcion='Descripción corta del proyecto de prueba.',
            carrera=self.carrera,
            grupo='4B',
            categoria='software',
            creado_por=self.user
        )

    def test_creacion_stand(self):
        stand = Stand.objects.create(
            numero='A-10',
            zona='gimnasio',
            capacidad_proyectos=1
        )
        self.assertEqual(str(stand), 'Gimnasio UTEQ - Stand A-10')

    def test_asignacion_stand(self):
        stand = Stand.objects.create(
            numero='A-11',
            zona='gimnasio',
            capacidad_proyectos=1
        )
        asignacion = AsignacionStand.objects.create(
            stand=stand,
            proyecto=self.proyecto,
            comentarios='Mesa principal'
        )
        self.assertEqual(asignacion.stand, stand)
        self.assertEqual(asignacion.proyecto, self.proyecto)
        self.assertEqual(stand.asignacion.proyecto, self.proyecto)


from rest_framework.test import APITestCase
from rest_framework import status
from django.core.management import call_command

class EspaciosAPITestCase(APITestCase):
    def setUp(self):
        # Crear usuarios
        self.admin = User.objects.create_user(
            username='admin.test', password='Password123!', rol='ADMIN'
        )
        self.alumno = User.objects.create_user(
            username='alumno.test', password='Password123!', rol='ALUMNO'
        )
        # Carreras
        self.carrera_dsm = Carrera.objects.create(nombre='DSM', clave='DSM')
        self.carrera_iric = Carrera.objects.create(nombre='IRIC', clave='IRIC')
        
        # Proyectos aprobados
        self.p1 = Proyecto.objects.create(
            titulo='DSM Proy 1', carrera=self.carrera_dsm, creado_por=self.alumno, estatus='aprobado'
        )
        self.p2 = Proyecto.objects.create(
            titulo='DSM Proy 2', carrera=self.carrera_dsm, creado_por=self.alumno, estatus='aprobado'
        )
        self.p3 = Proyecto.objects.create(
            titulo='IRIC Proy 1', carrera=self.carrera_iric, creado_por=self.alumno, estatus='aprobado'
        )
        
        # Stands con coordenadas en orden geométrico
        self.s1 = Stand.objects.create(numero='M-01', pos_fila=1, pos_col=1, zona='auditorio')
        self.s2 = Stand.objects.create(numero='M-02', pos_fila=1, pos_col=2, zona='auditorio')
        self.s3 = Stand.objects.create(numero='M-03', pos_fila=1, pos_col=3, zona='auditorio')

    def test_mapa_api_endpoint(self):
        # Autenticar
        self.client.force_authenticate(user=self.alumno)
        response = self.client.get('/api/stands/mapa/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assertEqual(response.data[0]['numero'], 'M-01')
        self.assertIsNone(response.data[0]['proyecto_asignado'])

    def test_asignar_stands_command(self):
        # Verificar que no existen asignaciones previas
        self.assertEqual(AsignacionStand.objects.count(), 0)
        
        # Ejecutar el comando
        call_command('asignar_stands')
        
        # Verificar asignaciones creadas
        self.assertEqual(AsignacionStand.objects.count(), 3)
        
        # Obtener asignaciones individuales
        asig_p1 = AsignacionStand.objects.get(proyecto=self.p1)
        asig_p2 = AsignacionStand.objects.get(proyecto=self.p2)
        asig_p3 = AsignacionStand.objects.get(proyecto=self.p3)
        
        # Validar la contigüidad física: p1 y p2 de DSM se asignan en M-01 y M-02
        # p3 de IRIC se asigna en M-03
        self.assertIn(asig_p1.stand.numero, ['M-01', 'M-02'])
        self.assertIn(asig_p2.stand.numero, ['M-01', 'M-02'])
        self.assertEqual(asig_p3.stand.numero, 'M-03')


from django.urls import reverse

class StandsGestionTestCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin.stands',
            email='admin.stands@uteq.edu.mx',
            password='Password123!',
            rol='ADMIN'
        )
        self.alumno = User.objects.create_user(
            username='alumno.stands',
            email='alumno.stands@uteq.edu.mx',
            password='Password123!',
            rol='ALUMNO'
        )
        self.stand = Stand.objects.create(
            numero='B-01',
            zona='gimnasio',
            pos_fila=1,
            pos_col=1,
            esta_activo=True
        )

    def test_gestionar_stands_acceso(self):
        url = reverse('espacios:gestionar_stands')
        
        # 1. Alumno de ejemplo no puede acceder (debe redirigir a index con mensaje de error)
        self.client.login(username='alumno.stands', password='Password123!')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        
        # 2. Administrador sí puede acceder
        self.client.login(username='admin.stands', password='Password123!')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'B-01')

    def test_crear_stand_via_post(self):
        url = reverse('espacios:gestionar_stands')
        self.client.login(username='admin.stands', password='Password123!')
        
        data = {
            'numero': 'B-02',
            'zona': 'gimnasio',
            'pos_fila': '2',
            'pos_col': '2',
            'descripcion': 'Mesa auxiliar'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302) # Redirect to self
        
        # Verify db
        self.assertTrue(Stand.objects.filter(numero='B-02').exists())

    def test_toggle_stand_view(self):
        url = reverse('espacios:toggle_stand', args=[self.stand.id])
        self.client.login(username='admin.stands', password='Password123!')
        
        # Toggle to inactive
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        
        self.stand.refresh_from_db()
        self.assertFalse(self.stand.esta_activo)

    def test_asignar_stands_automatico_view(self):
        url = reverse('espacios:asignar_stands_automatico')
        self.client.login(username='admin.stands', password='Password123!')
        
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)

