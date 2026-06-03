from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings


class Usuario(AbstractUser):
    ROLE_CHOICES = (
        ('ADMIN', 'Administrador de Evento'),
        ('EVALUADOR', 'Docente Evaluador'),
        ('ALUMNO', 'Alumno Participante'),
    )

    rol = models.CharField(
        max_length=15,
        choices=ROLE_CHOICES,
        default='ALUMNO'
    )
    matricula_empleado = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        unique=True,
        help_text="Matrícula del alumno o número de empleado del docente"
    )

    def __str__(self):
        return f"{self.username} - {self.get_rol_display()}"

    @property
    def es_admin(self):
        return self.rol == 'ADMIN'

    @property
    def es_evaluador(self):
        return self.rol == 'EVALUADOR'

    @property
    def es_alumno(self):
        return self.rol == 'ALUMNO'


class Carrera(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    clave = models.CharField(max_length=20, unique=True)

    class Meta:
        verbose_name = "Carrera"
        verbose_name_plural = "Carreras"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Proyecto(models.Model):
    ESTATUS_CHOICES = [
        ('revision', 'En Revisión'),
        ('aprobado', 'Aprobado'),
        ('rechazado', 'Rechazado'),
    ]
    CATEGORIA_CHOICES = [
        ('software', 'Desarrollo de Software'),
        ('hardware', 'Hardware / Electrónica'),
        ('redes', 'Redes y Telecomunicaciones'),
        ('ia', 'Inteligencia Artificial'),
        ('otro', 'Otro'),
    ]

    titulo = models.CharField(max_length=200, verbose_name="Título del Proyecto")
    descripcion = models.TextField(verbose_name="Descripción o Resumen")

    # NUEVO: campo de texto para integrantes se mantiene como respaldo,
    # pero ahora también hay modelo Integrante relacionado
    integrantes = models.TextField(
        help_text="Nombres de los integrantes separados por comas",
        verbose_name="Integrantes (texto)",
        blank=True
    )

    carrera = models.ForeignKey(
        Carrera,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='proyectos',
        verbose_name="Carrera"
    )
    grupo = models.CharField(
        max_length=10,
        blank=True,
        verbose_name="Grupo / Paralelo",
        help_text='Ej: "A", "4B"'
    )
    categoria = models.CharField(
        max_length=20,
        choices=CATEGORIA_CHOICES,
        default='software',
        verbose_name="Categoría"
    )

    alumno_creador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="proyectos"
    )
    evaluador_asignado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="proyectos_a_evaluar",
        limit_choices_to={'rol': 'EVALUADOR'},
        verbose_name="Evaluador Asignado"
    )

    estatus = models.CharField(
        max_length=20,
        choices=ESTATUS_CHOICES,
        default='revision'
    )
    calificacion = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Calificación Final"
    )
    comentarios_evaluador = models.TextField(
        null=True,
        blank=True,
        verbose_name="Comentarios del Profesor"
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Proyecto"
        verbose_name_plural = "Proyectos"
        ordering = ['-fecha_registro']

    def __str__(self):
        return self.titulo

    @property
    def codigo(self):
        return f"EQU-{self.pk:03d}"

    @property
    def num_integrantes(self):
        return self.miembros.count()


class Integrante(models.Model):
    proyecto = models.ForeignKey(
        Proyecto,
        on_delete=models.CASCADE,
        related_name='miembros'
    )
    nombre_completo = models.CharField(max_length=150, verbose_name="Nombre Completo")
    matricula = models.CharField(max_length=20, verbose_name="Matrícula")
    correo = models.EmailField(verbose_name="Correo Institucional")
    es_lider = models.BooleanField(default=False, verbose_name="¿Es líder?")

    class Meta:
        verbose_name = "Integrante"
        verbose_name_plural = "Integrantes"
        ordering = ['-es_lider', 'nombre_completo']
        constraints = [
            models.UniqueConstraint(
                fields=['proyecto', 'matricula'],
                name='unique_matricula_por_proyecto'
            )
        ]

    def __str__(self):
        return f"{self.nombre_completo} ({'Líder' if self.es_lider else 'Integrante'})"