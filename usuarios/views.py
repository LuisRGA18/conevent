from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required

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