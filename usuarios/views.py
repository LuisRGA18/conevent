from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import ProyectoForm, RegistroForm
from .models import Proyecto
import unicodedata
from .models import Usuario

def login_view(request):
    # Si el usuario ya está logueado, lo mandamos directo al inicio
    if request.user.is_authenticated:
        return redirect('index') # Cambiaremos esto al dashboard de conevent después

    if request.method == 'POST':
        usuario = request.POST.get('username')
        clave = request.POST.get('password')
        
        # Autenticación nativa con la base de datos de Django
        user = authenticate(request, username=usuario, password=clave)

        if user is not None:
            if user.is_active:
                login(request, user)
                messages.success(request, f"¡Bienvenido de nuevo, {user.username}!")
                return redirect('index') 
            else:
                messages.error(request, "Esta cuenta se encuentra desactivada.")
        else:
            messages.error(request, "Usuario o contraseña incorrectos.")

    return render(request, 'usuarios/login.html')

def logout_view(request):
    logout(request)
    return redirect('login')

def index_view(request):
    # Una vista temporal para la página de inicio
    return render(request, 'seguridad/index.html') # O el template que gustes usar de base

@login_required(login_url='login')  # <-- AGREGA ESTO PARA PROTEGER LA VISTA
def index_view(request):
    return render(request, 'seguridad/index.html')

@login_required(login_url='login')
def mi_proyecto_view(request):
    # Obtener los proyectos que ha registrado este alumno en específico
    mis_proyectos = Proyecto.objects.filter(alumno_creador=request.user)
    
    if request.method == 'POST':
        form = ProyectoForm(request.POST)
        if form.is_valid():
            proyecto = form.save(commit=False)
            proyecto.alumno_creador = request.user  # Asignamos al alumno logueado
            proyecto.save()
            messages.success(request, "¡Proyecto registrado con éxito y enviado a revisión!")
            return redirect('mi_proyecto')
    else:
        form = ProyectoForm()
        
    return render(request, 'usuarios/mi_proyecto.html', {
        'form': form,
        'mis_proyectos': mis_proyectos
    })
def limpiar_texto(texto):
    """Función auxiliar para quitar acentos, eñes y caracteres especiales"""
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
            
            # Extraemos el primer nombre y el primer apellido
            primer_nombre = limpiar_texto(nombres.split()[0])
            primer_apellido = limpiar_texto(apellidos.split()[0])
            
            # Construimos el formato: nombre.apellido
            username_propuesto = f"{primer_nombre}.{primer_apellido}"
            
            # CONTROL DE DUPLICADOS: Si por coincidencia existe otro "juan.perez", le agregamos un número al final
            contador = 1
            username_final = username_propuesto
            while Usuario.objects.filter(username=username_final).exists():
                username_final = f"{username_propuesto}{contador}"
                contador += 1
            
            # Guardamos los datos limpios en el objeto usuario
            user.username = username_final
            user.first_name = nombres
            user.last_name = apellidos
            user.email = form.cleaned_data['email']
            
            user.set_password(form.cleaned_data['password'])
            user.save()
            
            messages.success(request, f"¡Cuenta creada con éxito! Tu nombre de usuario asignado es: {username_final}")
            return redirect('login')
    else:
        form = RegistroForm()

    return render(request, 'usuarios/registro.html', {'form': form})