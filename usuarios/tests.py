from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Proyecto, Carrera, Evaluacion, CriterioEvaluacion, DetalleEvaluacion

User = get_user_model()

class RubricaTestCase(TestCase):
    def setUp(self):
        # Crear usuarios de prueba
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
        
        # Crear carrera
        self.carrera = Carrera.objects.create(
            nombre='Ingeniería en Redes Inteligentes y Ciberseguridad',
            clave='IRIC'
        )
        
        # Crear proyecto
        self.proyecto = Proyecto.objects.create(
            titulo='Proyecto Ciberseguridad UTEQ',
            descripcion='Descripción del proyecto de prueba.',
            carrera=self.carrera,
            grupo='IRIC08',
            categoria='redes',
            creado_por=self.alumno,
            evaluador_asignado=self.docente
        )

        # Crear criterios de rúbrica
        self.criterio_inv = CriterioEvaluacion.objects.create(
            nombre='Innovación',
            descripcion='Nivel de novedad de la propuesta.',
            peso=0.40,
            activo=True
        )
        self.criterio_exp = CriterioEvaluacion.objects.create(
            nombre='Exposición',
            descripcion='Claridad en la defensa del proyecto.',
            peso=0.30,
            activo=True
        )
        self.criterio_via = CriterioEvaluacion.objects.create(
            nombre='Viabilidad',
            descripcion='Factibilidad de implementación técnica.',
            peso=0.30,
            activo=True
        )

    def test_calificacion_ponderada_rubrica_uteq(self):
        # 1. Crear evaluación base
        evaluacion = Evaluacion.objects.create(
            proyecto=self.proyecto,
            evaluador=self.docente,
            estatus_sugerido='aprobado',
            comentarios_evaluador='Excelente proyecto en general.'
        )

        # 2. Asignar notas parciales cualitativas (AU=10, DE=9, SA=8, NA=0)
        # Ponderación esperada:
        # Innovación: DE (9) -> 9.0 * 0.4 = 3.6
        # Exposición: AU (10) -> 10.0 * 0.3 = 3.0
        # Viabilidad: SA (8) -> 8.0 * 0.3 = 2.4
        # Promedio final = 3.6 + 3.0 + 2.4 = 9.0
        det1 = DetalleEvaluacion.objects.create(
            evaluacion=evaluacion,
            criterio=self.criterio_inv,
            calificacion_cualitativa='DE'
        )
        det2 = DetalleEvaluacion.objects.create(
            evaluacion=evaluacion,
            criterio=self.criterio_exp,
            calificacion_cualitativa='AU'
        )
        det3 = DetalleEvaluacion.objects.create(
            evaluacion=evaluacion,
            criterio=self.criterio_via,
            calificacion_cualitativa='SA'
        )

        # 3. Refrescar objetos de la base de datos
        evaluacion.refresh_from_db()
        self.proyecto.refresh_from_db()

        # 4. Validar conversiones numéricas individuales
        self.assertEqual(det1.calificacion_numerica, 9.00)
        self.assertEqual(det2.calificacion_numerica, 10.00)
        self.assertEqual(det3.calificacion_numerica, 8.00)

        # 5. Validar calificaciones calculadas finales
        self.assertEqual(float(evaluacion.calificacion), 9.00)
        self.assertEqual(float(self.proyecto.calificacion), 9.00)


from rest_framework.test import APITestCase
from rest_framework import status

