from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token

from .models import (
    Perfil,
    PerfilProfesional,
    ResultadoAnalisis,
    Curriculum,
    Oferta,
    OptimizacionLinkedIn,
    SimulacionEntrevista,
    PreguntaRespuesta,
)

from .serializers import (
    RegistroSerializer,
    LoginSerializer,
    PerfilSerializer,
    PerfilProfesionalSerializer,
    ResultadoAnalisisSerializer,
    CurriculumUploadSerializer,
    CurriculumSerializer,
    OfertaCreateSerializer,
    OfertaSerializer,
    BusquedaEmpleoInputSerializer,
    OptimizacionLinkedInCreateSerializer,
    OptimizacionLinkedInSerializer,
    FinalizarEntrevistaSerializer,
    SimulacionEntrevistaSerializer,
)

from .utils import analizar_perfil, analizar_perfil_ia, extraer_texto_pdf, analizar_cv_ia
from .comparador import DatosOferta, DatosCandidato, comparar_oferta_ia
from .generador_busqueda_empleo import (
    DatosBusqueda,
    ContextoBusqueda,
    generar_busqueda_empleo_ia,
)
from .optimizador_linkedin import DatosLinkedIn, DatosContexto, optimizar_linkedin_ia
from .evaluador_entrevista import (
    ContextoEntrevista,
    RespuestaEntrevista,
    generar_preguntas_ia,
    evaluar_entrevista_ia,
)


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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_oferta(request):
    serializer = OfertaCreateSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    datos = serializer.validated_data
    perfil, _ = PerfilProfesional.objects.get_or_create(usuario=request.user)
    cv = Curriculum.objects.filter(usuario=request.user).first()

    datos_oferta = DatosOferta(
        habilidades=datos.get('habilidades', ''),
        experiencia_requerida=datos.get('experiencia_requerida', ''),
        estudios_requeridos=datos.get('estudios_requeridos', ''),
        descripcion=datos['descripcion'],
        requisitos=datos.get('requisitos', ''),
    )
    datos_candidato = DatosCandidato(
        habilidades=perfil.habilidades,
        experiencia=perfil.experiencia,
        estudios=perfil.estudios,
        texto_cv=cv.texto_extraido if cv else '',
    )

    resultado = comparar_oferta_ia(datos_oferta, datos_candidato)

    oferta = Oferta.objects.create(
        usuario=request.user,
        titulo_puesto=datos['titulo_puesto'],
        empresa=datos['empresa'],
        ubicacion=datos.get('ubicacion', ''),
        descripcion=datos['descripcion'],
        requisitos=datos.get('requisitos', ''),
        habilidades=datos.get('habilidades', ''),
        estudios_requeridos=datos.get('estudios_requeridos', ''),
        experiencia_requerida=datos.get('experiencia_requerida', ''),
        habilidades_coincidentes=resultado["habilidades_coincidentes"],
        habilidades_faltantes=resultado["habilidades_faltantes"],
        palabras_clave_coincidentes=resultado["palabras_clave_coincidentes"],
        experiencia_compatible=resultado["experiencia_compatible"],
        estudios_compatibles=resultado["estudios_compatibles"],
        porcentaje_match=resultado["porcentaje_match"],
        clasificacion=resultado["clasificacion"],
        recomendaciones=resultado["recomendaciones"],
    )

    return Response(OfertaSerializer(oferta).data, status=201)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def historial_ofertas(request):
    ofertas = Oferta.objects.filter(usuario=request.user)
    serializer = OfertaSerializer(ofertas, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generar_busqueda_empleo(request):
    serializer = BusquedaEmpleoInputSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    datos_validados = serializer.validated_data

    # El perfil y el CV son siempre los del usuario autenticado; el
    # payload del cliente nunca puede indicar ni sobrescribir el usuario.
    perfil, _ = PerfilProfesional.objects.get_or_create(usuario=request.user)
    cv = Curriculum.objects.filter(usuario=request.user).first()

    datos_busqueda = DatosBusqueda(
        puesto_objetivo=datos_validados.get('puesto_objetivo', ''),
        ubicacion=datos_validados.get('ubicacion', ''),
        modalidad=datos_validados.get('modalidad', 'cualquiera'),
    )
    contexto = ContextoBusqueda(
        perfil_experiencia=perfil.experiencia,
        perfil_estudios=perfil.estudios,
        perfil_habilidades=perfil.habilidades,
        texto_cv=cv.texto_extraido if cv else '',
    )

    resultado = generar_busqueda_empleo_ia(datos_busqueda, contexto)

    return Response(resultado)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_optimizacion_linkedin(request):
    serializer = OptimizacionLinkedInCreateSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    datos = serializer.validated_data
    perfil, _ = PerfilProfesional.objects.get_or_create(usuario=request.user)
    cv = Curriculum.objects.filter(usuario=request.user).first()

    datos_linkedin = DatosLinkedIn(
        titular_actual=datos.get('titular_actual', ''),
        extracto=datos['extracto'],
        experiencia=datos.get('experiencia', ''),
        estudios=datos.get('estudios', ''),
        habilidades=datos.get('habilidades', ''),
    )
    contexto = DatosContexto(
        perfil_experiencia=perfil.experiencia,
        perfil_estudios=perfil.estudios,
        perfil_habilidades=perfil.habilidades,
        texto_cv=cv.texto_extraido if cv else '',
    )

    resultado = optimizar_linkedin_ia(datos_linkedin, contexto)

    # El propietario del análisis es siempre el usuario autenticado; el
    # payload del cliente nunca puede indicar ni sobrescribir este campo.
    optimizacion = OptimizacionLinkedIn.objects.create(
        usuario=request.user,
        titular_actual=datos_linkedin.titular_actual,
        extracto=datos_linkedin.extracto,
        experiencia=datos_linkedin.experiencia,
        estudios=datos_linkedin.estudios,
        habilidades=datos_linkedin.habilidades,
        puntuacion=resultado["puntuacion"],
        clasificacion=resultado["clasificacion"],
        titular_optimizado=resultado["titular_optimizado"],
        fortalezas=resultado["fortalezas"],
        debilidades=resultado["debilidades"],
        plan_mejora=resultado["plan_mejora"],
    )

    return Response(OptimizacionLinkedInSerializer(optimizacion).data, status=201)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def historial_linkedin(request):
    optimizaciones = OptimizacionLinkedIn.objects.filter(usuario=request.user)
    serializer = OptimizacionLinkedInSerializer(optimizaciones, many=True)
    return Response(serializer.data)


def _construir_contexto_entrevista(usuario):
    """
    Reúne los datos reales más recientes del usuario (Perfil, CV, última
    oferta comparada y última optimización de LinkedIn) para adaptar las
    preguntas y valorar la coherencia de las respuestas. Se reutiliza tanto
    al iniciar como al finalizar la entrevista para no duplicar esta lógica.
    """
    perfil, _ = PerfilProfesional.objects.get_or_create(usuario=usuario)
    cv = Curriculum.objects.filter(usuario=usuario).first()
    oferta = Oferta.objects.filter(usuario=usuario).first()
    linkedin = OptimizacionLinkedIn.objects.filter(usuario=usuario).first()

    return ContextoEntrevista(
        perfil_nombre=perfil.nombre_completo,
        perfil_experiencia=perfil.experiencia,
        perfil_estudios=perfil.estudios,
        perfil_habilidades=perfil.habilidades,
        texto_cv=cv.texto_extraido if cv else '',
        oferta_titulo=oferta.titulo_puesto if oferta else '',
        oferta_empresa=oferta.empresa if oferta else '',
        oferta_habilidades=oferta.habilidades if oferta else '',
        linkedin_titular=linkedin.titular_actual if linkedin else '',
        linkedin_extracto=linkedin.extracto if linkedin else '',
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def iniciar_entrevista(request):
    contexto = _construir_contexto_entrevista(request.user)
    preguntas = generar_preguntas_ia(contexto)
    return Response({"preguntas": preguntas})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def finalizar_entrevista(request):
    serializer = FinalizarEntrevistaSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    respuestas_validadas = serializer.validated_data['respuestas']
    contexto = _construir_contexto_entrevista(request.user)

    respuestas_dominio = [
        RespuestaEntrevista(
            tipo=item['tipo'],
            pregunta=item['pregunta'],
            respuesta=item.get('respuesta', ''),
            orden=item['orden'],
        )
        for item in respuestas_validadas
    ]

    resultado = evaluar_entrevista_ia(respuestas_dominio, contexto)

    # El propietario de la simulación es siempre el usuario autenticado; el
    # payload del cliente nunca puede indicar ni sobrescribir este campo.
    simulacion = SimulacionEntrevista.objects.create(
        usuario=request.user,
        puntuacion=resultado["puntuacion"],
        clasificacion=resultado["clasificacion"],
        fortalezas=resultado["fortalezas"],
        aspectos_mejora=resultado["aspectos_mejora"],
        recomendaciones=resultado["recomendaciones"],
    )

    PreguntaRespuesta.objects.bulk_create([
        PreguntaRespuesta(
            simulacion=simulacion,
            tipo=item['tipo'],
            pregunta=item['pregunta'],
            respuesta=item.get('respuesta', ''),
            orden=item['orden'],
        )
        for item in respuestas_validadas
    ])

    return Response(SimulacionEntrevistaSerializer(simulacion).data, status=201)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def historial_entrevistas(request):
    simulaciones = SimulacionEntrevista.objects.filter(
        usuario=request.user
    ).prefetch_related('preguntas')
    serializer = SimulacionEntrevistaSerializer(simulaciones, many=True)
    return Response(serializer.data)