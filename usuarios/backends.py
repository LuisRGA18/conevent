from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from .models import Usuario


class EmailOrUsernameBackend(ModelBackend):
    """
    Permite iniciar sesión con nombre de usuario O correo institucional.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # Busca un usuario que coincida con el username O el email
            user = Usuario.objects.get(
                Q(username__iexact=username) | Q(email__iexact=username)
            )
        except Usuario.DoesNotExist:
            return None
        except Usuario.MultipleObjectsReturned:
            # Si por alguna razón hay duplicados, toma el primero activo
            user = Usuario.objects.filter(
                Q(username__iexact=username) | Q(email__iexact=username)
            ).filter(is_active=True).first()
            if not user:
                return None

        # Verifica la contraseña y que el usuario tenga permiso
        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None