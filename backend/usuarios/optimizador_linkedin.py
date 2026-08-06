"""
Motor de optimización del perfil profesional de LinkedIn.

Todas las funciones de este módulo son Python puro (sin dependencias de
Django ni acceso a base de datos), igual que `utils.py` y `comparador.py`,
para que sean testeables de forma aislada y fáciles de sustituir.

Punto de sustitución para el Sprint 10: `optimizar_linkedin_ia()` mantiene
la firma y la forma del resultado; hoy delega en `optimizar_linkedin()`
(reglas propias) y en el futuro delegará en una llamada a OpenAI sin que
las vistas que la usan tengan que cambiar.

No inventa experiencia, tecnologías ni certificaciones: el titular
optimizado y las recomendaciones se construyen únicamente a partir de los
datos reales proporcionados por el usuario.
"""
from dataclasses import dataclass

from . import openai_service
from .comparador import clasificar_match, extraer_palabras_clave
from .utils import detectar_keywords

# Nombres de tecnología con el casing real de la marca (Python capitalize()
# convertiría "typescript" en "Typescript" en lugar de "TypeScript").
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

# Categorías de especialización inferidas a partir de las tecnologías
# realmente detectadas (nunca se inventan tecnologías no presentes).
CATEGORIAS_TECNOLOGIA = {
    'backend': {'python', 'django', 'sql', 'postgresql'},
    'frontend': {'react', 'typescript', 'javascript', 'html', 'css'},
    'devops': {'docker', 'git'},
}


@dataclass
class DatosLinkedIn:
    """Datos del perfil de LinkedIn introducidos por el usuario."""
    titular_actual: str = ''
    extracto: str = ''
    experiencia: str = ''
    estudios: str = ''
    habilidades: str = ''


@dataclass
class DatosContexto:
    """Datos de contexto del usuario en TAI (perfil profesional + CV) para valorar coherencia."""
    perfil_experiencia: str = ''
    perfil_estudios: str = ''
    perfil_habilidades: str = ''
    texto_cv: str = ''


def _nombre_visible(keyword):
    return NOMBRES_VISIBLES.get(keyword, keyword.capitalize())


def _inferir_categoria(keywords):
    """Etiqueta de especialización a partir de las tecnologías detectadas."""
    detectadas = set(keywords)
    tiene_backend = bool(detectadas & CATEGORIAS_TECNOLOGIA['backend'])
    tiene_frontend = bool(detectadas & CATEGORIAS_TECNOLOGIA['frontend'])
    tiene_devops = bool(detectadas & CATEGORIAS_TECNOLOGIA['devops'])

    if tiene_backend and tiene_frontend:
        return 'Desarrollo Web'
    if tiene_backend:
        return 'Desarrollo Backend'
    if tiene_frontend:
        return 'Desarrollo Frontend'
    if tiene_devops:
        return 'DevOps'
    return ''


def evaluar_titular(titular_actual, texto_tecnologico):
    """Calidad del titular: longitud adecuada y presencia de tecnologías reconocibles."""
    fortalezas, debilidades, recomendaciones = [], [], []

    titular = (titular_actual or '').strip()

    if not titular:
        debilidades.append("No has definido un titular profesional en tu perfil de LinkedIn.")
        recomendaciones.append("Añade un titular profesional claro y específico.")
        return 0, fortalezas, debilidades, recomendaciones

    puntos = 0

    if 10 <= len(titular) <= 220:
        puntos += 8
        fortalezas.append("El titular tiene una longitud adecuada.")
    else:
        debilidades.append("El titular actual es demasiado breve o supera la longitud recomendada.")
        recomendaciones.append("Ajusta la longitud de tu titular para que sea claro y directo.")

    if detectar_keywords(titular):
        puntos += 7
        fortalezas.append("El titular incluye tecnologías reconocibles.")
    else:
        debilidades.append("El titular no incluye tecnologías o palabras clave reconocibles.")
        recomendaciones.append("Incluye tecnologías clave en tu titular para mejorar tu visibilidad.")

    return puntos, fortalezas, debilidades, recomendaciones


def evaluar_extracto(extracto):
    """Longitud del extracto ('Acerca de'): a mayor desarrollo, mayor puntuación."""
    fortalezas, debilidades, recomendaciones = [], [], []

    palabras = len((extracto or '').split())

    if palabras >= 150:
        fortalezas.append("El extracto (\"Acerca de\") tiene un desarrollo extenso y detallado.")
        return 20, fortalezas, debilidades, recomendaciones

    if palabras >= 60:
        fortalezas.append("El extracto tiene un desarrollo aceptable.")
        debilidades.append("El extracto podría ampliarse con más detalle.")
        recomendaciones.append("Amplía el extracto con más detalles de tu trayectoria y objetivos.")
        return 12, fortalezas, debilidades, recomendaciones

    debilidades.append("El extracto es demasiado breve para un perfil profesional atractivo.")
    recomendaciones.append("Amplía el extracto: quién eres, qué haces y qué buscas profesionalmente.")
    return 0, fortalezas, debilidades, recomendaciones


