from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Avg
from django.db import transaction
import unicodedata
import random
from .models import Proyecto, Usuario, Integrante, Evaluacion
from .forms import ProyectoForm
from django.db import transaction

from .forms import (
    ProyectoForm, RegistroForm,
    IntegranteFormSet, EvaluacionForm, AsignacionEvaluadorForm
)



# ──────────────────────────────────────────────────────────────
# AUTENTICACIÓN
# ──────────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == 'POST':
        usuario = request.POST.get('username')
        clave   = request.POST.get('password')
        user    = authenticate(request, username=usuario, password=clave)

        if user is not None:
            if user.is_active:
                # Dispositivo ya recordado → login directo
                if request.COOKIES.get(f'dispositivo_seguro_{user.id}') == 'true':
                    login(request, user)
                    request.session['mostrar_bienvenida'] = True
                    return redirect('index')

                # Dispositivo nuevo → generar código 2FA
                codigo_generado = str(random.randint(100000, 999999))
                request.session['pre_auth_user_id']    = user.id
                request.session['codigo_2fa_correcto'] = codigo_generado

                print("\n" + "="*50)
                print(f" CÓDIGO 2FA para {user.email}: {codigo_generado} ")
                print("="*50 + "\n")

                return redirect('verificar_2fa')
            else:
                messages.error(request, "Esta cuenta se encuentra desactivada.")
        else:
            messages.error(request, "Usuario o contraseña incorrectos.")

    return render(request, 'usuarios/login.html')


def verificar_2fa_view(request):
    user_id        = request.session.get('pre_auth_user_id')
    codigo_correcto = request.session.get('codigo_2fa_correcto')

    if not user_id or not codigo_correcto:
        return redirect('login')

    user = get_object_or_404(Usuario, id=user_id)

    if request.method == 'POST':
        codigo_ingresado = request.POST.get('codigo_2fa', '').strip()
        recordar         = request.POST.get('recordar_dispositivo')

        if codigo_ingresado == codigo_correcto:
            request.session.pop('pre_auth_user_id', None)
            request.session.pop('codigo_2fa_correcto', None)

            login(request, user, backend='usuarios.backends.EmailOrUsernameBackend')
            request.session['mostrar_bienvenida'] = True

            response = redirect('index')
            if recordar == 'si':
                response.set_cookie(
                    f'dispositivo_seguro_{user.id}', 'true',
                    max_age=30 * 24 * 60 * 60, httponly=True
                )
            return response
        else:
            messages.error(request, "Código de verificación incorrecto.")

    return render(request, 'usuarios/verificar_2fa.html')


def logout_view(request):
    logout(request)
    return redirect('login')


def limpiar_texto(texto):
    return unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('utf-8').lower().strip()


def registro_view(request):
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)

            nombres   = form.cleaned_data['first_name']
            apellidos = form.cleaned_data['last_name']
            primer_nombre   = limpiar_texto(nombres.split()[0])
            primer_apellido = limpiar_texto(apellidos.split()[0])
            username_base   = f"{primer_nombre}.{primer_apellido}"

            contador = 1
            username_final = username_base
            while Usuario.objects.filter(username=username_final).exists():
                username_final = f"{username_base}{contador}"
                contador += 1

            user.username   = username_final
            user.first_name = nombres
            user.last_name  = apellidos
            user.email      = form.cleaned_data['email']
            user.set_password(form.cleaned_data['password'])
            user.is_active  = False   # Cuenta desactivada hasta verificar correo
            user.save()

            codigo_activacion = str(random.randint(100000, 999999))
            request.session['id_usuario_pendiente']     = user.id
            request.session['codigo_activacion_correcto'] = codigo_activacion

            print("\n" + "═"*50)
            print(f" CÓDIGO DE ACTIVACIÓN para {user.email}: {codigo_activacion} ")
            print("═"*50 + "\n")

            return redirect('activar_cuenta')
    else:
        form = RegistroForm()

    return render(request, 'usuarios/registro.html', {'form': form})


def activar_cuenta_view(request):
    user_id         = request.session.get('id_usuario_pendiente')
    codigo_correcto = request.session.get('codigo_activacion_correcto')

    if not user_id or not codigo_correcto:
        return redirect('registro')

    user = get_object_or_404(Usuario, id=user_id)

    if request.method == 'POST':
        codigo_ingresado = request.POST.get('codigo_activacion', '').strip()

        if codigo_ingresado == codigo_correcto:
            user.is_active = True
            user.save()
            del request.session['id_usuario_pendiente']
            del request.session['codigo_activacion_correcto']
            messages.success(
                request,
                f"¡Cuenta verificada! Tu usuario es: {user.username}. Ya puedes iniciar sesión."
            )
            return redirect('login')
        else:
            messages.error(request, "Código de validación incorrecto.")

    return render(request, 'usuarios/activar_cuenta.html')


