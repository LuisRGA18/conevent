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

    # Dashboard
    path('', usuarios_views.index_view, name='index'),

]