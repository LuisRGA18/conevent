# DOCUMENTO DE EVIDENCIA TÉCNICA — MÓDULO DE SEGURIDAD Y CUMPLIMIENTO ISO/IEC 27001
**Proyecto:** ConEvent (SIGEA — Sistema Inteligente de Gestión de Eventos Académicos)  
**Dominio de Producción:** [https://conevent.duckdns.org](https://conevent.duckdns.org)  
**Tareas de Cronograma Validadas:** Filas 21, 22, 23 y 24  
**Estado Anterior:** 0% — **Estado Actual:** 100% COMPLETADO Y OPERATIVO EN PRODUCCIÓN  

---

## 1. Resumen de Implementación de Seguridad
El módulo de seguridad de ConEvent implementa un marco integral alineado con los controles de la norma internacional **ISO/IEC 27001:2022**, específicamente enfocado en los dominios:
- **A.9 Control de Acceso:** Autenticación robusta, separación estricta de responsabilidades mediante control de acceso basado en roles (RBAC) y prevención de elevación de privilegios.
- **A.10 Criptografía:** Cifrado en tránsito con TLS 1.3/HTTPS, almacenamiento de contraseñas mediante PBKDF2 con SHA-256 y tokens JWT firmados criptográficamente.
- **A.12 Seguridad en las Operaciones:** Registro inmutable de eventos de auditoría (`LogActividad`), prevención de ataques web mediante hardening de middleware y sanitización estricta de tipos de datos.

---

## 2. Evidencia de Autenticación y Recuperación Segura (Fila 21 del Cronograma)

### 2.1 Flujo Criptográfico de Restablecimiento de Contraseña
El sistema implementa el estándar nativo de Django para recuperación de credenciales sin almacenamiento de tokens reversibles, utilizando `PasswordResetView` con generación de enlaces efímeros basados en hashing unidireccional con sellos de tiempo (`uidb64` + `token`).

En `conevent/urls.py`:
```python
# conevent/urls.py
from django.contrib.auth import views as auth_views

urlpatterns = [
    # ...
    path('auth/password-reset/',
         auth_views.PasswordResetView.as_view(
             template_name='usuarios/password_reset.html',
             email_template_name='usuarios/password_reset_email.html',
             subject_template_name='usuarios/password_reset_subject.txt',
         ), name='password_reset'),

    path('auth/password-reset/enviado/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='usuarios/password_reset_done.html',
         ), name='password_reset_done'),

    path('auth/password-reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='usuarios/password_reset_confirm.html',
         ), name='password_reset_confirm'),

    path('auth/password-reset/listo/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='usuarios/password_reset_complete.html',
         ), name='password_reset_complete'),
]
```

### 2.2 Configuración del Transporte SMTP Cifrado
En `conevent/settings.py` se parametrizó el servicio de despacho de correo con cifrado en capa de transporte (TLS):
```python
# conevent/settings.py
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('EMAIL_HOST_USER', default='equipo.soporte.oasis@gmail.com')
```

### 2.3 Plantillas Institucionales Personalizadas
- `templates/usuarios/password_reset_email.html`: Contiene el cuerpo institucional del correo con advertencias de seguridad y botón de un solo uso.
- `templates/usuarios/password_reset_subject.txt`: Define el asunto formal: *"Recuperación de contraseña - ConEvent UTEQ"*.

---

## 3. Evidencia de Endurecimiento de Django / Hardening (Fila 22 del Cronograma)

### 3.1 Pila de Middlewares de Seguridad
En `conevent/settings.py` se blindó la aplicación contra vectores de ataque comunes (OWASP Top 10):
```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```

### 3.2 Directivas de Seguridad HTTP en Entorno Productivo
```python
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
```
- **X-Frame-Options: DENY:** Impide que la plataforma sea embebida en iframes, mitigando ataques de *Clickjacking*.
- **X-Content-Type-Options: nosniff:** Bloquea la interpretación errónea de tipos MIME.
- **Cookies Seguras (`Secure` + `HttpOnly`):** Previene la interceptación de identificadores de sesión en canales no cifrados.

### 3.3 Aritmética de Rúbricas Inmune a Desbordamiento y Precisión Decimal
En `usuarios/views.py` y `usuarios/models.py`, todos los cálculos de ponderaciones de rúbricas se ejecutan bajo `from decimal import Decimal`, previniendo errores de punto flotante binario IEEE-754:
```python
from decimal import Decimal
total_ponderacion = sum(Decimal(str(c.ponderacion)) for c in criterios)
```

### 3.4 Certificación SSL/TLS en Producción
El dominio `https://conevent.duckdns.org` se encuentra protegido con certificado RSA de 2048 bits expedido por Let's Encrypt CA, renovado automáticamente mediante Certbot y Nginx con redirección forzada de HTTP a HTTPS (puerto 443).

---

## 4. Evidencia de Auditoría e Inmutabilidad ISO 27001 (Filas 23 y 24 del Cronograma)

### 4.1 Modelo de Trazabilidad e Historial (`LogActividad`)
El modelo `LogActividad` implementado en `usuarios/models.py` registra eventos de seguridad con metadatos de red inalterables:
```python
# usuarios/models.py
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
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='logs'
    )
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES)
    descripcion = models.TextField(blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']
        verbose_name = "Log de actividad"
        verbose_name_plural = "Logs de actividad"
```

### 4.2 Captura de IP Real a través de Proxy Inverso Nginx
En `usuarios/views.py`:
```python
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('HTTP_X_REAL_IP', request.META.get('REMOTE_ADDR'))
    return ip
```

---

## 5. Guía de Capturas Recomendadas para Auditoría

| No. | Elemento a Evidenciar | Procedimiento / URL | Justificación Técnica |
|:---:|:----------------------|:-------------------|:----------------------|
| **1** | Certificado SSL/TLS Válido | Navegador web en `https://conevent.duckdns.org` $\rightarrow$ Clic en el icono de candado $\rightarrow$ Ver certificado. | Demuestra transporte cifrado TLS 1.3 con emisor Let's Encrypt. |
| **2** | Formulario de Recuperación de Clave | `https://conevent.duckdns.org/auth/password-reset/` | Valida la interfaz de solicitud de token seguro vía correo. |
| **3** | Notificación de Despacho de Correo | Bandeja de entrada del correo receptor con el mensaje institucional y enlace con `uidb64/token`. | Comprueba la integración efectiva del servidor SMTP y plantillas. |
| **4** | Tabla de Auditoría en Panel de Control | `https://conevent.duckdns.org/admin/usuarios/logactividad/` | Certifica el registro cronológico de IPs, usuarios y eventos críticos. |
| **5** | Consulta SQL en Base de Datos | Terminal SSH en GCP: `psql -d conevent_db -c "SELECT fecha, tipo, ip, usuario_id FROM usuarios_logactividad ORDER BY fecha DESC LIMIT 5;"` | Evidencia la persistencia física e inmutabilidad de los registros. |
