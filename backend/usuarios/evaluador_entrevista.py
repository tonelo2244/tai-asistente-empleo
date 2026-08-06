"""
Motor del simulador de entrevistas de trabajo: generación de preguntas y
evaluación de respuestas.

Todas las funciones de este módulo son Python puro (sin dependencias de
Django ni acceso a base de datos), igual que `utils.py`, `comparador.py` y
`optimizador_linkedin.py`, para que sean testeables de forma aislada y
fáciles de sustituir.

Puntos de sustitución para el Sprint 10: `generar_preguntas_ia()` y
`evaluar_entrevista_ia()` mantienen la firma y la forma del resultado; hoy
delegan en las reglas propias (`generar_preguntas()` y `evaluar_entrevista()`)
y en el futuro delegarán en una llamada a OpenAI sin que las vistas que las
usan tengan que cambiar.
"""
import os
from dataclasses import dataclass

from .comparador import clasificar_match, extraer_palabras_clave
from .utils import detectar_keywords

# Mismo mapa de nombres visibles que optimizador_linkedin.py; se mantiene
# aquí también para no acoplar este módulo a otro módulo de reglas más
# allá de las funciones puramente compartidas (detectar_keywords).
NOMBRES_VISIBLES = {
    'python': 'Python',
    'django': 'Django',
    'react': 'React',
    'typescript': 'TypeScript',
    'javascript': 'JavaScript',
    'html': 'HTML',
    'css': 'CSS',
    'sql': 'SQL',
    'postgresql': 'PostgreSQL',
    'docker': 'Docker',
    'git': 'Git',
}

VOCABULARIO_PROFESIONAL = {
    'equipo', 'proyecto', 'responsabilidad', 'liderazgo', 'objetivo', 'resultado',
    'comunicación', 'colaboración', 'iniciativa', 'aprendizaje', 'reto', 'desafío',
    'logro', 'eficiencia', 'calidad', 'cliente', 'estrategia', 'planificación',
    'organización', 'compromiso',
}

# Orden fijo de los tipos de pregunta (checklist del Sprint 8).
TIPOS_PREGUNTA_ORDEN = (
    'presentacion',
    'experiencia',
    'formacion',
    'habilidades',
    'fortalezas',
    'debilidades',
    'motivacion',
    'trabajo_equipo',
    'resolucion_problemas',
    'objetivos',
)

ETIQUETAS_TIPO = {
    'presentacion': 'tu presentación personal',
    'experiencia': 'tu experiencia profesional',
    'formacion': 'tu formación académica',
    'habilidades': 'tus habilidades técnicas',
    'fortalezas': 'tus fortalezas',
    'debilidades': 'tus áreas de mejora',
    'motivacion': 'tu motivación',
    'trabajo_equipo': 'el trabajo en equipo',
    'resolucion_problemas': 'la resolución de problemas',
    'objetivos': 'tus objetivos profesionales',
}


def _nombre_visible(keyword):
    return NOMBRES_VISIBLES.get(keyword, keyword.capitalize())


@dataclass
class ContextoEntrevista:
    """Datos reales del usuario (Perfil, CV, Oferta y LinkedIn) usados para
    adaptar las preguntas y valorar la coherencia de las respuestas."""
    perfil_nombre: str = ''
    perfil_experiencia: str = ''
    perfil_estudios: str = ''
    perfil_habilidades: str = ''
    texto_cv: str = ''
    oferta_titulo: str = ''
    oferta_empresa: str = ''
    oferta_habilidades: str = ''
    linkedin_titular: str = ''
    linkedin_extracto: str = ''


@dataclass
class RespuestaEntrevista:
    """Una pregunta ya respondida por el usuario, lista para evaluar."""
    tipo: str
    pregunta: str
    respuesta: str = ''
    orden: int = 0


# -----------------------------
# Generación de preguntas
# -----------------------------

def _pregunta_presentacion(contexto):
    if contexto.perfil_nombre.strip():
        nombre = contexto.perfil_nombre.strip().split()[0]
        return f"Hola {nombre}, para empezar: preséntate brevemente y cuéntame qué te trae a esta entrevista."
    return "Para empezar: preséntate brevemente y cuéntame qué te trae a esta entrevista."


