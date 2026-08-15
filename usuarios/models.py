from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings


# ──────────────────────────────────────────────────────────────
# USUARIO
# ──────────────────────────────────────────────────────────────

class Usuario(AbstractUser):
    ROLE_CHOICES = (
        ('ADMIN',      'Administrador de Evento'),
        ('EVALUADOR',  'Docente Evaluador'),
        ('ALUMNO',     'Alumno Participante'),
    )
    rol = models.CharField(max_length=15, choices=ROLE_CHOICES, default='ALUMNO')
    matricula_empleado = models.CharField(
        max_length=20, blank=True, null=True, unique=True,
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


# ──────────────────────────────────────────────────────────────
# CARRERA
# ──────────────────────────────────────────────────────────────

class Carrera(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    clave  = models.CharField(max_length=20,  unique=True)

    class Meta:
        verbose_name        = "Carrera"
        verbose_name_plural = "Carreras"
        ordering            = ['nombre']

    def __str__(self):
        return self.nombre


# ──────────────────────────────────────────────────────────────
# PROYECTO
# ──────────────────────────────────────────────────────────────

class Proyecto(models.Model):
    ESTATUS_CHOICES = [
        ('revision',  'En Revisión'),
        ('aprobado',  'Aprobado'),
        ('rechazado', 'Rechazado'),
    ]
    CATEGORIA_CHOICES = [
        ('software',  'Desarrollo de Software'),
        ('hardware',  'Hardware / Electrónica'),
        ('redes',     'Redes y Telecomunicaciones'),
        ('ia',        'Inteligencia Artificial'),
        ('otro',      'Otro'),
    ]

    titulo      = models.CharField(max_length=200, verbose_name="Título del Proyecto")
    descripcion = models.TextField(verbose_name="Descripción o Resumen")
    carrera     = models.ForeignKey(
        Carrera, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='proyectos', verbose_name="Carrera"
    )
    grupo    = models.CharField(max_length=10, blank=True, verbose_name="Grupo / Paralelo")
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default='software')
    logo     = models.ImageField(upload_to='logos_proyectos/', null=True, blank=True)

    # Quién registró el proyecto
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='proyectos', verbose_name="Alumno / Creador"
    )
    # Quién lo evaluará
    evaluadores = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='proyectos_asignados',
        limit_choices_to={'rol': 'EVALUADOR'},
        verbose_name='Evaluadores asignados'
    )

    estatus     = models.CharField(max_length=20, choices=ESTATUS_CHOICES, default='revision')
    # Calificación final (resumen rápido; el detalle está en Evaluacion)
    calificacion = models.DecimalField(
        max_digits=4, decimal_places=2, null=True, blank=True,
        verbose_name="Calificación Final"
    )
    comentarios_evaluador = models.TextField(blank=True, default='')
    qr_evaluacion_externa = models.ImageField(
        upload_to='qr_proyectos/',
        null=True, blank=True,
        verbose_name="QR de evaluación externa"
    )

    MESAS_CHOICES = [
        (1, '1 mesa (estándar)'),
        (2, '2 mesas (proyecto con equipo grande o prototipo físico)'),
        (3, '3 mesas (instalación especial — requiere autorización del admin)'),
    ]
    mesas_requeridas = models.PositiveIntegerField(
        choices=MESAS_CHOICES,
        default=1,
        verbose_name="Mesas requeridas para exhibición"
    )
    mesas_autorizadas = models.BooleanField(
        default=False,
        verbose_name="Mesas extra autorizadas por admin"
    )

    fecha_registro      = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "Proyecto"
        verbose_name_plural = "Proyectos"
        ordering            = ['-fecha_registro']

    def __str__(self):
        return self.titulo

    @property
    def codigo(self):
        return f"EQU-{self.pk:03d}"

    @property
    def num_integrantes(self):
        return self.miembros.count()


# ──────────────────────────────────────────────────────────────
# INTEGRANTE
# ──────────────────────────────────────────────────────────────

class Integrante(models.Model):
    proyecto       = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name='miembros')
    nombre_completo = models.CharField(max_length=150, verbose_name="Nombre Completo")
    matricula      = models.CharField(max_length=20,  verbose_name="Matrícula")
    correo         = models.EmailField(verbose_name="Correo Institucional")
    es_lider       = models.BooleanField(default=False, verbose_name="¿Es líder?")

    class Meta:
        verbose_name        = "Integrante"
        verbose_name_plural = "Integrantes"
        ordering            = ['-es_lider', 'nombre_completo']
        constraints = [
            models.UniqueConstraint(
                fields=['proyecto', 'matricula'],
                name='unique_matricula_por_proyecto'
            )
        ]

    def __str__(self):
        return f"{self.nombre_completo} ({'Líder' if self.es_lider else 'Integrante'})"


# ──────────────────────────────────────────────────────────────
# EVALUACION  (modelo separado — una por proyecto por evaluador)
# ──────────────────────────────────────────────────────────────
# CRITERIO DE EVALUACIÓN
# ──────────────────────────────────────────────────────────────

class CriterioEvaluacion(models.Model):
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre del criterio")
    descripcion = models.TextField(blank=True, verbose_name="Descripción o rúbrica de desempeño")
    peso = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        help_text="Peso en decimal (ej. 0.35 para 35%). La suma de los criterios activos debe ser 1.00",
        verbose_name="Peso del criterio"
    )
    activo = models.BooleanField(default=True, verbose_name="Criterio activo")

    class Meta:
        verbose_name = "Criterio de Evaluación"
        verbose_name_plural = "Criterios de Evaluación"
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({int(self.peso * 100)}%)"


# ──────────────────────────────────────────────────────────────
# EVALUACION  (modelo separado — una por proyecto por evaluador)
# ──────────────────────────────────────────────────────────────