# ──────────────────────────────────────────────────────────────
# DASHBOARD
# ──────────────────────────────────────────────────────────────

@login_required(login_url='login')
def index_view(request):
    if request.session.pop('mostrar_bienvenida', False):
        nombre = request.user.first_name or request.user.username
        messages.success(request, f"¡Bienvenido de nuevo, {nombre}!")

    return render(request, 'seguridad/index.html')


# ──────────────────────────────────────────────────────────────
# VISTAS ALUMNO
# ──────────────────────────────────────────────────────────────

@login_required(login_url='login')
def mi_proyecto_view(request):
    """El alumno registra su proyecto e integrantes."""
    # 🟢 Corregido: se cambia 'alumno_creador' por 'creado_por'
    mis_proyectos = Proyecto.objects.filter(
        creado_por=request.user
    ).prefetch_related('miembros')

    proyecto_existente = mis_proyectos.exists()

    if request.method == 'POST':
        form    = ProyectoForm(request.POST, request.FILES)
        formset = IntegranteFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            lideres = sum(
                1 for f in formset
                if f.cleaned_data.get('es_lider') and not f.cleaned_data.get('DELETE')
            )
            if lideres != 1:
                messages.error(request, "Debe haber exactamente un integrante marcado como líder.")
            else:
                proyecto = form.save(commit=False)
                # 🟢 Corregido: se asigna al campo real del modelo
                proyecto.creado_por = request.user
                proyecto.save()
                formset.instance = proyecto
                formset.save()
                messages.success(request, "¡Proyecto registrado con éxito en ConEvent!")
                return redirect('mi_proyecto')
    else:
        form    = ProyectoForm()
        formset = IntegranteFormSet()

    return render(request, 'usuarios/mi_proyecto.html', {
        'form':    form,
        'formset': formset,
        'mis_proyectos': mis_proyectos,
        'proyecto_existente': proyecto_existente,
    })


@login_required(login_url='login')
def editar_proyecto_view(request, pk):
    """El alumno edita su proyecto si aún está en revisión."""
    # 🟢 Corregido: se cambia 'alumno_creador' por 'creado_por'
    proyecto = get_object_or_404(Proyecto, pk=pk, creado_por=request.user)

    if proyecto.estatus != 'revision':
        messages.warning(request, "No puedes editar un proyecto que ya fue evaluado.")
        return redirect('mi_proyecto')

    if request.method == 'POST':
        form    = ProyectoForm(request.POST, request.FILES, instance=proyecto)
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
        form    = ProyectoForm(instance=proyecto)
        formset = IntegranteFormSet(instance=proyecto)

    return render(request, 'usuarios/editar_proyecto.html', {
        'form': form, 'formset': formset, 'proyecto': proyecto,
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

    # ✅ related_name correcto: miembros
    proyectos = Proyecto.objects.filter(
        evaluador_asignado=request.user
    ).prefetch_related('miembros').select_related('carrera')

    return render(request, 'usuarios/proyectos_asignados.html', {'proyectos': proyectos})


@login_required(login_url='login')
def evaluar_proyecto_view(request, pk):
    """El evaluador crea/actualiza una Evaluacion para un proyecto."""
    if not request.user.es_evaluador:
        messages.error(request, "No tienes permiso.")
        return redirect('index')

    proyecto = get_object_or_404(Proyecto, pk=pk, evaluador_asignado=request.user)

    # Busca evaluación existente o prepara una nueva
    evaluacion_existente = Evaluacion.objects.filter(
        proyecto=proyecto, evaluador=request.user
    ).first()

    if request.method == 'POST':
        form = EvaluacionForm(request.POST, instance=evaluacion_existente)
        if form.is_valid():
            evaluacion = form.save(commit=False)
            evaluacion.proyecto  = proyecto
            evaluacion.evaluador = request.user
            evaluacion.save()

            # Actualizar estatus y calificación en el Proyecto para consulta rápida
            proyecto.estatus      = evaluacion.estatus_sugerido
            proyecto.calificacion = evaluacion.calificacion
            proyecto.save(update_fields=['estatus', 'calificacion'])

            messages.success(request, f'Evaluación guardada para "{proyecto.titulo}".')
            return redirect('proyectos_asignados')
    else:
        form = EvaluacionForm(instance=evaluacion_existente)

    return render(request, 'usuarios/evaluar_proyecto.html', {
        'form':       form,
        'proyecto':   proyecto,
        'integrantes': proyecto.miembros.all(),  # ✅ related_name correcto
        'ya_evaluado': evaluacion_existente is not None,
    })


# ──────────────────────────────────────────────────────────────
# VISTAS ADMINISTRADOR
# ──────────────────────────────────────────────────────────────

@login_required(login_url='login')
def panel_admin_view(request):
    """Panel del administrador con filtros."""
    if not request.user.es_admin:
        messages.error(request, "No tienes permiso.")
        return redirect('index')

    # ✅ Campos correctos: alumno_creador, miembros
    qs = Proyecto.objects.select_related(
        'alumno_creador', 'evaluador_asignado', 'carrera'
    ).prefetch_related('miembros')

    q       = request.GET.get('q', '').strip()
    estatus = request.GET.get('estatus', '')

    if q:
        qs = qs.filter(
            Q(titulo__icontains=q) | Q(alumno_creador__username__icontains=q)
        )
    if estatus:
        qs = qs.filter(estatus=estatus)

    return render(request, 'usuarios/panel_admin.html', {
        'proyectos':       qs,
        'evaluadores':     Usuario.objects.filter(rol='EVALUADOR'),
        'q':               q,
        'estatus_filtro':  estatus,
        'estatus_choices': Proyecto.ESTATUS_CHOICES,
    })


@login_required(login_url='login')
def asignar_evaluador_view(request, pk):
    """El admin asigna un evaluador."""
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
        'form': form, 'proyecto': proyecto,
    })


