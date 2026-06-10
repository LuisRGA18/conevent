from django.db import models
from django.conf import settings

class Stand(models.Model):
    ZONA_CHOICES = [
        ('gimnasio', 'Gimnasio UTEQ'),
        ('auditorio', 'Auditorio principal'),
        ('pasillo_a', 'Pasillo Edificio A'),
        ('pasillo_b', 'Pasillo Edificio B'),
        ('exterior', 'Explanada / Exterior'),
        ('otro', 'Otro / Sala alterna'),
    ]

    numero = models.CharField(max_length=20, unique=True, verbose_name="Número / Identificador del Stand")
    zona = models.CharField(max_length=20, choices=ZONA_CHOICES, default='gimnasio', verbose_name="Zona física")
    capacidad_proyectos = models.PositiveIntegerField(default=1, verbose_name="Capacidad de proyectos simultáneos")
    descripcion = models.TextField(blank=True, verbose_name="Detalles adicionales del espacio")
    esta_activo = models.BooleanField(default=True, verbose_name="Disponible para asignación")

    class Meta:
        verbose_name = "Stand / Espacio"
        verbose_name_plural = "Stands / Espacios"
        ordering = ['zona', 'numero']

    def __str__(self):
        return f"{self.get_zona_display()} - Stand {self.numero}"


class AsignacionStand(models.Model):
    # Un stand físico individual solo puede asignarse a un único proyecto para evitar colisiones.
    # Sin embargo, un proyecto puede tener asignados múltiples stands (por ejemplo, si necesitan hasta 2 mesas/stands).
    # Por lo tanto, stand es OneToOneField y proyecto es ForeignKey.
    stand = models.OneToOneField(
        Stand, 
        on_delete=models.CASCADE, 
        related_name='asignacion', 
        verbose_name="Stand / Mesa física",
        limit_choices_to={'esta_activo': True}
    )
    proyecto = models.ForeignKey(
        'usuarios.Proyecto', 
        on_delete=models.CASCADE, 
        related_name='asignaciones_stands', 
        verbose_name="Proyecto asignado"
    )
    fecha_asignacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de asignación")
    comentarios = models.TextField(blank=True, verbose_name="Comentarios de asignación")

    class Meta:
        verbose_name = "Asignación de Stand"
        verbose_name_plural = "Asignaciones de Stands"
        ordering = ['-fecha_asignacion']

    def __str__(self):
        return f"Stand {self.stand.numero} -> {self.proyecto.titulo}"

# ──────────────────────────────────────────────────────────────
# CARGA ACADÉMICA DOCENTE (Para Asignación Automática RF3)
# ──────────────────────────────────────────────────────────────

class CargaDocente(models.Model):
    docente = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='grupos_impartidos',
        limit_choices_to={'rol': 'EVALUADOR'},
        verbose_name="Docente Evaluador"
    )
    # Almacena el código del grupo, ej: "IRIC08", "DSM20"
    codigo_grupo = models.CharField(max_length=10, verbose_name="Código del Grupo a evaluar")

    class Meta:
        verbose_name = "Carga Académica Docente"
        verbose_name_plural = "Cargas Académicas de Docentes"
        # Evita que el mismo profesor registre el mismo grupo dos veces
        constraints = [
            models.UniqueConstraint(fields=['docente', 'codigo_grupo'], name='unique_grupo_por_docente')
        ]

    def __str__(self):
        return f"{self.docente.username} -> Grupo {self.codigo_grupo}"