class APIRESTTestCase(APITestCase):
    def setUp(self):
        # Crear usuarios de prueba
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
        
        # Crear carrera
        self.carrera = Carrera.objects.create(
            nombre='Ingeniería en Redes Inteligentes y Ciberseguridad',
            clave='IRIC'
        )
        
        # Crear criterios de rúbrica
        self.criterio_inv = CriterioEvaluacion.objects.create(
            nombre='Innovación',
            descripcion='Nivel de novedad de la propuesta.',
            peso=1.00,
            activo=True
        )

    def test_jwt_auth_workflow(self):
        # 1. Intentar login y obtener tokens
        login_url = '/api/token/'
        data = {
            'username': 'alumno.test',
            'password': 'Password123!'
        }
        response = self.client.post(login_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        access_token = response.data['access']

        # 2. Consultar perfil /me sin token (debe fallar)
        me_url = '/api/auth/me/'
        response_fail = self.client.get(me_url)
        self.assertEqual(response_fail.status_code, status.HTTP_401_UNAUTHORIZED)

        # 3. Consultar perfil /me con token (debe ser exitoso)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        response_success = self.client.get(me_url)
        self.assertEqual(response_success.status_code, status.HTTP_200_OK)
        self.assertEqual(response_success.data['username'], 'alumno.test')
        self.assertEqual(response_success.data['rol'], 'ALUMNO')

    def test_proyecto_crud_via_api(self):
        # Obtener token de alumno
        login_response = self.client.post('/api/token/', {
            'username': 'alumno.test',
            'password': 'Password123!'
        })
        token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        # Crear proyecto
        proyecto_data = {
            'titulo': 'Nuevo Proyecto API',
            'descripcion': 'Probando la creación de proyectos mediante DRF.',
            'carrera_id': self.carrera.id,
            'grupo': 'IRIC08',
            'categoria': 'software',
            'miembros': [
                {
                    'nombre_completo': 'Juan Perez',
                    'matricula': '20230001',
                    'correo': 'juan@uteq.edu.mx',
                    'es_lider': True
                },
                {
                    'nombre_completo': 'Ana Gomez',
                    'matricula': '20230002',
                    'correo': 'ana@uteq.edu.mx',
                    'es_lider': False
                }
            ]
        }
        
        response = self.client.post('/api/proyectos/', proyecto_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['titulo'], 'Nuevo Proyecto API')
        self.assertEqual(len(response.data['miembros']), 2)
        
        # Validar que los miembros se guardaron en la base de datos
        proyecto_id = response.data['id']
        proyecto_obj = Proyecto.objects.get(pk=proyecto_id)
        self.assertEqual(proyecto_obj.miembros.count(), 2)

    def test_evaluacion_via_api(self):
        # Crear un proyecto asignado al docente
        proyecto = Proyecto.objects.create(
            titulo='Proyecto Docente',
            descripcion='Proyecto asignado para evaluación.',
            carrera=self.carrera,
            creado_por=self.alumno,
            evaluador_asignado=self.docente
        )

        # Autenticar docente
        login_response = self.client.post('/api/token/', {
            'username': 'prof.test',
            'password': 'Password123!'
        })
        token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        # Enviar evaluación
        eval_data = {
            'proyecto': proyecto.id,
            'comentarios_evaluador': 'Muy buen proyecto experimental.',
            'estatus_sugerido': 'aprobado',
            'detalles': [
                {
                    'criterio_id': self.criterio_inv.id,
                    'calificacion_cualitativa': 'AU'
                }
            ]
        }

        response = self.client.post('/api/evaluaciones/', eval_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(float(response.data['calificacion']), 10.00)

        # Verificar en base de datos
        evaluacion_obj = Evaluacion.objects.get(proyecto=proyecto, evaluador=self.docente)
        self.assertEqual(evaluacion_obj.calificacion, 10.00)


class ProyectoEditTestCase(TestCase):
    def setUp(self):
        self.alumno = User.objects.create_user(
            username='alumno.edit',
            email='alumno.edit@uteq.edu.mx',
            password='Password123!',
            rol='ALUMNO'
        )
        self.otro_alumno = User.objects.create_user(
            username='alumno.otro',
            email='alumno.otro@uteq.edu.mx',
            password='Password123!',
            rol='ALUMNO'
        )
        self.carrera = Carrera.objects.create(
            nombre='DSM',
            clave='DSM'
        )
        # Proyecto en revisión del primer alumno
        self.proyecto = Proyecto.objects.create(
            titulo='Proyecto Original',
            descripcion='Descripción corta.',
            carrera=self.carrera,
            grupo='DSM4B',
            categoria='software',
            creado_por=self.alumno,
            estatus='revision'
        )
        
    def test_editar_proyecto_permissions_and_status(self):
        # 1. Intentar editar sin login (debe redirigir)
        url = f"/auth/mi-proyecto/{self.proyecto.pk}/editar/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        
        # 2. Intentar editar con otro alumno (debe dar 404 / no encontrado ya que get_object_or_404 filtra por creado_por=request.user)
        self.client.login(username='alumno.otro', password='Password123!')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        
        # 3. Intentar editar con el alumno creador cuando está en 'revision' (debe dar 200)
        self.client.login(username='alumno.edit', password='Password123!')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # 4. Cambiar estatus a 'aprobado' e intentar editar (debe dar 302 redirect con error)
        self.proyecto.estatus = 'aprobado'
        self.proyecto.save()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)


from decouple import config
from django.urls import reverse
from .models import EvaluacionExterna

class EvaluatorRegistrationTestCase(TestCase):
    def test_registro_evaluador_codigo_correcto(self):
        url = reverse('registro')
        data = {
            'first_name': 'Juan',
            'last_name': 'Perez',
            'email': 'juan.docente@uteq.edu.mx',
            'rol': 'EVALUADOR',
            'password': 'Password123!',
            'confirm_password': 'Password123!',
            'codigo_acceso_docente': config('CODIGO_REGISTRO_EVALUADOR', default='2011')
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('activar_cuenta'))
        user = User.objects.get(email='juan.docente@uteq.edu.mx')
        self.assertFalse(user.is_active)
        self.assertEqual(user.rol, 'EVALUADOR')

    def test_registro_evaluador_codigo_incorrecto(self):
        url = reverse('registro')
        data = {
            'first_name': 'Juan',
            'last_name': 'Perez',
            'email': 'juan.docente@uteq.edu.mx',
            'rol': 'EVALUADOR',
            'password': 'Password123!',
            'confirm_password': 'Password123!',
            'codigo_acceso_docente': 'WRONG_CODE'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Código de acceso docente incorrecto. Contacta al coordinador del evento.")


class EvaluacionExternaTestCase(TestCase):
    def setUp(self):
        self.alumno = User.objects.create_user(
            username='alumno.test',
            email='alumno@uteq.edu.mx',
            password='Password123!',
            rol='ALUMNO'
        )
        self.carrera = Carrera.objects.create(nombre='ISC', clave='ISC')
        self.proyecto = Proyecto.objects.create(
            titulo='Proyecto Visitantes',
            descripcion='Proyecto para testear visitas.',
            carrera=self.carrera,
            grupo='ISC8B',
            categoria='software',
            creado_por=self.alumno
        )

    def test_evaluacion_externa_workflow(self):
        url = reverse('evaluar_externo', args=[self.proyecto.id])
        
        # 1. GET request should return 200
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.proyecto.titulo)

        # 2. POST with wrong access code
        data = {
            'nombre_visitante': 'John Doe',
            'empresa_procedencia': 'Google',
            'correo_contacto': 'john.doe@gmail.com',
            'telefono_contacto': '1234567890',
            'calificacion': 'AU',
            'comentario': 'Excelente!',
            'codigo_acceso': 'WRONG'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Código de acceso incorrecto. Solicita el código correcto en el stand del proyecto.")
        self.assertFalse(EvaluacionExterna.objects.filter(correo_contacto='john.doe@gmail.com').exists())

        # 3. POST with correct access code
        data['codigo_acceso'] = config('CODIGO_EVALUACION_EXTERNA', default='UTEQ2025')
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "¡Evaluación Registrada!")
        
        # Verify db
        eval_ext = EvaluacionExterna.objects.get(correo_contacto='john.doe@gmail.com')
        self.assertEqual(eval_ext.calificacion, 'AU')
        self.assertEqual(eval_ext.get_valor_numerico(), 10)

        # 4. POST duplicate email evaluation
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Este correo electrónico ya ha registrado una evaluación para este proyecto.")


class LogActividadTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='admin.log',
            email='admin.log@uteq.edu.mx',
            password='Password123!',
            rol='ADMIN'
        )

    def test_log_creation(self):
        from .models import LogActividad
        log = LogActividad.objects.create(
            usuario=self.user,
            tipo='login',
            descripcion='Prueba de inicio de sesión',
            ip='127.0.0.1'
        )
        self.assertEqual(log.usuario, self.user)
        self.assertEqual(log.tipo, 'login')
        self.assertEqual(log.ip, '127.0.0.1')
        self.assertTrue("Inicio de sesión" in str(log))

    def test_admin_logs_view_restricted(self):
        from django.urls import reverse
        # Alumno no debe poder entrar
        alumno = User.objects.create_user(
            username='alumno.log',
            email='alumno.log@uteq.edu.mx',
            password='Password123!',
            rol='ALUMNO'
        )
        self.client.login(username='alumno.log', password='Password123!')
        response = self.client.get(reverse('admin_logs'))
        self.assertEqual(response.status_code, 302) # Redirect to index

    def test_admin_logs_view_allowed(self):
        from django.urls import reverse
        self.client.login(username='admin.log', password='Password123!')
        response = self.client.get(reverse('admin_logs'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'usuarios/admin_logs.html')


class Superuser2FABypassTestCase(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='superadmin',
            email='',
            password='Password123!'
        )

    def test_superuser_login_bypasses_2fa(self):
        from django.urls import reverse
        response = self.client.post(reverse('login'), {
            'username': 'superadmin',
            'password': 'Password123!'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('index'))
        self.assertIn('_auth_user_id', self.client.session)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.superuser.id)

    def test_superuser_verificar_2fa_safeguard(self):
        from django.urls import reverse
        session = self.client.session
        session['pre_auth_user_id'] = self.superuser.id
        session['codigo_2fa_correcto'] = '123456'
        session.save()

        response = self.client.get(reverse('verificar_2fa'))
        self.assertRedirects(response, reverse('index'))
        self.assertIn('_auth_user_id', self.client.session)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.superuser.id)


