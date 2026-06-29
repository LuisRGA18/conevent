from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Avg, Count
from django.db import transaction
import unicodedata
import random
from django.core.mail import send_mail
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.utils import timezone

# Imports de ReportLab y QRCode
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.platypus import Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# 🟢 Aseguramos todos los modelos importados correctamente
from .models import (
    Usuario,
    Proyecto,
    Carrera,
    Integrante,
    CriterioEvaluacion,
    Evaluacion,
    DetalleEvaluacion,
    EvaluacionExterna,
    LogActividad,
)
from .forms import (
    ProyectoForm, RegistroForm,
    IntegranteFormSet, EvaluacionForm, AsignacionEvaluadorForm
)

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

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
                    LogActividad.objects.create(
                        usuario=user,
                        tipo='login',
                        descripcion="Inicio de sesión directo (dispositivo seguro)",
                        ip=get_client_ip(request)
                    )
                    return redirect('index')

                codigo_generado = str(random.randint(100000, 999999))
                request.session['pre_auth_user_id']    = user.id
                request.session['codigo_2fa_correcto'] = codigo_generado

                send_mail(
                    subject="Tu código de verificación — CONEVENT",
                    message=f"Tu código de verificación de inicio de sesión de dos factores es: {codigo_generado}",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )

                return redirect('verificar_2fa')
            else:
                messages.error(request, "Esta cuenta se encuentra desactivada.")
                LogActividad.objects.create(
                    usuario=user,
                    tipo='login_fallido',
                    descripcion="Intento de inicio de sesión fallido: cuenta desactivada",
                    ip=get_client_ip(request)
                )
        else:
            messages.error(request, "Usuario o contraseña incorrectos.")
            LogActividad.objects.create(
                usuario=None,
                tipo='login_fallido',
                descripcion=f"Intento de inicio de sesión fallido para el usuario/correo: '{usuario}'",
                ip=get_client_ip(request)
            )

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

            LogActividad.objects.create(
                usuario=user,
                tipo='2fa_exitoso',
                descripcion="Verificación 2FA exitosa",
                ip=get_client_ip(request)
            )
            LogActividad.objects.create(
                usuario=user,
                tipo='login',
                descripcion="Inicio de sesión completado tras 2FA",
                ip=get_client_ip(request)
            )

            response = redirect('index')
            if recordar == 'si':
                response.set_cookie(
                    f'dispositivo_seguro_{user.id}', 'true',
                    max_age=24 * 60 * 60, httponly=True
                )
            return response
        else:
            messages.error(request, "Código de verificación incorrecto.")
            LogActividad.objects.create(
                usuario=user,
                tipo='2fa_fallido',
                descripcion="Código 2FA incorrecto ingresado",
                ip=get_client_ip(request)
            )

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

            LogActividad.objects.create(
                usuario=user,
                tipo='registro',
                descripcion=f"Registro de nuevo usuario creado (pendiente activación): {user.username} (rol: {user.rol})",
                ip=get_client_ip(request)
            )

            codigo_activacion = str(random.randint(100000, 999999))
            request.session['id_usuario_pendiente']     = user.id
            request.session['codigo_activacion_correcto'] = codigo_activacion

            send_mail(
                subject="Tu código de verificación — CONEVENT",
                message=f"Tu código de activación de cuenta es: {codigo_activacion}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )

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

def generar_qr_externo_proyecto(proyecto, base_url):
    qr_url = f"{base_url.rstrip('/')}/proyectos/{proyecto.id}/evaluar-externo/"
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(qr_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    
    filename = f"qr_{proyecto.id}.png"
    proyecto.qr_evaluacion_externa.save(filename, ContentFile(buffer.getvalue()), save=True)


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
    
    form = ProyectoForm(instance=proyecto) if proyecto else None
    formset = IntegranteFormSet(instance=proyecto) if proyecto else None
    
    return render(request, 'usuarios/registrar_proyecto.html', {
        'proyecto': proyecto,
        'proyecto_registrado': proyecto,
        'miembros': proyecto.miembros.all() if proyecto else [],
        'carreras': carreras,
        'form': form,
        'formset': formset,
    })


@login_required(login_url='login')
def registrar_proyecto_view(request):
    """🟢 Vista unificada de Gestión y Formulario: Remueve restricciones de estatus e inyecta al líder y compañeros."""
    if request.user.rol != 'ALUMNO':
        messages.error(request, "Solo los alumnos pueden acceder a esta sección.")
        return redirect('index')

    # Contingencia carreras vacías
    if not Carrera.objects.exists():
        messages.error(request, "No hay carreras registradas. Contacta al administrador del evento.")

    proyecto = Proyecto.objects.filter(creado_por=request.user).first()

    if request.method == 'POST':
        # Caso A: El proyecto ya existe y se está editando
        if proyecto:
            form = ProyectoForm(request.POST, request.FILES, instance=proyecto)
            formset = IntegranteFormSet(request.POST, instance=proyecto)
            if form.is_valid() and formset.is_valid():
                # Enforce that the leader is NOT deleted and es_lider remains True
                for f in formset.forms:
                    if f.instance.pk and f.instance.es_lider:
                        f.cleaned_data['DELETE'] = False
                        f.cleaned_data['es_lider'] = True
                        
                with transaction.atomic():
                    form.save()
                    formset.save()
                messages.success(request, "¡Los datos de tu proyecto se actualizaron con éxito!")
                return redirect('mi_proyecto')
            else:
                messages.error(request, "Por favor, corrige los errores en el formulario.")
        
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

                    # 4. Generación automática de QR para evaluación externa
                    base_url = request.build_absolute_uri('/')
                    generar_qr_externo_proyecto(nuevo_proyecto, base_url)

                messages.success(request, "¡Proyecto registrado con éxito! Te hemos asignado automáticamente como líder de equipo.")
                return redirect('mi_proyecto')
            else:
                messages.error(request, "Por favor, completa todos los campos obligatorios.")

    # GET response (or invalid POST)
    carreras = Carrera.objects.all()
    if request.method == 'POST' and proyecto:
        # form and formset are already bound with errors
        pass
    else:
        form = ProyectoForm(instance=proyecto) if proyecto else None
        formset = IntegranteFormSet(instance=proyecto) if proyecto else None

    return render(request, 'usuarios/registrar_proyecto.html', {
        'proyecto_registrado': proyecto,
        'proyecto': proyecto,
        'carreras': carreras,
        'form': form,
        'formset': formset,
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

                    # 🟢 Registrar log de auditoría
                    evaluacion.refresh_from_db()
                    LogActividad.objects.create(
                        usuario=request.user,
                        tipo='evaluacion',
                        descripcion=f"Evaluación registrada/actualizada para proyecto '{proyecto.titulo}' (Código: {proyecto.codigo}) con calificación: {evaluacion.calificacion}",
                        ip=get_client_ip(request)
                    )

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

    from django.db.models import Count, Avg, Case, When, Value, FloatField

    calificacion_numerica_expr = Case(
        When(evaluaciones_externas__calificacion='AU', then=Value(10.0)),
        When(evaluaciones_externas__calificacion='DE', then=Value(9.0)),
        When(evaluaciones_externas__calificacion='SA', then=Value(8.0)),
        When(evaluaciones_externas__calificacion='NA', then=Value(6.0)),
        default=Value(0.0),
        output_field=FloatField()
    )

    qs = Proyecto.objects.select_related(
        'creado_por', 'evaluador_asignado', 'carrera'
    ).prefetch_related('miembros', 'asignaciones_stands__stand').annotate(
        num_externas=Count('evaluaciones_externas', distinct=True),
        promedio_externa=Avg(calificacion_numerica_expr)
    )

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
            LogActividad.objects.create(
                usuario=request.user,
                tipo='cambio_estatus',
                descripcion=f"Estatus del proyecto '{proyecto.titulo}' cambiado a: {proyecto.get_estatus_display()}",
                ip=get_client_ip(request)
            )
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
            # Enforce that the leader is NOT deleted and es_lider remains True
            for f in formset.forms:
                if f.instance.pk and f.instance.es_lider:
                    f.cleaned_data['DELETE'] = False
                    f.cleaned_data['es_lider'] = True
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


# ──────────────────────────────────────────────────────────────
# EVALUACION EXTERNA PÚBLICA Y ENLACES QR
# ──────────────────────────────────────────────────────────────

def evaluar_externo_view(request, proyecto_id):
    from decouple import config
    proyecto = get_object_or_404(Proyecto, id=proyecto_id)
    error_msg = None
    exito = False

    if request.method == 'POST':
        nombre_visitante = request.POST.get('nombre_visitante', '').strip()
        empresa_procedencia = request.POST.get('empresa_procedencia', '').strip()
        correo_contacto = request.POST.get('correo_contacto', '').strip().lower()
        telefono_contacto = request.POST.get('telefono_contacto', '').strip()
        calificacion = request.POST.get('calificacion', '').strip()
        comentario = request.POST.get('comentario', '').strip()
        codigo_acceso = request.POST.get('codigo_acceso', '').strip()

        if not nombre_visitante or not empresa_procedencia or not correo_contacto or not calificacion or not codigo_acceso:
            error_msg = "Por favor, completa todos los campos obligatorios."
        elif codigo_acceso != config('CODIGO_EVALUACION_EXTERNA', default='UTEQ2025'):
            error_msg = "Código de acceso incorrecto. Solicita el código correcto en el stand del proyecto."
        elif calificacion not in ['AU', 'DE', 'SA', 'NA']:
            error_msg = "Opción de calificación no válida."
        elif EvaluacionExterna.objects.filter(proyecto=proyecto, correo_contacto=correo_contacto).exists():
            error_msg = "Este correo electrónico ya ha registrado una evaluación para este proyecto."
        else:
            EvaluacionExterna.objects.create(
                proyecto=proyecto,
                nombre_visitante=nombre_visitante,
                empresa_procedencia=empresa_procedencia,
                correo_contacto=correo_contacto,
                telefono_contacto=telefono_contacto,
                calificacion=calificacion,
                comentario=comentario,
                codigo_acceso_usado=codigo_acceso
            )
            LogActividad.objects.create(
                usuario=None,
                tipo='evaluacion_externa',
                descripcion=f"Evaluación externa registrada por '{nombre_visitante}' ({empresa_procedencia}) para proyecto '{proyecto.titulo}' con calificación: {calificacion}",
                ip=get_client_ip(request)
            )
            exito = True

    return render(request, 'usuarios/evaluar_externo.html', {
        'proyecto': proyecto,
        'error_msg': error_msg,
        'exito': exito,
    })


@login_required(login_url='login')
def qr_externo_view(request, proyecto_id):
    if request.user.rol != 'ADMIN' and not request.user.es_admin:
        return HttpResponse("Acceso denegado", status=403)
        
    proyecto = get_object_or_404(Proyecto, id=proyecto_id)
    url = request.build_absolute_uri(f"/proyectos/{proyecto.id}/evaluar-externo/")
    
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    response = HttpResponse(content_type="image/png")
    img.save(response, "PNG")
    return response


@login_required(login_url='login')
def qr_externo_lote_view(request):
    if request.user.rol != 'ADMIN' and not request.user.es_admin:
        return HttpResponse("Acceso denegado", status=403)
        
    proyectos = Proyecto.objects.all().exclude(estatus='rechazado').order_by('titulo')
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="qr_externos_lote.pdf"'
    
    doc = SimpleDocTemplate(
        response, pagesize=letter,
        rightMargin=36, leftMargin=36,
        topMargin=36, bottomMargin=36
    )
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        alignment=1,
        spaceAfter=15
    )
    label_style = ParagraphStyle(
        'LabelStyle',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        alignment=1
    )
    
    story.append(Paragraph("Códigos QR de Evaluación Externa - Proyectos", title_style))
    story.append(Spacer(1, 10))
    
    data = []
    row = []
    
    for proyecto in proyectos:
        url = request.build_absolute_uri(f"/proyectos/{proyecto.id}/evaluar-externo/")
        
        qr = qrcode.QRCode(version=1, box_size=3, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        buf = BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        
        rl_img = RLImage(buf, width=110, height=110)
        
        carrera_name = proyecto.carrera.clave if proyecto.carrera else "Sin carrera"
        label_text = f"<b>{proyecto.titulo}</b><br/>Carrera: {carrera_name}<br/>Código: {proyecto.codigo}"
        label_p = Paragraph(label_text, label_style)
        
        cell_table = Table([[rl_img], [label_p]], colWidths=[160])
        cell_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('TOPPADDING', (0,0), (-1,-1), 2),
        ]))
        
        row.append(cell_table)
        
        if len(row) == 3:
            data.append(row)
            row = []
            
    if row:
        while len(row) < 3:
            row.append("")
        data.append(row)
        
    if data:
        t = Table(data, colWidths=[180, 180, 180])
        t.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(t)
    else:
        story.append(Paragraph("No hay proyectos registrados.", styles['Normal']))
        
    doc.build(story)
    return response


@login_required(login_url='login')
def admin_logs_view(request):
    if not request.user.es_admin and request.user.rol != 'ADMIN':
        messages.error(request, "No tienes permiso.")
        return redirect('index')

    tipo_filtro = request.GET.get('tipo', '').strip()
    logs = LogActividad.objects.all().select_related('usuario')

    if tipo_filtro:
        logs = logs.filter(tipo=tipo_filtro)

    from django.core.paginator import Paginator
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'usuarios/admin_logs.html', {
        'page_obj': page_obj,
        'tipo_filtro': tipo_filtro,
        'tipo_choices': LogActividad.TIPO_CHOICES,
    })