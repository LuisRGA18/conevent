from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings

class Usuario(AbstractUser):
    # Definimos las opciones de roles utilizando una tupla
    ROLE_CHOICES = (
        ('ADMIN', 'Administrador de Evento'),
        ('EVALUADOR', 'Docente Evaluador'),
        ('ALUMNO', 'Alumno Participante'),
    )
    
    # Añadimos el campo de rol a la tabla de usuarios
    rol = models.CharField(
        max_length=15, 
        choices=ROLE_CHOICES, 
        default='ALUMNO'
    )
    
    # Campos adicionales útiles para la UTEQ
    matricula_empleado = models.CharField(
        max_length=20, 
        blank=True, 
        null=True, 
        unique=True,
        help_text="Matrícula del alumno o número de empleado del docente"
    )

    def __str__(self):
        return f"{self.username} - {self.get_rol_display()}"

class Proyecto(models.Model):
    ESTATUS_CHOICES = [
        ('revision', 'En Revisión'),
        ('aprobado', 'Aprobado'),
        ('rechazado', 'Rechazado'),
    ]

    titulo = models.CharField(max_length=200, verbose_name="Título del Proyecto")
    descripcion = models.TextField(verbose_name="Descripción o Resumen")
    integrantes = models.TextField(help_text="Nombres de los integrantes separados por comas", verbose_name="Integrantes")
    alumno_creador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="proyectos")
    estatus = models.CharField(max_length=20, choices=ESTATUS_CHOICES, default='revision')
    calificacion = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, verbose_name="Calificación Final")
    comentarios_evaluador = models.TextField(null=True, blank=True, verbose_name="Comentarios del Profesor")
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titulo