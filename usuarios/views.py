from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Avg, Count
from django.db import transaction
import unicodedata
import random
# 🟢 Aseguramos todos los modelos importados correctamente
from .models import Proyecto, Usuario, Integrante, Evaluacion, Carrera 
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
                if request.COOKIES.get(f'dispositivo_seguro_{user.id}') == 'true':
                    login(request, user)
                    request.session['mostrar_bienvenida'] = True
                    return redirect('index')

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
            user.is_active  = False   
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
# DASHBOARD PRINCIPAL (CON CONTADORES REALES)
# ──────────────────────────────────────────────────────────────

@login_required(login_url='login')
def index_view(request):
    if request.session.pop('mostrar_bienvenida', False):
        nombre = request.user.first_name or request.user.username
        messages.success(request, f"¡Bienvenido de nuevo, {nombre}!")

    stats = {}
    rol = request.user.rol

    if request.user.es_admin or rol == 'ADMIN':
        stats = {
            'total_usuarios': Usuario.objects.count(),
            'total_proyectos': Proyecto.objects.count(),
            'evaluados': Proyecto.objects.filter(calificacion__isnull=False).count(),
            'sin_evaluador': Proyecto.objects.filter(evaluador_asignado__isnull=True).count()
        }

    return render(request, 'seguridad/index.html', {'stats': stats})


# ──────────────────────────────────────────────────────────────
# VISTAS ALUMNO (REGISTRO, PANEL Y CONTROL TOTAL)
# ──────────────────────────────────────────────────────────────

@login_required(login_url='login')
def panel_alumno_view(request):
    """🟢 Home/Dashboard del Alumno: Resuelve el bug del POST y envía variables exactas."""
    if request.user.rol != 'ALUMNO':
        return redirect('index')
        
    if request.method == 'POST':
        # Procesamos la creación/edición del proyecto delegando a la vista unificada
        return registrar_proyecto_view(request)
        
    proyecto = Proyecto.objects.filter(creado_por=request.user).prefetch_related('miembros').first()
    carreras = Carrera.objects.all()
    
    return render(request, 'usuarios/registrar_proyecto.html', {
        'proyecto': proyecto,
        'proyecto_registrado': proyecto,
        'miembros': proyecto.miembros.all() if proyecto else [],
        'carreras': carreras,
    })


