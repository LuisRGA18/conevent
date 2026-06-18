from rest_framework import viewsets, permissions
from rest_framework.permissions import BasePermission
from .models import Stand, AsignacionStand
from .serializers import StandSerializer, AsignacionStandSerializer

class IsAdminUserRole(BasePermission):
    """
    Permiso personalizado que permite el acceso de escritura solo a administradores.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.rol == 'ADMIN'

class StandViewSet(viewsets.ModelViewSet):
    queryset = Stand.objects.all()
    serializer_class = StandSerializer
    
    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsAdminUserRole()]

class AsignacionStandViewSet(viewsets.ModelViewSet):
    queryset = AsignacionStand.objects.all()
    serializer_class = AsignacionStandSerializer
    
    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsAdminUserRole()]
