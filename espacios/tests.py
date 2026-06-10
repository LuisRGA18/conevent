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