@login_required(login_url='login')
def registrar_proyecto_view(request):
    """🟢 Vista unificada de Gestión y Formulario: Remueve restricciones de estatus e inyecta al líder y compañeros."""
    if request.user.rol != 'ALUMNO':
        messages.error(request, "Solo los alumnos pueden acceder a esta sección.")
        return redirect('index')

    # Contingencia carreras vacías
    if not Carrera.objects.exists():
        Carrera.objects.create(nombre="Ingeniería en Redes Inteligentes y Ciberseguridad", clave="IRIC")
        Carrera.objects.create(nombre="Desarrollo de Software Multiplataforma", clave="DSM")
        Carrera.objects.create(nombre="Entornos Virtuales y Negocios Digitales", clave="EVND")

    proyecto = Proyecto.objects.filter(creado_por=request.user).first()

    if request.method == 'POST':
        # Caso A: El proyecto ya existe y se está editando desde el Modal
        if proyecto:
            titulo = request.POST.get('titulo')
            descripcion = request.POST.get('descripcion')
            carrera_id = request.POST.get('carrera')
            grupo = request.POST.get('grupo', '').strip().upper()
            categoria = request.POST.get('categoria')
            
            if titulo and descripcion and carrera_id and grupo:
                proyecto.titulo = titulo
                proyecto.descripcion = descripcion
                proyecto.carrera = Carrera.objects.get(id=carrera_id)
                proyecto.grupo = grupo
                proyecto.categoria = categoria
                if request.FILES.get('logo'):
                    proyecto.logo = request.FILES.get('logo')
                proyecto.save()
                messages.success(request, "¡Los datos de tu proyecto se actualizaron con éxito!")
                return redirect('mi_proyecto')
        
        # Caso B: El proyecto no existe y se está creando desde cero
        else:
            titulo = request.POST.get('titulo')
            descripcion = request.POST.get('descripcion')
            carrera_id = request.POST.get('carrera')
            grupo = request.POST.get('grupo', '').strip().upper()
            categoria = request.POST.get('categoria')
            logo = request.FILES.get('logo')

            if titulo and descripcion and carrera_id and grupo:
                carrera_obj = Carrera.objects.get(id=carrera_id)
                
                with transaction.atomic():
                    # 1. Creamos el proyecto limpio
                    nuevo_proyecto = Proyecto.objects.create(
                        titulo=titulo,
                        descripcion=descripcion,
                        carrera=carrera_obj,
                        grupo=grupo,
                        categoria=categoria,
                        logo=logo,
                        creado_por=request.user
                    )

                    # 2. AUTOMÁTICO: Insertamos al creador logueado como Integrante Líder
                    Integrante.objects.create(
                        proyecto=nuevo_proyecto,
                        nombre_completo=f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username,
                        matricula=request.user.matricula_empleado or "2023XXXXXX",
                        correo=request.user.email,
                        es_lider=True
                    )

                    # 3. ADICIONALES: Procesamos los integrantes extras del wizard
                    extra_matriculas = request.POST.getlist('extra_matricula[]')
                    extra_nombres = request.POST.getlist('extra_nombres[]')
                    extra_apellidos = request.POST.getlist('extra_apellidos[]')
                    
                    for i in range(len(extra_matriculas)):
                        mat = extra_matriculas[i].strip()
                        nom = extra_nombres[i].strip()
                        ape = extra_apellidos[i].strip()
                        
                        if mat and nom:
                            nombre_completo = f"{nom} {ape}".strip()
                            Integrante.objects.create(
                                proyecto=nuevo_proyecto,
                                nombre_completo=nombre_completo,
                                matricula=mat,
                                correo=f"{mat}@alumnos.uteq.edu.mx",
                                es_lider=False
                            )

                messages.success(request, "¡Proyecto registrado con éxito! Te hemos asignado automáticamente como líder de equipo.")
                return redirect('mi_proyecto')
            else:
                messages.error(request, "Por favor, completa todos los campos obligatorios.")

    carreras = Carrera.objects.all()
    return render(request, 'usuarios/registrar_proyecto.html', {
        'proyecto_registrado': proyecto,
        'proyecto': proyecto,
        'carreras': carreras,
    })


@login_required(login_url='login')
def eliminar_proyecto_view(request, pk):
    """🟢 Endpoint POST definitivo para eliminar el proyecto y limpiar el flujo."""
    if request.user.rol != 'ALUMNO':
        return redirect('index')
        
    proyecto = get_object_or_404(Proyecto, pk=pk, creado_por=request.user)
    
    if request.method == 'POST':
        proyecto.delete()
        messages.success(request, "Tu proyecto fue eliminado correctamente del sistema ConEvent.")
        return redirect('mi_proyecto')
        
    return redirect('mi_proyecto')


@login_required(login_url='login')
def ver_calificacion_view(request):
    proyecto = Proyecto.objects.filter(creado_por=request.user).first()
    evaluacion = None
    if proyecto:
        evaluacion = Evaluacion.objects.filter(proyecto=proyecto).first()

    context = {
        'proyecto': proyecto,
        'evaluacion': evaluacion,
    }
    return render(request, 'seguridad/mis_calificaciones.html', context)


# ──────────────────────────────────────────────────────────────
# VISTAS EVALUADOR
# ──────────────────────────────────────────────────────────────

@login_required(login_url='login')
def proyectos_asignados_view(request):
    if not request.user.es_evaluador:
        messages.error(request, "No tienes permiso para acceder a esta sección.")
        return redirect('index')

    proyectos = Proyecto.objects.filter(
        evaluador_asignado=request.user
    ).prefetch_related('miembros').select_related('carrera')

    return render(request, 'usuarios/proyectos_asignados.html', {'proyectos': proyectos})