class LandingPageTestCase(TestCase):
    def setUp(self):
        self.alumno = User.objects.create_user(
            username='alumno.landing',
            email='alumno.landing@uteq.edu.mx',
            password='Password123!',
            rol='ALUMNO'
        )

    def test_anonymous_user_access_landing_page(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'landing_home.html')

    def test_anonymous_user_redirected_from_dashboard(self):
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/')

    def test_authenticated_user_redirected_from_landing(self):
        self.client.login(username='alumno.landing', password='Password123!')
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/dashboard/')

    def test_authenticated_user_access_dashboard(self):
        self.client.login(username='alumno.landing', password='Password123!')
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'seguridad/index.html')

    def test_landing_funciona_page_access(self):
        response = self.client.get('/como-funciona/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'landing_funciona.html')

    def test_landing_faq_page_access(self):
        response = self.client.get('/faq/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'landing_faq.html')

    def test_landing_contacto_page_access(self):
        response = self.client.get('/contacto/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'landing_contacto.html')


class ContactoTestCase(TestCase):
    def test_contacto_form_submission_success(self):
        from django.urls import reverse
        from django.core import mail
        response = self.client.post(reverse('contacto_enviar'), {
            'nombre': 'Luis Ángel',
            'correo': 'luis@gmail.com',
            'asunto': 'Duda de registro',
            'mensaje': 'Hola, tengo una pregunta sobre el registro de proyectos.'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'ok': True})
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, '[ConEvent] Contacto: Duda de registro')
        self.assertIn('Luis Ángel', mail.outbox[0].body)

    def test_contacto_form_submission_incomplete(self):
        from django.urls import reverse
        response = self.client.post(reverse('contacto_enviar'), {
            'nombre': 'Luis Ángel',
            'correo': '',
            'asunto': '',
            'mensaje': ''
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'ok': False, 'error': 'Campos incompletos'})




