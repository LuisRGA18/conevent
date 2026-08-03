from django import forms
from django.forms import inlineformset_factory
from .models import Proyecto, Usuario, Integrante, Evaluacion
import re
from decouple import config

# ─── Estilos reutilizables (dark theme que ya usan) ───────────────────────────
INPUT_CLASS = 'form-control bg-dark text-white border-secondary'
SELECT_CLASS = 'form-select bg-dark text-white border-secondary'
TEXTAREA_CLASS = 'form-control bg-dark text-white border-secondary'


class ProyectoForm(forms.ModelForm):
    class Meta:
        model = Proyecto
        fields = ['titulo', 'descripcion', 'carrera', 'grupo', 'categoria', 'logo', 'mesas_requeridas']
        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'Ej. Sistema de Control de Eventos'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': TEXTAREA_CLASS,
                'rows': 4,
                'placeholder': 'Describe brevemente de qué trata tu proyecto...'
            }),
            'carrera': forms.Select(attrs={'class': SELECT_CLASS}),
            'grupo': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'Ej. A, 4B'
            }),
            'categoria': forms.Select(attrs={'class': SELECT_CLASS}),
            'logo': forms.ClearableFileInput(attrs={'class': INPUT_CLASS}),
            'mesas_requeridas': forms.RadioSelect(attrs={'class': 'mesas-radio-input form-check-input'}),
        }
        labels = {
            'titulo': 'Título del Proyecto',
            'descripcion': 'Descripción / Resumen',
            'carrera': 'Carrera',
            'grupo': 'Grupo / Paralelo',
            'categoria': 'Categoría',
            'logo': 'Logotipo del Proyecto',
            'mesas_requeridas': 'Mesas requeridas para exhibición',
        }


class IntegranteForm(forms.ModelForm):
    class Meta:
        model = Integrante
        fields = ['nombre_completo', 'matricula', 'correo', 'es_lider']
        widgets = {
            'nombre_completo': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'Nombre completo'
            }),
            'matricula': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'Matrícula'
            }),
            'correo': forms.EmailInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'correo@uteq.edu.mx'
            }),
            'es_lider': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


# FormSet: permite agregar varios integrantes en el mismo formulario del proyecto
IntegranteFormSet = inlineformset_factory(
    Proyecto,
    Integrante,
    form=IntegranteForm,
    extra=1,
    min_num=1,
    max_num=6,
    validate_min=True,
    can_delete=True,
)


class EvaluacionForm(forms.ModelForm):
    """Formulario para que el evaluador califique y comente un proyecto."""
    class Meta:
        model = Evaluacion
        fields = ['comentarios_evaluador']
        widgets = {
            'comentarios_evaluador': forms.Textarea(attrs={
                'class': TEXTAREA_CLASS,
                'rows': 4,
                'placeholder': 'Observaciones sobre el proyecto...'
            }),
        }
        labels = {
            'comentarios_evaluador': 'Comentarios generales / observaciones',
        }


class AsignacionEvaluadorForm(forms.ModelForm):
    """Formulario para que el ADMIN asigne evaluador a un proyecto."""
    class Meta:
        model = Proyecto
        fields = ['evaluador_asignado']
        widgets = {
            'evaluador_asignado': forms.Select(attrs={'class': SELECT_CLASS}),
        }
        labels = {
            'evaluador_asignado': 'Evaluador Asignado',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo mostrar usuarios con rol EVALUADOR
        self.fields['evaluador_asignado'].queryset = Usuario.objects.filter(rol='EVALUADOR')


class RegistroForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': INPUT_CLASS,
            'placeholder': 'Ej. Luis Ángel'
        }),
        label="Nombre(s)"
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': INPUT_CLASS,
            'placeholder': 'Ej. Pérez Gómez'
        }),
        label="Apellido(s)"
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': INPUT_CLASS,
            'placeholder': 'Mínimo 8 caracteres, 1 mayúscula y 1 número'
        }),
        label="Contraseña"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': INPUT_CLASS,
            'placeholder': 'Repite tu contraseña'
        }),
        label="Confirmar Contraseña"
    )
    codigo_acceso_docente = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': INPUT_CLASS,
            'placeholder': 'Código de acceso docente'
        }),
        label="Código de acceso docente"
    )

    class Meta:
        model = Usuario
        fields = ['email', 'rol']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'tu_correo@uteq.edu.mx'
            }),
            'rol': forms.Select(attrs={'class': SELECT_CLASS}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email').lower()
        if not email.endswith('@uteq.edu.mx'):
            raise forms.ValidationError(
                "Acceso denegado. Solo se permiten correos institucionales de la UTEQ (@uteq.edu.mx)."
            )
        if Usuario.objects.filter(email=email).exists():
            raise forms.ValidationError("Este correo institucional ya se encuentra registrado.")
        return email

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if len(password) < 8:
            raise forms.ValidationError("La contraseña debe tener un mínimo de 8 caracteres.")
        if not re.search(r'[A-Z]', password):
            raise forms.ValidationError("La contraseña debe contener al menos una letra mayúscula.")
        if not re.search(r'[0-9]', password):
            raise forms.ValidationError("La contraseña debe contener al menos un número.")
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password != confirm_password:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        
        rol = cleaned_data.get("rol")
        if rol == 'EVALUADOR':
            codigo = cleaned_data.get("codigo_acceso_docente")
            if codigo != config('CODIGO_REGISTRO_EVALUADOR', default='2011'):
                self.add_error('codigo_acceso_docente', "Código de acceso docente incorrecto. Contacta al coordinador del evento.")
        return cleaned_data
    

class ProyectoForm(forms.ModelForm):
    class Meta:
        model = Proyecto
        fields = ['titulo', 'descripcion', 'carrera', 'grupo', 'categoria', 'logo']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control bg-dark text-white border-secondary', 'placeholder': 'Ej. Sistema de Control ConEvent'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control bg-dark text-white border-secondary', 'rows': 4, 'placeholder': 'Resume de qué trata tu proyecto...'}),
            'carrera': forms.Select(attrs={'class': 'form-select bg-dark text-white border-secondary'}),
            'grupo': forms.TextInput(attrs={'class': 'form-control bg-dark text-white border-secondary', 'placeholder': 'Ej. 8° A'}),
            'categoria': forms.Select(attrs={'class': 'form-select bg-dark text-white border-secondary'}),
            'logo': forms.FileInput(attrs={'class': 'form-control bg-dark text-white border-secondary'}),
        }