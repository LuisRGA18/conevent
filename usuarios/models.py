from django.contrib.auth.models import AbstractUser
from django.db import models

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