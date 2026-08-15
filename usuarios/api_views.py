from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Proyecto, Usuario, Carrera, Evaluacion, CriterioEvaluacion
from .serializers import (
    UsuarioSerializer, CarreraSerializer, ProyectoSerializer,
    EvaluacionSerializer, CriterioEvaluacionSerializer
)

class UserMeView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        serializer = UsuarioSerializer(request.user)
        data = serializer.data
        if request.user.rol == 'ALUMNO':
            proyectos = request.user.proyectos.all()
            data['proyectos'] = ProyectoSerializer(proyectos, many=True, context={'request': request}).data
        elif request.user.rol == 'EVALUADOR':
            proyectos = request.user.proyectos_a_evaluar.all()
            data['proyectos_asignados'] = ProyectoSerializer(proyectos, many=True, context={'request': request}).data
        return Response(data)

class ProyectoViewSet(viewsets.ModelViewSet):
    serializer_class = ProyectoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.rol == 'ADMIN':
            return Proyecto.objects.all()
        elif user.rol == 'EVALUADOR':
            return Proyecto.objects.filter(evaluadores=user)
        elif user.rol == 'ALUMNO':
            return Proyecto.objects.filter(creado_por=user)
        return Proyecto.objects.none()

    def perform_create(self, serializer):
        if self.request.user.rol == 'ALUMNO':
            serializer.save(creado_por=self.request.user)
        else:
            serializer.save()

class CarreraViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Carrera.objects.all()
    serializer_class = CarreraSerializer
    permission_classes = [AllowAny]

class UsuarioViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UsuarioSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.rol == 'ADMIN':
            return Usuario.objects.filter(rol='EVALUADOR')
        return Usuario.objects.none()

class CriterioEvaluacionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CriterioEvaluacion.objects.filter(activo=True)
    serializer_class = CriterioEvaluacionSerializer
    permission_classes = [IsAuthenticated]

class EvaluacionViewSet(viewsets.ModelViewSet):
    serializer_class = EvaluacionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.rol == 'ADMIN':
            return Evaluacion.objects.all()
        elif user.rol == 'EVALUADOR':
            return Evaluacion.objects.filter(evaluador=user)
        elif user.rol == 'ALUMNO':
            return Evaluacion.objects.filter(proyecto__creado_por=user)
        return Evaluacion.objects.none()

    def perform_create(self, serializer):
        serializer.save(evaluador=self.request.user)