@login_required(login_url='login')
def evaluar_proyecto_view(request, pk):
    if not request.user.es_evaluador:
        messages.error(request, "No tienes permiso.")
        return redirect('index')

    proyecto = get_object_or_404(Proyecto, pk=pk, evaluador_asignado=request.user)
    evaluacion_existente = Evaluacion.objects.filter(
        proyecto=proyecto, evaluador=request.user
    ).first()

    criterios = CriterioEvaluacion.objects.filter(activo=True)
    
    # Cargar calificaciones de criterios si ya existen
    detalles_existentes = {}
    if evaluacion_existente:
        for det in evaluacion_existente.detalles.all():
            detalles_existentes[det.criterio_id] = det.calificacion_cualitativa

    if request.method == 'POST':
        form = EvaluacionForm(request.POST, instance=evaluacion_existente)
        
        # Si hay criterios, la calificación numérica se calculará por lo que prellenamos con 0.0
        if criterios.exists():
            post_data = request.POST.copy()
            post_data['calificacion'] = '0.00'
            form = EvaluacionForm(post_data, instance=evaluacion_existente)

        if form.is_valid():
            error_rubrica = False
            respuestas_criterios = {}
            if criterios.exists():
                for c in criterios:
                    clave_post = f"criterio_{c.id}"
                    valor = request.POST.get(clave_post)
                    if not valor or valor not in ['AU', 'DE', 'SA', 'NA']:
                        error_rubrica = True
                        messages.error(request, f"Por favor, selecciona una calificación para el criterio: {c.nombre}")
                    else:
                        respuestas_criterios[c.id] = valor
            
            if not error_rubrica:
                with transaction.atomic():
                    # 1. Guardar la evaluación base
                    evaluacion = form.save(commit=False)
                    evaluacion.proyecto  = proyecto
                    evaluacion.evaluador = request.user
                    evaluacion.save()

                    # 2. Guardar detalles de la rúbrica si existen
                    if criterios.exists():
                        for c_id, val_cualitativo in respuestas_criterios.items():
                            criterio_obj = CriterioEvaluacion.objects.get(id=c_id)
                            DetalleEvaluacion.objects.update_or_create(
                                evaluacion=evaluacion,
                                criterio=criterio_obj,
                                defaults={'calificacion_cualitativa': val_cualitativo}
                            )
                        # Forzar recalculación para actualizar Evaluación y Proyecto
                        evaluacion.recalcular_calificacion()
                    else:
                        # Si es evaluación directa, guardar la calificación ingresada
                        proyecto.calificacion = evaluacion.calificacion
                        proyecto.save(update_fields=['calificacion'])

                    # 3. Guardar estatus sugerido en el proyecto
                    proyecto.estatus = evaluacion.estatus_sugerido
                    proyecto.save(update_fields=['estatus'])

                messages.success(request, f'Evaluación guardada con éxito para "{proyecto.titulo}".')
                return redirect('proyectos_asignados')
    else:
        form = EvaluacionForm(instance=evaluacion_existente)

    return render(request, 'usuarios/evaluar_proyecto.html', {
        'form':       form,
        'proyecto':   proyecto,
        'integrantes': proyecto.miembros.all(),  
        'ya_evaluado': evaluacion_existente is not None,
        'criterios':  criterios,
        'detalles_existentes': detalles_existentes,
    })


# ──────────────────────────────────────────────────────────────
# VISTAS ADMINISTRADOR
# ──────────────────────────────────────────────────────────────