class Evaluacion(models.Model):
    proyecto     = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name='evaluaciones')
    evaluador    = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='evaluaciones_realizadas'
    )
    calificacion          = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    comentarios_evaluador = models.TextField(blank=True, null=True)
    estatus_sugerido      = models.CharField(
        max_length=20, choices=Proyecto.ESTATUS_CHOICES, default='aprobado',
        verbose_name="Resultado sugerido"
    )
    fecha_evaluacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = "Evaluación"
        verbose_name_plural = "Evaluaciones"
        # Un evaluador solo puede evaluar el mismo proyecto una vez
        constraints = [
            models.UniqueConstraint(
                fields=['proyecto', 'evaluador'],
                name='unique_evaluacion_por_evaluador'
            )
        ]

    def __str__(self):
        return f"Evaluación {self.proyecto.codigo} — {self.calificacion}"

    def recalcular_calificacion(self):
        """
        Recalcula la calificación final a partir de los detalles cargados de la rúbrica.
        """
        detalles = self.detalles.all()
        if detalles.exists():
            calif_final = 0
            for det in detalles:
                calif_final += float(det.calificacion_numerica) * float(det.criterio.peso)
            self.calificacion = calif_final
            
            # Guardamos únicamente la calificación para evitar ciclos infinitos de save()
            Evaluacion.objects.filter(pk=self.pk).update(calificacion=self.calificacion)
            
            # También actualizamos la calificación final del proyecto
            self.proyecto.calificacion = self.calificacion
            self.proyecto.save(update_fields=['calificacion'])


# ──────────────────────────────────────────────────────────────
# DETALLE DE EVALUACIÓN
# ──────────────────────────────────────────────────────────────

class DetalleEvaluacion(models.Model):
    CUALITATIVA_CHOICES = [
        ('AU', 'Autónomo (10)'),
        ('DE', 'Destacado (9)'),
        ('SA', 'Satisfactorio (8)'),
        ('NA', 'No Aprobatorio (0)'),
    ]

    VALORES_NUMERICOS = {
        'AU': 10.0,
        'DE': 9.0,
        'SA': 8.0,
        'NA': 0.0,
    }

    evaluacion = models.ForeignKey(Evaluacion, on_delete=models.CASCADE, related_name='detalles')
    criterio = models.ForeignKey(CriterioEvaluacion, on_delete=models.CASCADE, related_name='detalles_evaluacion')
    calificacion_cualitativa = models.CharField(max_length=2, choices=CUALITATIVA_CHOICES, verbose_name="Evaluación cualitativa")
    calificacion_numerica = models.DecimalField(max_digits=4, decimal_places=2, editable=False, verbose_name="Calificación numérica")

    class Meta:
        verbose_name = "Detalle de Evaluación"
        verbose_name_plural = "Detalles de Evaluación"
        constraints = [
            models.UniqueConstraint(
                fields=['evaluacion', 'criterio'],
                name='unique_criterio_por_evaluacion'
            )
        ]

    def __str__(self):
        return f"{self.criterio.nombre}: {self.get_calificacion_cualitativa_display()}"

    def save(self, *args, **kwargs):
        # Auto-calcular el valor numérico basado en el valor cualitativo antes de guardar
        self.calificacion_numerica = self.VALORES_NUMERICOS.get(self.calificacion_cualitativa, 0.0)
        super().save(*args, **kwargs)
        
        # Recalcular la nota general de la evaluación principal
        self.evaluacion.recalcular_calificacion()


# ──────────────────────────────────────────────────────────────
# EVALUACION EXTERNA (Visitantes externos por QR)
# ──────────────────────────────────────────────────────────────

class EvaluacionExterna(models.Model):
    ESCALA_CHOICES = [
        ('AU', 'AU - Autónomo (10)'),
        ('DE', 'DE - Destacado (9)'),
        ('SA', 'SA - Satisfactorio (8)'),
        ('NA', 'NA - No Acreditado'),
    ]

    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name='evaluaciones_externas')
    nombre_visitante = models.CharField(max_length=150)
    empresa_procedencia = models.CharField(max_length=150)
    correo_contacto = models.EmailField()
    telefono_contacto = models.CharField(max_length=20, blank=True)
    calificacion = models.CharField(max_length=2, choices=ESCALA_CHOICES)
    comentario = models.TextField(blank=True)
    codigo_acceso_usado = models.CharField(max_length=20)  # para auditoría
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']

    def get_valor_numerico(self):
        return {'AU': 10, 'DE': 9, 'SA': 8, 'NA': 6}.get(self.calificacion, 0)


class LogActividad(models.Model):
    TIPO_CHOICES = [
        ('login', 'Inicio de sesión'),
        ('logout', 'Cierre de sesión'),
        ('login_fallido', 'Intento fallido de login'),
        ('2fa_exitoso', 'Verificación 2FA exitosa'),
        ('2fa_fallido', 'Verificación 2FA fallida'),
        ('registro', 'Registro de usuario'),
        ('cambio_estatus', 'Cambio de estatus de proyecto'),
        ('evaluacion', 'Evaluación registrada'),
        ('evaluacion_externa', 'Evaluación externa registrada'),
        ('resolucion_incidencia', 'Incidencia resuelta'),
    ]
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='logs')
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES)
    descripcion = models.TextField(blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']
        verbose_name = "Log de actividad"
        verbose_name_plural = "Logs de actividad"

    def __str__(self):
        user_str = self.usuario.username if self.usuario else "Anónimo/Visitante"
        return f"{self.fecha.strftime('%Y-%m-%d %H:%M')} | {self.get_tipo_display()} | {user_str}"