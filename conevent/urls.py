from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from usuarios import views as usuarios_views


urlpatterns = [
    path('admin/', admin.site.urls),

    # REST API
    path('api/', include('usuarios.api_urls')),

    # App usuarios
    path('auth/', include('usuarios.urls')),

    # Nuevas Apps (Fase 1)
    path('espacios/', include('espacios.urls')),
    path('inventario/', include('inventario.urls')),
    path('reportes/', include('reportes.urls')),

    # Reset de contraseña
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

    # Landing Page y Dashboard
    path('', usuarios_views.landing_home_view, name='landing'),
    path('como-funciona/', usuarios_views.landing_funciona_view, name='landing_funciona'),
    path('faq/', usuarios_views.landing_faq_view, name='landing_faq'),
    path('contacto/', usuarios_views.landing_contacto_view, name='landing_contacto'),
    path('dashboard/', usuarios_views.index_view, name='index'),
    path('contacto/enviar/', usuarios_views.contacto_view, name='contacto_enviar'),

    # Evaluación Externa y QRs por Proyecto
    path('proyectos/<int:proyecto_id>/evaluar-externo/', usuarios_views.evaluar_externo_view, name='evaluar_externo'),
    path('proyectos/<int:proyecto_id>/qr-externo/', usuarios_views.qr_externo_view, name='qr_externo'),
    path('proyectos/qr-externo/lote/', usuarios_views.qr_externo_lote_view, name='qr_externo_lote'),
]

from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)