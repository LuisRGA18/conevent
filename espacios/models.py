from django.db import models
from django.conf import settings

class Recinto(models.Model):
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    direccion = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Recinto"


class Planta(models.Model):
    recinto = models.ForeignKey(
        Recinto, on_delete=models.CASCADE, related_name='plantas'
    )
    nombre = models.CharField(max_length=100)  # "Planta Baja", "Planta Alta"
    nivel = models.PositiveIntegerField(default=0)  # 0=PB, 1=PA
    filas = models.PositiveIntegerField(default=7)
    columnas = models.PositiveIntegerField(default=3)
    descripcion = models.TextField(blank=True)

    def __str__(self):
        return f"{self.recinto.nombre} — {self.nombre}"

    class Meta:
        ordering = ['nivel']
        verbose_name = "Planta"


class Stand(models.Model):
    ZONA_CHOICES = [
        ('gimnasio', 'Gimnasio UTEQ'),
        ('auditorio', 'Auditorio principal'),
        ('pasillo_a', 'Pasillo Edificio A'),
        ('pasillo_b', 'Pasillo Edificio B'),
        ('exterior', 'Explanada / Exterior'),
        ('otro', 'Otro / Sala alterna'),
    ]

    planta = models.ForeignKey(
        Planta, on_delete=models.CASCADE,
        related_name='stands', null=True, blank=True
    )
    numero = models.CharField(max_length=20)
    zona = models.CharField(max_length=100, blank=True)
    pos_fila = models.PositiveIntegerField(default=0)
    pos_col = models.PositiveIntegerField(default=0)
    capacidad_proyectos = models.PositiveIntegerField(default=1)
    descripcion = models.TextField(blank=True)
    esta_activo = models.BooleanField(default=True)

    def __str__(self):
        return f"Stand {self.numero}"

    def get_zona_display(self):
        return dict(self.ZONA_CHOICES).get(self.zona, self.zona or "General")

    @property
    def asignacion(self):
        return self.asignacionstand_set.filter(activa=True).first()


class AsignacionStand(models.Model):
    stand = models.ForeignKey(
        Stand, 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='asignacionstand_set', 
        related_query_name='asignacion',
        verbose_name="Stand / Mesa física",
        limit_choices_to={'esta_activo': True}
    )
    proyecto = models.ForeignKey(
        'usuarios.Proyecto', 
        on_delete=models.CASCADE, 
        related_name='asignaciones_stands', 
        related_query_name='asignacionstand',
        verbose_name="Proyecto asignado"
    )
    fecha_asignacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de asignación")
    comentarios = models.TextField(blank=True, verbose_name="Comentarios de asignación")
    cambio_solicitado = models.BooleanField(default=False, verbose_name="Cambio solicitado por alumno")
    motivo_cambio = models.TextField(blank=True, verbose_name="Motivo de solicitud de cambio")
    cambio_autorizado = models.BooleanField(null=True, blank=True, verbose_name="Cambio autorizado por admin")
    motivo_rechazo = models.TextField(blank=True, verbose_name="Motivo de rechazo de cambio")
    activa = models.BooleanField(default=True, verbose_name="Asignación activa")

    class Meta:
        verbose_name = "Asignación de Stand"
        verbose_name_plural = "Asignaciones de Stands"
        ordering = ['-fecha_asignacion']

    def __str__(self):
        return f"Stand {self.stand.numero if self.stand else 'N/A'} -> {self.proyecto.titulo}"

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