def evaluar_palabras_clave(texto_completo):
    """Presencia de palabras clave técnicas en el conjunto del perfil de LinkedIn."""
    fortalezas, debilidades, recomendaciones = [], [], []

    keywords = detectar_keywords(texto_completo)

    if len(keywords) >= 4:
        visibles = ', '.join(_nombre_visible(k) for k in keywords)
        fortalezas.append(f"Tu perfil incluye numerosas palabras clave relevantes: {visibles}.")
        return 15, fortalezas, debilidades, recomendaciones

    if keywords:
        visibles = ', '.join(_nombre_visible(k) for k in keywords)
        fortalezas.append(f"Tu perfil incluye algunas palabras clave relevantes: {visibles}.")
        debilidades.append("El perfil podría incluir más palabras clave técnicas.")
        recomendaciones.append("Mejora las palabras clave añadiendo más tecnologías relevantes para tu sector.")
        return 8, fortalezas, debilidades, recomendaciones

    debilidades.append("No se detectan palabras clave técnicas relevantes en tu perfil de LinkedIn.")
    recomendaciones.append("Mejora las palabras clave incluyendo tecnologías que mejoren tu visibilidad en búsquedas.")
    return 0, fortalezas, debilidades, recomendaciones


def evaluar_habilidades(habilidades):
    """Presencia de habilidades y de tecnologías reconocibles entre ellas."""
    fortalezas, debilidades, recomendaciones = [], [], []

    texto = (habilidades or '').strip()

    if not texto:
        debilidades.append("No has añadido habilidades a tu perfil de LinkedIn.")
        recomendaciones.append("Añade más habilidades técnicas y profesionales a tu perfil.")
        return 0, fortalezas, debilidades, recomendaciones

    if detectar_keywords(texto):
        fortalezas.append("Las habilidades incluyen tecnologías reconocibles.")
        return 15, fortalezas, debilidades, recomendaciones

    debilidades.append("Las habilidades no incluyen tecnologías o herramientas reconocibles.")
    recomendaciones.append("Añade más habilidades técnicas concretas, como lenguajes o herramientas.")
    return 5, fortalezas, debilidades, recomendaciones


def evaluar_experiencia(experiencia):
    """Presencia y detalle de la experiencia profesional."""
    fortalezas, debilidades, recomendaciones = [], [], []

    texto = (experiencia or '').strip()

    if not texto:
        debilidades.append("No has descrito experiencia profesional en tu perfil de LinkedIn.")
        recomendaciones.append("Completa tu experiencia: empresa, rol y logros concretos.")
        return 0, fortalezas, debilidades, recomendaciones

    if len(texto) >= 100:
        fortalezas.append("La experiencia está descrita con suficiente detalle.")
        return 15, fortalezas, debilidades, recomendaciones

    debilidades.append("La experiencia está descrita de forma muy breve.")
    recomendaciones.append("Completa tu experiencia con más detalle: empresa, rol y logros concretos.")
    return 7, fortalezas, debilidades, recomendaciones


def evaluar_estudios(estudios):
    """Presencia de formación académica."""
    fortalezas, debilidades, recomendaciones = [], [], []

    texto = (estudios or '').strip()

    if texto:
        fortalezas.append("Has incluido tu formación académica.")
        return 10, fortalezas, debilidades, recomendaciones

    debilidades.append("No has añadido formación académica a tu perfil de LinkedIn.")
    recomendaciones.append("Mejora tus estudios añadiendo tu formación académica.")
    return 0, fortalezas, debilidades, recomendaciones


def evaluar_coherencia_perfil(texto_linkedin, texto_perfil):
    """
    Coherencia con el Perfil Profesional de TAI. Si el usuario no tiene
    perfil profesional relleno, no hay nada que contrastar y no se penaliza.
    """
    if not (texto_perfil or '').strip():
        return 5, [], [], []

    coincidencias = extraer_palabras_clave(texto_linkedin) & extraer_palabras_clave(texto_perfil)

    if coincidencias:
        return 5, ["Tu perfil de LinkedIn es coherente con tu perfil profesional en TAI."], [], []

    debilidad = "Tu perfil de LinkedIn no coincide con la información de tu perfil profesional."
    recomendacion = "Revisa que tu perfil de LinkedIn refleje la misma información que tu perfil profesional."
    return 0, [], [debilidad], [recomendacion]


