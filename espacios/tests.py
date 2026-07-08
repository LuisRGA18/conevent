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


class EspaciosMejorasTestCase(TestCase):
    def setUp(self):
        # Crear usuarios
        self.admin = User.objects.create_user(
            username='admin.mejoras', password='Password123!', rol='ADMIN'
        )
        self.alumno = User.objects.create_user(
            username='alumno.mejoras', password='Password123!', rol='ALUMNO'
        )
        self.alumno2 = User.objects.create_user(
            username='alumno2.mejoras', password='Password123!', rol='ALUMNO'
        )
        self.carrera = Carrera.objects.create(nombre='ISC', clave='ISC')

        # Proyectos
        self.p_2mesas = Proyecto.objects.create(
            titulo='Proyecto 2 Mesas',
            carrera=self.carrera,
            creado_por=self.alumno,
            estatus='aprobado',
            mesas_requeridas=2
        )
        self.p_3mesas_unauth = Proyecto.objects.create(
            titulo='Proyecto 3 Mesas Unauth',
            carrera=self.carrera,
            creado_por=self.alumno2,
            estatus='aprobado',
            mesas_requeridas=3,
            mesas_autorizadas=False
        )
        self.p_3mesas_auth = Proyecto.objects.create(
            titulo='Proyecto 3 Mesas Auth',
            carrera=self.carrera,
            creado_por=self.admin, # just a different user
            estatus='aprobado',
            mesas_requeridas=3,
            mesas_autorizadas=True
        )

    def test_poblar_auditorio_command(self):
        # Eliminar stands previos para verificar conteo exacto
        Stand.objects.filter(zona='auditorio').delete()
        call_command('poblar_auditorio')
        
        self.assertEqual(Stand.objects.filter(zona='auditorio').count(), 70)
        
        # Verificar coordenadas y nombres de los extremos
        s_a01 = Stand.objects.get(numero='A-01')
        self.assertEqual(s_a01.pos_fila, 1)
        self.assertEqual(s_a01.pos_col, 1)
        
        s_c14 = Stand.objects.get(numero='C-14')
        self.assertEqual(s_c14.pos_fila, 10)
        self.assertEqual(s_c14.pos_col, 7)

    def test_asignar_stands_multimesas_contiguas(self):
        # Crear stands libres consecutivos
        Stand.objects.all().delete()
        stands = []
        for col in range(1, 8):
            stands.append(Stand.objects.create(
                numero=f"M-{col:02d}",
                pos_fila=1,
                pos_col=col,
                zona='auditorio',
                esta_activo=True
            ))

        # Ejecutar asignación
        call_command('asignar_stands')

        # 1. Proyecto 3 mesas sin autorización: omitido, no tiene stands asignados
        self.assertEqual(self.p_3mesas_unauth.asignaciones_stands.count(), 0)

        # 2. Proyecto 2 mesas: recibe 2 stands contiguos (M-01, M-02)
        asigs_2mesas = list(self.p_2mesas.asignaciones_stands.all().order_by('stand__pos_col'))
        self.assertEqual(len(asigs_2mesas), 2)
        self.assertEqual(asigs_2mesas[0].stand.numero, 'M-01')
        self.assertEqual(asigs_2mesas[1].stand.numero, 'M-02')

        # 3. Proyecto 3 mesas con autorización: recibe 3 stands contiguos (M-03, M-04, M-05)
        asigs_3mesas = list(self.p_3mesas_auth.asignaciones_stands.all().order_by('stand__pos_col'))
        self.assertEqual(len(asigs_3mesas), 3)
        self.assertEqual(asigs_3mesas[0].stand.numero, 'M-03')
        self.assertEqual(asigs_3mesas[1].stand.numero, 'M-04')
        self.assertEqual(asigs_3mesas[2].stand.numero, 'M-05')

    def test_solicitud_cambio_stand_alumno(self):
        # Asignar un stand de prueba
        stand = Stand.objects.create(numero='X-01', pos_fila=1, pos_col=1, zona='gimnasio')
        asig = AsignacionStand.objects.create(stand=stand, proyecto=self.p_2mesas)

        # Iniciar sesión alumno
        self.client.login(username='alumno.mejoras', password='Password123!')
        
        # Hacer POST a la vista de solicitar cambio
        url = reverse('solicitar_cambio_stand')
        response = self.client.post(url, {'motivo_cambio': 'Requerimos más flujo de personas.'})
        
        self.assertEqual(response.status_code, 302)
        
        asig.refresh_from_db()
        self.assertTrue(asig.cambio_solicitado)
        self.assertEqual(asig.motivo_cambio, 'Requerimos más flujo de personas.')

    def test_procesar_cambio_stand_admin_aprobar(self):
        # Asignar un stand
        stand = Stand.objects.create(numero='X-02', pos_fila=1, pos_col=1, zona='gimnasio')
        asig = AsignacionStand.objects.create(stand=stand, proyecto=self.p_2mesas, cambio_solicitado=True, motivo_cambio='Test')

        # Login admin
        self.client.login(username='admin.mejoras', password='Password123!')

        # Aprobar
        url = reverse('procesar_cambio_stand', args=[asig.id, 'aprobar'])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)

        # El stand debe quedar libre (la asignación se elimina)
        self.assertEqual(self.p_2mesas.asignaciones_stands.count(), 0)

    def test_procesar_cambio_stand_admin_rechazar(self):
        # Asignar un stand
        stand = Stand.objects.create(numero='X-03', pos_fila=1, pos_col=1, zona='gimnasio')
        asig = AsignacionStand.objects.create(stand=stand, proyecto=self.p_2mesas, cambio_solicitado=True, motivo_cambio='Test')

        # Login admin
        self.client.login(username='admin.mejoras', password='Password123!')

        # Rechazar
        url = reverse('procesar_cambio_stand', args=[asig.id, 'rechazar'])
        response = self.client.post(url, {'motivo_rechazo': 'No hay más espacio disponible en esa fila.'})
        self.assertEqual(response.status_code, 302)

        asig.refresh_from_db()
        self.assertTrue(asig.cambio_solicitado)
        self.assertFalse(asig.cambio_autorizado)
        self.assertEqual(asig.motivo_rechazo, 'No hay más espacio disponible en esa fila.')