# ──────────────────────────────────────────────────────────────
# REGISTRO DE PROYECTO (wizard)
# ──────────────────────────────────────────────────────────────

@login_required(login_url='login')
def registrar_proyecto_view(request):
    """Vista del wizard de registro de proyecto (paso a paso en JS)."""
    
    # 🟢 VALIDACIÓN EXTRA: Si el alumno ya creó un proyecto, lo mandamos a su panel
    if Proyecto.objects.filter(creado_por=request.user).exists():
        messages.warning(request, "Ya cuentas con un proyecto registrado en el sistema.")
        return redirect('mi_proyecto')

    if request.method == 'POST':
        titulo      = request.POST.get('titulo', '').strip()
        carrera_id  = request.POST.get('carrera')
        categoria   = request.POST.get('categoria', 'software')
        grupo       = request.POST.get('grupo', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        logo        = request.FILES.get('logo')

        matriculas      = request.POST.getlist('matricula[]')
        nombres_lista   = request.POST.getlist('nombres[]')
        apellidos_lista = request.POST.getlist('apellidos[]')

        if not matriculas or not matriculas[0].strip():
            messages.error(request, "Debe registrar al menos un integrante (Tú como líder).")
            return render(request, 'usuarios/registrar_proyecto.html', {'carreras': Carrera.objects.all()})

        try:
            carrera_obj = Carrera.objects.filter(pk=carrera_id).first()

            with transaction.atomic():
                # 1. Creamos el proyecto asociándolo al alumno actual
                proyecto = Proyecto.objects.create(
                    titulo=titulo,
                    carrera=carrera_obj,
                    categoria=categoria,
                    grupo=grupo,
                    descripcion=descripcion,
                    logo=logo,
                    estatus='revision',
                    creado_por=request.user,
                )
                
                # 2. Iteramos los integrantes agregados en el paso 2 del Wizard
                for i, matricula in enumerate(matriculas):
                    if matricula.strip() and nombres_lista[i].strip():
                        nombre_completo = f"{nombres_lista[i].strip()} {apellidos_lista[i].strip()}".strip()
                        
                        # El primer integrante (índice 0) se guarda automáticamente como líder
                        Integrante.objects.create(
                            proyecto=proyecto,
                            matricula=matricula.strip(),
                            nombre_completo=nombre_completo,
                            correo=f"{matricula.strip()}@alumnos.uteq.edu.mx",
                            es_lider=(i == 0),
                        )

            messages.success(request, "¡Proyecto registrado con éxito!")
            return redirect('mi_proyecto')

        except Exception as e:
            messages.error(request, f"Error al guardar el proyecto: {str(e)}")

    return render(request, 'usuarios/registrar_proyecto.html', {
        'carreras': Carrera.objects.all()
    })

@login_required
def ver_calificacion_view(request):
    # 1. Intentamos buscar si el alumno logueado tiene un proyecto registrado
    proyecto = Proyecto.objects.filter(creado_por=request.user).first()
    
    evaluacion = None
    if proyecto:
        # 2. Si tiene proyecto, buscamos si ya cuenta con una evaluación realizada
        evaluacion = Evaluacion.objects.filter(proyecto=proyecto).first()

    context = {
        'proyecto': proyecto,
        'evaluacion': evaluacion,
    }
    return render(request, 'seguridad/mis_calificaciones.html', context)