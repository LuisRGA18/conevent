import uuid
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from .models import ItemInventario, Incidencia
from .serializers import ItemInventarioSerializer, IncidenciaSerializer
from espacios.api_views import IsAdminUserRole

class ItemInventarioViewSet(viewsets.ModelViewSet):
    queryset = ItemInventario.objects.all()
    serializer_class = ItemInventarioSerializer
    
    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsAdminUserRole()]

    def get_object(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_value = self.kwargs[lookup_url_kwarg]
        
        # Intentar buscar por UUID si el formato coincide
        try:
            uuid.UUID(str(lookup_value))
            return ItemInventario.objects.get(uuid=lookup_value)
        except (ValueError, TypeError, ItemInventario.DoesNotExist):
            return super().get_object()

class IncidenciaViewSet(viewsets.ModelViewSet):
    serializer_class = IncidenciaSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.rol == 'ADMIN':
            return Incidencia.objects.all()
        return Incidencia.objects.filter(reportado_por=user)

    def perform_create(self, serializer):
        serializer.save(reportado_por=self.request.user)

    def perform_update(self, serializer):
        # Impedir que usuarios no ADMIN marquen como resuelta o editen comentarios de resolución
        if self.request.user.rol != 'ADMIN':
            serializer.save(
                resuelta=serializer.instance.resuelta,
                comentarios_resolucion=serializer.instance.comentarios_resolucion
            )
        else:
            # Si se marca como resuelta ahora, auto-asignar fecha_resolucion
            if serializer.validated_data.get('resuelta', False) and not serializer.instance.resuelta:
                from django.utils import timezone
                serializer.save(fecha_resolucion=timezone.now())
            else:
                serializer.save()
