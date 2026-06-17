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
