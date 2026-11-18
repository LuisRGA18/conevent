from django import forms
from django.forms import inlineformset_factory, BaseInlineFormSet
from decimal import Decimal
from .models import Proyecto, Usuario, Integrante, Evaluacion, CriterioEvaluacion, Evento
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
    comentarios = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': TEXTAREA_CLASS,
            'rows': 4,
            'placeholder': 'Observaciones o retroalimentación sobre el proyecto (opcional)...'
        }),
        label='Comentarios generales / observaciones (opcional)'
    )

    class Meta:
        model = Evaluacion
        fields = ['comentarios']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'comentarios' in self.fields:
            self.fields['comentarios'].required = False
            self.fields['comentarios_evaluador'] = self.fields['comentarios']


class CriterioEvaluacionForm(forms.ModelForm):
    """Formulario para editar o agregar un criterio de evaluación individual."""
    nombre = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': INPUT_CLASS,
            'placeholder': 'Ej. Presentación y Exposición'
        }),
        label='Nombre del Criterio'
    )
    descripcion = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': INPUT_CLASS,
            'placeholder': 'Descripción o rúbrica de desempeño (opcional)'
        }),
        label='Descripción / Rúbrica'
    )
    peso = forms.DecimalField(
        max_digits=4,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': INPUT_CLASS + ' criterio-peso-input',
            'step': '0.01',
            'min': '0.01',
            'max': '100',
            'placeholder': '0.25 (o 25%)'
        }),
        label='Ponderación'
    )
    activo = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Activo'
    )

    class Meta:
        model = CriterioEvaluacion
        fields = ['nombre', 'descripcion', 'peso', 'activo']

    def clean_peso(self):
        peso = self.cleaned_data.get('peso')
        if peso is not None:
            # Si el usuario ingresó un valor en porcentaje > 1 (ej. 25 en vez de 0.25)
            if peso > 1:
                peso = round(Decimal(str(peso)) / Decimal('100'), 2)
            if peso <= 0 or peso > 1:
                raise forms.ValidationError("La ponderación debe ser entre 0.01 (1%) y 1.00 (100%).")
        return peso


class BaseCriterioFormSet(BaseInlineFormSet):
    """FormSet para validar la cantidad máxima de 10 criterios."""
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        total_validos = 0
        criterios_activos = 0
        total_peso = Decimal('0')

        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data.get('DELETE'):
                continue
            total_validos += 1
            if form.cleaned_data.get('activo', True):
                criterios_activos += 1
                total_peso += form.cleaned_data.get('peso') or Decimal('0')

        if total_validos > 10:
            raise forms.ValidationError("No es posible configurar más de 10 criterios de evaluación por evento.")
        if total_validos == 0:
            raise forms.ValidationError("Debe existir al menos un criterio de evaluación para el evento.")


class AsignacionEvaluadorForm(forms.ModelForm):
    """Formulario para que el ADMIN asigne evaluador a un proyecto."""
    class Meta:
        model = Proyecto
        fields = ['evaluadores']
        widgets = {
            'evaluadores': forms.SelectMultiple(attrs={'class': SELECT_CLASS}),
        }
        labels = {
            'evaluadores': 'Evaluadores Asignados',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo mostrar usuarios con rol EVALUADOR
        self.fields['evaluadores'].queryset = Usuario.objects.filter(rol='EVALUADOR')


class RegistroForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': INPUT_CLASS,
            'placeholder': 'Ej. Juan'
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