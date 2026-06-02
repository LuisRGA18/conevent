from django import forms
from .models import Proyecto
from .models import Usuario
import re

class ProyectoForm(forms.ModelForm):
    class Meta:
        model = Proyecto
        fields = ['titulo', 'descripcion', 'integrantes']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control bg-dark text-white border-secondary', 'placeholder': 'Ej. Sistema de Control de Eventos'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control bg-dark text-white border-secondary', 'rows': 4, 'placeholder': 'Describe brevemente de qué trata tu proyecto...'}),
            'integrantes': forms.Textarea(attrs={'class': 'form-control bg-dark text-white border-secondary', 'rows': 2, 'placeholder': 'Juan Pérez, María López, Luis Ángel...'}),
        }

class RegistroForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=150, 
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control bg-dark text-white border-secondary', 'placeholder': 'Ej. Luis Ángel'}),
        label="Nombre(s)"
    )
    last_name = forms.CharField(
        max_length=150, 
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control bg-dark text-white border-secondary', 'placeholder': 'Ej. Pérez Gómez'}),
        label="Apellido(s)"
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control bg-dark text-white border-secondary', 'placeholder': 'Mínimo 8 caracteres, 1 mayúscula y 1 número'}),
        label="Contraseña"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control bg-dark text-white border-secondary', 'placeholder': 'Repite tu contraseña'}),
        label="Confirmar Contraseña"
    )

    class Meta:
        model = Usuario
        fields = ['email', 'rol']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control bg-dark text-white border-secondary', 'placeholder': 'tu_correo@uteq.edu.mx'}),
            'rol': forms.Select(attrs={'class': 'form-select bg-dark text-white border-secondary'}),
        }

    # FILTRO DE CORREO INSTITUCIONAL @uteq.edu.mx
    def clean_email(self):
        email = self.cleaned_data.get('email').lower() # Lo pasamos a minúsculas por seguridad
        
        if not email.endswith('@uteq.edu.mx'):
            raise forms.ValidationError("Acceso denegado. Solo se permiten correos institucionales de la UTEQ (@uteq.edu.mx).")
            
        # Validar si el correo ya está registrado en la base de datos
        if Usuario.objects.filter(email=email).exists():
            raise forms.ValidationError("Este correo institucional ya se encuentra registrado.")
            
        return email

    # POLÍTICAS DE SEGURIDAD EN LA CONTRASEÑA
    def clean_password(self):
        password = self.cleaned_data.get('password')
        
        if len(password) < 8:
            raise forms.ValidationError("La contraseña debe tener un mínimo de 8 caracteres.")
        if not re.search(r'[A-Z]', password):
            raise forms.ValidationError("La contraseña debe contener al menos una letra mayúscula.")
        if not re.search(r'[0-9]', password):
            raise forms.ValidationError("La contraseña debe contener al menos un número.")
            
        return password

    # COINCIDENCIA DE CONTRASEÑAS
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            raise forms.ValidationError("Las contraseñas no coinciden.")
            
        return cleaned_data