def evaluar_coherencia_cv(texto_linkedin, texto_cv):
    """
    Coherencia con el CV analizado. Si el usuario no ha subido ningún CV,
    no hay nada que contrastar y no se penaliza.
    """
    if not (texto_cv or '').strip():
        return 5, [], [], []

    coincidencias = extraer_palabras_clave(texto_linkedin) & extraer_palabras_clave(texto_cv)

    if coincidencias:
        return 5, ["Tu perfil de LinkedIn es coherente con tu CV analizado."], [], []

    debilidad = "Tu perfil de LinkedIn no coincide con el contenido de tu CV analizado."
    recomendacion = "Revisa que tu perfil de LinkedIn refleje la misma información que tu CV."
    return 0, [], [debilidad], [recomendacion]


def recomendaciones_adicionales(texto_completo):
    """
    Sugerencias generales que no dependen de una puntuación, basadas en la
    ausencia de menciones concretas (proyectos, certificaciones) en el texto.
    """
    recomendaciones = []
    texto = (texto_completo or '').lower()

    if not any(p in texto for p in ('proyecto', 'github', 'portfolio', 'portafolio')):
        recomendaciones.append(
            "Incluye proyectos personales o un enlace a GitHub para reforzar tu experiencia."
        )

    if not any(p in texto for p in ('certificaci', 'curso', 'bootcamp')):
        recomendaciones.append("Añade certificaciones o cursos relevantes para reforzar tu perfil.")

    return recomendaciones


def generar_titular_optimizado(datos: DatosLinkedIn, contexto: DatosContexto) -> str:
    """
    Construye un titular profesional optimizado a partir de datos reales:
    el titular actual del usuario (si existe) como base, las tecnologías
    detectadas en sus habilidades y una categoría de especialización
    inferida de esas mismas tecnologías. Nunca inventa roles, tecnologías
    ni certificaciones que no estén presentes en los datos de entrada.
    """
    texto_habilidades = " ".join(filter(None, [datos.habilidades, contexto.perfil_habilidades]))
    keywords = detectar_keywords(texto_habilidades)
    categoria = _inferir_categoria(keywords)
    base = (datos.titular_actual or '').strip()

    segmentos = []

    if base:
        segmentos.append(base)
    elif categoria:
        segmentos.append(categoria)

    if keywords:
        segmentos.append(" · ".join(_nombre_visible(k) for k in keywords[:5]))

    if categoria and base:
        segmentos.append(categoria)

    return " | ".join(segmentos)


def optimizar_linkedin(datos: DatosLinkedIn, contexto: DatosContexto) -> dict:
    """
    Reglas de optimización (sin IA). Devuelve el mismo formato que usará
    `optimizar_linkedin_ia()` cuando en el Sprint 10 se sustituya por OpenAI.
    """
    texto_linkedin_completo = " ".join(filter(None, [
        datos.titular_actual, datos.extracto, datos.experiencia, datos.habilidades,
    ]))
    texto_perfil = " ".join(filter(None, [
        contexto.perfil_experiencia, contexto.perfil_estudios, contexto.perfil_habilidades,
    ]))

    evaluaciones = [
        evaluar_titular(datos.titular_actual, " ".join(filter(None, [datos.habilidades, datos.experiencia]))),
        evaluar_extracto(datos.extracto),
        evaluar_palabras_clave(texto_linkedin_completo),
        evaluar_habilidades(datos.habilidades),
        evaluar_experiencia(datos.experiencia),
        evaluar_estudios(datos.estudios),
        evaluar_coherencia_perfil(texto_linkedin_completo, texto_perfil),
        evaluar_coherencia_cv(texto_linkedin_completo, contexto.texto_cv),
    ]

    puntuacion = 0
    fortalezas, debilidades, plan_mejora = [], [], []

    for puntos, f, d, r in evaluaciones:
        puntuacion += puntos
        fortalezas += f
        debilidades += d
        plan_mejora += r

    plan_mejora += recomendaciones_adicionales(texto_linkedin_completo)

    puntuacion = max(0, min(100, puntuacion))

    return {
        "puntuacion": puntuacion,
        "clasificacion": clasificar_match(puntuacion),
        "titular_optimizado": generar_titular_optimizado(datos, contexto),
        "fortalezas": fortalezas,
        "debilidades": debilidades,
        "plan_mejora": plan_mejora,
    }


def optimizar_linkedin_ia(datos: DatosLinkedIn, contexto: DatosContexto) -> dict:
    """
    Punto de entrada principal de la optimización de LinkedIn. El motor de
    reglas (optimizar_linkedin) se calcula siempre: la puntuación y la
    clasificación son siempre las calculadas por reglas. Si hay una clave
    de OpenAI configurada y la llamada tiene éxito, se sustituyen el
    titular optimizado, las fortalezas, las debilidades y el plan de
    mejora por los generados por IA a partir de los mismos datos reales.
    """
    resultado = optimizar_linkedin(datos, contexto)

    resultado_ia = openai_service.optimizar_linkedin(datos, contexto, resultado)
    if resultado_ia is not None:
        resultado.update(resultado_ia)

    return resultado