def _pregunta_experiencia(contexto):
    if contexto.perfil_experiencia.strip() or contexto.texto_cv.strip():
        return "Háblame de tu experiencia profesional. ¿Cuál dirías que ha sido tu logro más relevante?"
    return "¿Qué experiencia profesional, prácticas o proyectos personales puedes aportar a este puesto?"


def _pregunta_formacion(contexto):
    if contexto.perfil_estudios.strip():
        return "Cuéntame sobre tu formación académica y cómo te ha preparado para este puesto."
    return "¿Qué formación académica tienes y cómo te ha preparado para este puesto?"


def _pregunta_habilidades(contexto):
    texto = " ".join(filter(None, [contexto.perfil_habilidades, contexto.texto_cv]))
    keywords = detectar_keywords(texto)
    if keywords:
        visibles = ', '.join(_nombre_visible(k) for k in keywords[:3])
        return f"Veo que dominas {visibles}. ¿Puedes darme un ejemplo de cómo las has aplicado en un proyecto real?"
    return "¿Cuáles son tus principales habilidades técnicas y cómo las has aplicado en la práctica?"


def _pregunta_fortalezas(contexto):
    return "¿Cuáles consideras que son tus principales fortalezas como profesional?"


def _pregunta_debilidades(contexto):
    return "¿Cuál consideras que es tu principal área de mejora y qué estás haciendo al respecto?"


def _pregunta_motivacion(contexto):
    if contexto.oferta_empresa.strip():
        puesto = contexto.oferta_titulo.strip() or "este puesto"
        return f"¿Por qué te interesa trabajar en {contexto.oferta_empresa.strip()} como {puesto}?"
    return "¿Qué te motiva a buscar un nuevo reto profesional?"


def _pregunta_trabajo_equipo(contexto):
    return "Cuéntame una situación en la que hayas trabajado en equipo y cuál fue tu contribución."


def _pregunta_resolucion_problemas(contexto):
    return "Describe un problema complejo al que te hayas enfrentado profesionalmente y cómo lo resolviste."


def _pregunta_objetivos(contexto):
    if contexto.linkedin_titular.strip():
        return (
            f"Tu titular profesional actual es \"{contexto.linkedin_titular.strip()}\". "
            "¿Dónde te ves profesionalmente dentro de 3-5 años?"
        )
    return "¿Cuáles son tus objetivos profesionales a corto y medio plazo?"


_GENERADORES_PREGUNTA = {
    'presentacion': _pregunta_presentacion,
    'experiencia': _pregunta_experiencia,
    'formacion': _pregunta_formacion,
    'habilidades': _pregunta_habilidades,
    'fortalezas': _pregunta_fortalezas,
    'debilidades': _pregunta_debilidades,
    'motivacion': _pregunta_motivacion,
    'trabajo_equipo': _pregunta_trabajo_equipo,
    'resolucion_problemas': _pregunta_resolucion_problemas,
    'objetivos': _pregunta_objetivos,
}


def generar_preguntas(contexto: ContextoEntrevista) -> list:
    """
    Genera las preguntas de la entrevista mediante reglas, adaptando su
    redacción a la información real disponible del usuario (Perfil, CV,
    Oferta comparada y LinkedIn). Nunca inventa datos: si no hay contexto
    disponible para un tipo de pregunta, se usa una versión genérica.
    """
    return [
        {
            "orden": indice + 1,
            "tipo": tipo,
            "pregunta": _GENERADORES_PREGUNTA[tipo](contexto),
        }
        for indice, tipo in enumerate(TIPOS_PREGUNTA_ORDEN)
    ]


def generar_preguntas_ia(contexto: ContextoEntrevista) -> list:
    """
    Punto de entrada principal de la generación de preguntas.
    De momento usa reglas propias (generar_preguntas). En el Sprint 10
    podrá delegar en OpenAI si existe OPENAI_API_KEY, manteniendo la misma
    firma y forma de resultado.
    """
    openai_key = os.environ.get("OPENAI_API_KEY", "")

    if openai_key:
        # Futura integración con OpenAI (Sprint 10).
        pass

    return generar_preguntas(contexto)