@login_required(login_url='login')
def panel_admin_view(request):
    if not request.user.es_admin and request.user.rol != 'ADMIN':
        messages.error(request, "No tienes permiso.")
        return redirect('index')

    qs = Proyecto.objects.select_related(
        'creado_por', 'evaluador_asignado', 'carrera'
    ).prefetch_related('miembros', 'asignaciones_stands__stand')

    q       = request.GET.get('q', '').strip()
    estatus = request.GET.get('estatus', '').strip()

    if q:
        qs = qs.filter(
            Q(titulo__icontains=q) | 
            Q(creado_por__username__icontains=q) |
            Q(creado_por__first_name__icontains=q)
        )
    if estatus:
        qs = qs.filter(estatus=estatus)

    qs = qs.order_by('-id')

    return render(request, 'usuarios/panel_admin.html', {
        'todos_los_proyectos': qs,
        'todos_los_docentes':  Usuario.objects.filter(rol='EVALUADOR'),
        'q':               q,
        'estatus_filtro':  estatus,
        'estatus_choices': Proyecto.ESTATUS_CHOICES,
    })


@login_required(login_url='login')
def cambiar_estatus_proyecto_view(request, pk):
    if not request.user.es_admin and request.user.rol != 'ADMIN':
        return redirect('index')
        
    proyecto = get_object_or_404(Proyecto, pk=pk)
    if request.method == 'POST':
        nuevo_estatus = request.POST.get('nuevo_estatus')
        if nuevo_estatus in ['revision', 'aprobado', 'rechazado']:
            proyecto.estatus = nuevo_estatus
            proyecto.save(update_fields=['estatus'])
            messages.success(request, f'Estatus del proyecto "{proyecto.titulo}" cambiado a: {proyecto.get_estatus_display()}.')
    return redirect('panel_admin')


@login_required(login_url='login')
def asignar_evaluador_view(request, pk):
    if not request.user.es_admin and request.user.rol != 'ADMIN':
        return redirect('index')

    proyecto = get_object_or_404(Proyecto, pk=pk)

    if request.method == 'POST':
        docente_id = request.POST.get('docente_id')
        if docente_id:
            docente = get_object_or_404(Usuario, pk=docente_id, rol='EVALUADOR')
            proyecto.evaluador_asignado = docente
            proyecto.save(update_fields=['evaluador_asignado'])
            messages.success(request, f'Docente {docente.get_full_name() or docente.username} asignado correctamente a "{proyecto.titulo}".')
        else:
            proyecto.evaluador_asignado = None
            proyecto.save(update_fields=['evaluador_asignado'])
            messages.info(request, f'Se retiró el evaluador de "{proyecto.titulo}".')
            
    return redirect('panel_admin')


@login_required(login_url='login')
def guardar_comentario_admin_view(request, pk):
    if not request.user.es_admin and request.user.rol != 'ADMIN':
        return redirect('index')

    proyecto = get_object_or_404(Proyecto, pk=pk)
    if request.method == 'POST':
        comentarios = request.POST.get('comentarios', '').strip()
        proyecto.comentarios_evaluador = comentarios
        proyecto.save(update_fields=['comentarios_evaluador'])
        messages.success(request, f'Comentarios actualizados para "{proyecto.titulo}".')
    return redirect('panel_admin')


@login_required(login_url='login')
def editar_proyecto_view(request, pk):
    """
    Permite al alumno creador editar su proyecto si y solo si
    este se encuentra con estatus 'revision'.
    """
    if request.user.rol != 'ALUMNO':
        messages.error(request, "Solo los alumnos pueden acceder a esta sección.")
        return redirect('index')

    proyecto = get_object_or_404(Proyecto, pk=pk, creado_por=request.user)

    if proyecto.estatus != 'revision':
        messages.error(request, "No puedes editar tu proyecto si ya ha sido evaluado o tiene un estatus aprobado/rechazado.")
        return redirect('mi_proyecto')

    if request.method == 'POST':
        form = ProyectoForm(request.POST, request.FILES, instance=proyecto)
        formset = IntegranteFormSet(request.POST, instance=proyecto)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, "¡Los datos de tu proyecto se actualizaron con éxito!")
            return redirect('mi_proyecto')
        else:
            messages.error(request, "Por favor, corrige los errores en el formulario.")
    else:
        form = ProyectoForm(instance=proyecto)
        formset = IntegranteFormSet(instance=proyecto)

    return render(request, 'usuarios/editar_proyecto.html', {
        'proyecto': proyecto,
        'form': form,
        'formset': formset,
    })