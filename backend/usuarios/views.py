from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token

from .models import Perfil, PerfilProfesional, ResultadoAnalisis, Curriculum

from .serializers import (
    RegistroSerializer,
    LoginSerializer,
    PerfilSerializer,
    PerfilProfesionalSerializer,
    ResultadoAnalisisSerializer,
    CurriculumUploadSerializer,
    CurriculumSerializer,
)

from .utils import analizar_perfil, analizar_perfil_ia, extraer_texto_pdf, analizar_cv_ia


@api_view(['GET'])
def ping(request):
    return Response({"message": "Backend TAI funcionando"})


@api_view(['POST'])
def registro(request):
    serializer = RegistroSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)

        return Response({
            "message": "Usuario creado correctamente.",
            "token": token.key
        }, status=201)

    return Response(serializer.errors, status=400)


@api_view(['POST'])
def login(request):
    serializer = LoginSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.validated_data['user']
        token, _ = Token.objects.get_or_create(user=user)
        perfil = Perfil.objects.get(usuario=user)

        return Response({
            "token": token.key,
            "rol": perfil.rol,
            "username": user.username
        })

    return Response(serializer.errors, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def yo(request):
    perfil = Perfil.objects.get(usuario=request.user)
    serializer = PerfilSerializer(perfil)
    return Response(serializer.data)


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def perfil_profesional(request):
    perfil, _ = PerfilProfesional.objects.get_or_create(usuario=request.user)

    if request.method == 'GET':
        serializer = PerfilProfesionalSerializer(perfil)
        return Response(serializer.data)

    if request.method == 'PUT':
        serializer = PerfilProfesionalSerializer(
            perfil,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analisis_perfil(request):
    perfil, _ = PerfilProfesional.objects.get_or_create(usuario=request.user)
    resultado = analizar_perfil(perfil)
    return Response(resultado)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generar_analisis(request):
    perfil, _ = PerfilProfesional.objects.get_or_create(usuario=request.user)
    resultado = analizar_perfil_ia(perfil)

    analisis = ResultadoAnalisis.objects.create(
        usuario=request.user,
        resumen=resultado["resumen"],
        fortalezas=resultado["fortalezas"],
        aspectos_mejora=resultado["aspectos_mejora"],
        recomendaciones=resultado["recomendaciones"],
        puntuacion_completitud=resultado["puntuacion_completitud"],
    )

    serializer = ResultadoAnalisisSerializer(analisis)
    return Response(serializer.data, status=201)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ultimo_analisis(request):
    analisis = ResultadoAnalisis.objects.filter(usuario=request.user).first()

    if not analisis:
        return Response(
            {"detail": "Todavía no tienes ningún análisis generado."},
            status=404
        )

    serializer = ResultadoAnalisisSerializer(analisis)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def historial_analisis(request):
    analisis = ResultadoAnalisis.objects.filter(usuario=request.user)
    serializer = ResultadoAnalisisSerializer(analisis, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser])
def subir_cv(request):
    serializer = CurriculumUploadSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    archivo = serializer.validated_data['archivo']
    texto = extraer_texto_pdf(archivo)
    resultado = analizar_cv_ia(texto)

    curriculum = Curriculum.objects.create(
        usuario=request.user,
        archivo=archivo,
        nombre_archivo=archivo.name,
        texto_extraido=texto,
        resumen=resultado["resumen"],
        puntuacion=resultado["puntuacion"],
        fortalezas=resultado["fortalezas"],
        debilidades=resultado["debilidades"],
        recomendaciones=resultado["recomendaciones"],
    )

    return Response(CurriculumSerializer(curriculum).data, status=201)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ultimo_cv(request):
    curriculum = Curriculum.objects.filter(usuario=request.user).first()

    if not curriculum:
        return Response(
            {"detail": "Todavía no has subido ningún CV."},
            status=404
        )

    serializer = CurriculumSerializer(curriculum)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def historial_cv(request):
    curriculums = Curriculum.objects.filter(usuario=request.user)
    serializer = CurriculumSerializer(curriculums, many=True)
    return Response(serializer.data)