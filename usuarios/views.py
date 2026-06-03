from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
import unicodedata

from .forms import (
    ProyectoForm, RegistroForm,
    IntegranteFormSet, EvaluacionForm, AsignacionEvaluadorForm
)
from .models import Proyecto, Usuario, Integrante


# ──────────────────────────────────────────────────────────────
# AUTENTICACIÓN
# ──────────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == 'POST':
        usuario = request.POST.get('username')
        clave = request.POST.get('password')
        user = authenticate(request, username=usuario, password=clave)

        if user is not None:
            if user.is_active:
                login(request, user)
                messages.success(request, f"¡Bienvenido de nuevo, {user.first_name or user.username}!")
                return redirect('index')
            else:
                messages.error(request, "Esta cuenta se encuentra desactivada.")
        else:
            messages.error(request, "Usuario o contraseña incorrectos.")

    return render(request, 'usuarios/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


def limpiar_texto(texto):
    texto_limpio = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('utf-8')
    return texto_limpio.lower().strip()


def registro_view(request):
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            nombres = form.cleaned_data['first_name']
            apellidos = form.cleaned_data['last_name']
            primer_nombre = limpiar_texto(nombres.split()[0])
            primer_apellido = limpiar_texto(apellidos.split()[0])
            username_propuesto = f"{primer_nombre}.{primer_apellido}"

            contador = 1
            username_final = username_propuesto
            while Usuario.objects.filter(username=username_final).exists():
                username_final = f"{username_propuesto}{contador}"
                contador += 1

            user.username = username_final
            user.first_name = nombres
            user.last_name = apellidos
            user.email = form.cleaned_data['email']
            user.set_password(form.cleaned_data['password'])
            user.save()

            messages.success(request, f"¡Cuenta creada! Tu usuario es: {username_final}")
            return redirect('login')
    else:
        form = RegistroForm()

    return render(request, 'usuarios/registro.html', {'form': form})


# ──────────────────────────────────────────────────────────────
# DASHBOARD / INDEX (redirige según rol)
# ──────────────────────────────────────────────────────────────

@login_required(login_url='login')
def index_view(request):
    return render(request, 'seguridad/index.html')


# ──────────────────────────────────────────────────────────────
# VISTAS ALUMNO
# ──────────────────────────────────────────────────────────────

@login_required(login_url='login')
def mi_proyecto_view(request):
    """El alumno registra su proyecto e integrantes."""
    mis_proyectos = Proyecto.objects.filter(alumno_creador=request.user).prefetch_related('miembros')

    if request.method == 'POST':
        form = ProyectoForm(request.POST)
        formset = IntegranteFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            # Validar exactamente un líder
            lideres = sum(
                1 for f in formset
                if f.cleaned_data.get('es_lider') and not f.cleaned_data.get('DELETE')
            )
            if lideres != 1:
                messages.error(request, "Debe haber exactamente un integrante marcado como líder.")
            else:
                proyecto = form.save(commit=False)
                proyecto.alumno_creador = request.user
                proyecto.save()
                formset.instance = proyecto
                formset.save()
                messages.success(request, "¡Proyecto registrado con éxito!")
                return redirect('mi_proyecto')
    else:
        form = ProyectoForm()
        formset = IntegranteFormSet()

    return render(request, 'usuarios/mi_proyecto.html', {
        'form': form,
        'formset': formset,
        'mis_proyectos': mis_proyectos,
    })


@login_required(login_url='login')
def editar_proyecto_view(request, pk):
    """El alumno edita su propio proyecto (solo si está en revisión)."""
    proyecto = get_object_or_404(Proyecto, pk=pk, alumno_creador=request.user)

    if proyecto.estatus != 'revision':
        messages.warning(request, "No puedes editar un proyecto que ya fue evaluado.")
        return redirect('mi_proyecto')

    if request.method == 'POST':
        form = ProyectoForm(request.POST, instance=proyecto)
        formset = IntegranteFormSet(request.POST, instance=proyecto)

        if form.is_valid() and formset.is_valid():
            lideres = sum(
                1 for f in formset
                if f.cleaned_data.get('es_lider') and not f.cleaned_data.get('DELETE')
            )
            if lideres != 1:
                messages.error(request, "Debe haber exactamente un integrante marcado como líder.")
            else:
                form.save()
                formset.save()
                messages.success(request, "Proyecto actualizado correctamente.")
                return redirect('mi_proyecto')
    else:
        form = ProyectoForm(instance=proyecto)
        formset = IntegranteFormSet(instance=proyecto)

    return render(request, 'usuarios/editar_proyecto.html', {
        'form': form,
        'formset': formset,
        'proyecto': proyecto,
    })


# ──────────────────────────────────────────────────────────────
# VISTAS EVALUADOR
# ──────────────────────────────────────────────────────────────

@login_required(login_url='login')
def proyectos_asignados_view(request):
    """El evaluador ve los proyectos que le fueron asignados."""
    if not request.user.es_evaluador:
        messages.error(request, "No tienes permiso para acceder a esta sección.")
        return redirect('index')

    proyectos = Proyecto.objects.filter(
        evaluador_asignado=request.user
    ).prefetch_related('miembros').select_related('carrera')

    return render(request, 'usuarios/proyectos_asignados.html', {
        'proyectos': proyectos
    })


@login_required(login_url='login')
def evaluar_proyecto_view(request, pk):
    """El evaluador califica y comenta un proyecto."""
    if not request.user.es_evaluador:
        messages.error(request, "No tienes permiso para acceder a esta sección.")
        return redirect('index')

    proyecto = get_object_or_404(Proyecto, pk=pk, evaluador_asignado=request.user)

    if request.method == 'POST':
        form = EvaluacionForm(request.POST, instance=proyecto)
        if form.is_valid():
            form.save()
            messages.success(request, f'Evaluación guardada para "{proyecto.titulo}".')
            return redirect('proyectos_asignados')
    else:
        form = EvaluacionForm(instance=proyecto)

    integrantes = proyecto.miembros.all()
    return render(request, 'usuarios/evaluar_proyecto.html', {
        'form': form,
        'proyecto': proyecto,
        'integrantes': integrantes,
    })


# ──────────────────────────────────────────────────────────────
# VISTAS ADMINISTRADOR
# ──────────────────────────────────────────────────────────────

@login_required(login_url='login')
def panel_admin_view(request):
    """Panel del administrador: lista todos los proyectos con filtros."""
    if not request.user.es_admin:
        messages.error(request, "No tienes permiso para acceder a esta sección.")
        return redirect('index')

    qs = Proyecto.objects.select_related(
        'alumno_creador', 'evaluador_asignado', 'carrera'
    ).prefetch_related('miembros')

    # Filtros
    q = request.GET.get('q', '').strip()
    estatus = request.GET.get('estatus', '')

    if q:
        qs = qs.filter(Q(titulo__icontains=q) | Q(alumno_creador__username__icontains=q))
    if estatus:
        qs = qs.filter(estatus=estatus)

    evaluadores = Usuario.objects.filter(rol='EVALUADOR')

    return render(request, 'usuarios/panel_admin.html', {
        'proyectos': qs,
        'evaluadores': evaluadores,
        'q': q,
        'estatus_filtro': estatus,
        'estatus_choices': Proyecto.ESTATUS_CHOICES,
    })


@login_required(login_url='login')
def asignar_evaluador_view(request, pk):
    """El admin asigna un evaluador a un proyecto específico."""
    if not request.user.es_admin:
        messages.error(request, "No tienes permiso.")
        return redirect('index')

    proyecto = get_object_or_404(Proyecto, pk=pk)

    if request.method == 'POST':
        form = AsignacionEvaluadorForm(request.POST, instance=proyecto)
        if form.is_valid():
            form.save()
            messages.success(request, f'Evaluador asignado a "{proyecto.titulo}".')
            return redirect('panel_admin')
    else:
        form = AsignacionEvaluadorForm(instance=proyecto)

    return render(request, 'usuarios/asignar_evaluador.html', {
        'form': form,
        'proyecto': proyecto,
    })