# -----------------------------
# Evaluación de respuestas
# -----------------------------

def _evaluar_longitud(respuesta):
    """(puntos_0_a_30, estado) — estado in {'vacia', 'corta', 'larga', 'adecuada'}."""
    palabras = len((respuesta or '').strip().split())

    if palabras == 0:
        return 0, 'vacia'
    if palabras < 15:
        return 10, 'corta'
    if palabras > 250:
        return 18, 'larga'
    return 30, 'adecuada'


def _evaluar_claridad(respuesta):
    """
    Heurística simple de claridad: una respuesta larga sin ningún signo de
    puntuación de cierre de frase se considera poco estructurada.
    """
    texto = (respuesta or '').strip()
    if not texto:
        return None

    palabras = len(texto.split())
    tiene_puntuacion = any(signo in texto for signo in ('.', '!', '?'))

    return not (palabras > 20 and not tiene_puntuacion)


def _evaluar_vocabulario_profesional(respuesta):
    """(puntos_0_a_25, palabras_encontradas)."""
    texto = (respuesta or '').lower()
    encontradas = sorted(p for p in VOCABULARIO_PROFESIONAL if p in texto)

    if len(encontradas) >= 3:
        return 25, encontradas
    if encontradas:
        return 12, encontradas
    return 0, encontradas


def _evaluar_palabras_clave_tecnicas(respuesta, texto_contexto):
    """(puntos_0_a_25, keywords_coincidentes) — tecnologías mencionadas que
    coinciden con el contexto real del usuario (Perfil, CV y Oferta)."""
    keywords_respuesta = set(detectar_keywords(respuesta))
    keywords_contexto = set(detectar_keywords(texto_contexto))
    coincidentes = sorted(keywords_respuesta & keywords_contexto)

    return (25 if coincidentes else 0), coincidentes


def evaluar_respuesta(respuesta: str, texto_contexto_tecnico: str) -> dict:
    """
    Evalúa una única respuesta: longitud, claridad, vocabulario profesional
    y palabras clave técnicas coincidentes con el contexto real del usuario.
    Puntuación máxima por respuesta: 100 (30 + 20 + 25 + 25).
    """
    puntos_longitud, estado_longitud = _evaluar_longitud(respuesta)
    es_clara = _evaluar_claridad(respuesta)
    puntos_vocabulario, vocabulario_encontrado = _evaluar_vocabulario_profesional(respuesta)
    puntos_keywords, keywords_coincidentes = _evaluar_palabras_clave_tecnicas(
        respuesta, texto_contexto_tecnico
    )

    puntos_claridad = 20 if es_clara else 0
    puntuacion = puntos_longitud + puntos_claridad + puntos_vocabulario + puntos_keywords

    return {
        "puntuacion": puntuacion,
        "estado_longitud": estado_longitud,
        "es_clara": es_clara,
        "vocabulario_profesional": vocabulario_encontrado,
        "palabras_clave_tecnicas": keywords_coincidentes,
    }


def _evaluar_coherencia_global(texto_respuestas, contexto: ContextoEntrevista):
    """
    Coherencia del conjunto de respuestas con las cuatro fuentes de datos
    reales del usuario. Si una fuente no existe (p. ej. no ha subido CV o
    no ha comparado ninguna oferta), no se penaliza: se otorga el crédito
    completo de esa fuente, igual que en comparador.py y optimizador_linkedin.py.
    """
    fortalezas, recomendaciones = [], []
    puntos = 0
    palabras_respuestas = extraer_palabras_clave(texto_respuestas)

    fuentes = (
        ("tu Perfil Profesional", " ".join(filter(None, [
            contexto.perfil_experiencia, contexto.perfil_estudios, contexto.perfil_habilidades,
        ]))),
        ("tu CV analizado", contexto.texto_cv),
        ("la oferta de empleo comparada", " ".join(filter(None, [
            contexto.oferta_titulo, contexto.oferta_habilidades,
        ]))),
        ("tu perfil de LinkedIn", " ".join(filter(None, [
            contexto.linkedin_titular, contexto.linkedin_extracto,
        ]))),
    )

    for nombre_fuente, texto_fuente in fuentes:
        if not texto_fuente.strip():
            puntos += 25
            continue

        if palabras_respuestas & extraer_palabras_clave(texto_fuente):
            puntos += 25
            fortalezas.append(f"Tus respuestas son coherentes con {nombre_fuente}.")
        else:
            recomendaciones.append(
                f"Intenta relacionar tus respuestas con la información de {nombre_fuente}."
            )

    return puntos, fortalezas, recomendaciones


def evaluar_entrevista(respuestas: list, contexto: ContextoEntrevista) -> dict:
    """
    Reglas de evaluación (sin IA) de una simulación completa. Devuelve el
    mismo formato que usará `evaluar_entrevista_ia()` cuando en el Sprint 10
    se sustituya por OpenAI. Resultado determinista: sin aleatoriedad.
    """
    fortalezas, aspectos_mejora, recomendaciones = [], [], []
    puntuaciones = []

    texto_contexto_tecnico = " ".join(filter(None, [
        contexto.perfil_habilidades, contexto.texto_cv, contexto.oferta_habilidades,
    ]))

    for item in respuestas:
        resultado = evaluar_respuesta(item.respuesta, texto_contexto_tecnico)
        puntuaciones.append(resultado["puntuacion"])
        etiqueta = ETIQUETAS_TIPO.get(item.tipo, item.tipo)

        if resultado["estado_longitud"] == 'vacia':
            aspectos_mejora.append(f"No has respondido a la pregunta sobre {etiqueta}.")
            recomendaciones.append(f"Responde a la pregunta sobre {etiqueta} antes de finalizar la entrevista.")
            continue

        if resultado["estado_longitud"] == 'corta':
            aspectos_mejora.append(f"Tu respuesta sobre {etiqueta} es demasiado breve.")
            recomendaciones.append(f"Desarrolla más tu respuesta sobre {etiqueta} con ejemplos concretos.")
        elif resultado["estado_longitud"] == 'larga':
            aspectos_mejora.append(f"Tu respuesta sobre {etiqueta} es excesivamente larga.")
            recomendaciones.append(f"Sintetiza tu respuesta sobre {etiqueta}: ve directo a lo esencial.")
        else:
            fortalezas.append(f"Tu respuesta sobre {etiqueta} tiene una longitud adecuada.")

        if resultado["es_clara"] is False:
            aspectos_mejora.append(f"Tu respuesta sobre {etiqueta} carece de una estructura clara.")
            recomendaciones.append(f"Organiza tu respuesta sobre {etiqueta} en frases cortas y bien puntuadas.")

        if resultado["vocabulario_profesional"]:
            fortalezas.append(f"Usas vocabulario profesional en tu respuesta sobre {etiqueta}.")
        else:
            recomendaciones.append(f"Incluye vocabulario más profesional en tu respuesta sobre {etiqueta}.")

    puntuacion_respuestas = round(sum(puntuaciones) / len(puntuaciones)) if puntuaciones else 0

    texto_todas_respuestas = " ".join(filter(None, (item.respuesta for item in respuestas)))
    puntuacion_coherencia, f_coherencia, r_coherencia = _evaluar_coherencia_global(
        texto_todas_respuestas, contexto
    )
    fortalezas += f_coherencia
    recomendaciones += r_coherencia

    puntuacion = round(0.7 * puntuacion_respuestas + 0.3 * puntuacion_coherencia)
    puntuacion = max(0, min(100, puntuacion))

    return {
        "puntuacion": puntuacion,
        "clasificacion": clasificar_match(puntuacion),
        "fortalezas": fortalezas,
        "aspectos_mejora": aspectos_mejora,
        "recomendaciones": recomendaciones,
    }


def evaluar_entrevista_ia(respuestas: list, contexto: ContextoEntrevista) -> dict:
    """
    Punto de entrada principal de la evaluación de la entrevista.
    De momento usa reglas propias (evaluar_entrevista), misma arquitectura
    que analizar_perfil_ia(), analizar_cv_ia(), comparar_oferta_ia() y
    optimizar_linkedin_ia(). En el Sprint 10 esta función podrá delegar en
    OpenAI, manteniendo exactamente la misma firma y forma de resultado.
    """
    return evaluar_entrevista(respuestas, contexto)
