"""
Motor de comparación entre el candidato (perfil profesional + CV) y una
oferta de empleo.

Todas las funciones de este módulo son Python puro (sin dependencias de
Django ni acceso a base de datos), igual que `utils.py`, para que sean
testeables de forma aislada y fáciles de sustituir.

Punto de sustitución para el Sprint 10: `comparar_oferta_ia()` mantiene la
firma y la forma del resultado; hoy delega en `comparar_oferta()` (reglas
propias) y en el futuro delegará en una llamada a OpenAI sin que las vistas
que la usan tengan que cambiar.
"""
import os
import re
from dataclasses import dataclass

from .utils import detectar_keywords

STOPWORDS_ES = {
    'de', 'la', 'el', 'en', 'y', 'a', 'los', 'las', 'un', 'una', 'que',
    'para', 'con', 'se', 'su', 'sus', 'del', 'al', 'por', 'como', 'es',
    'son', 'o', 'u', 'le', 'les', 'lo', 'este', 'esta', 'estos', 'estas',
    'nuestro', 'nuestra', 'sobre', 'entre', 'sin', 'más', 'muy', 'ser',
    'tiene', 'tener', 'debe', 'puede',
}

# Umbrales de clasificación cualitativa a partir del porcentaje (0-100)
CLASIFICACIONES = (
    (90, "Excelente"),
    (75, "Muy buena"),
    (55, "Buena"),
    (35, "Mejorable"),
    (0, "Insuficiente"),
)


@dataclass
class DatosOferta:
    """Datos de la oferta de empleo relevantes para la comparación."""
    habilidades: str = ''
    experiencia_requerida: str = ''
    estudios_requeridos: str = ''
    descripcion: str = ''
    requisitos: str = ''


@dataclass
class DatosCandidato:
    """Datos del candidato (perfil profesional + CV) para la comparación."""
    habilidades: str = ''
    experiencia: str = ''
    estudios: str = ''
    texto_cv: str = ''


def extraer_palabras_clave(texto, longitud_minima=4):
    """Conjunto de palabras significativas de un texto (sin stopwords)."""
    if not texto:
        return set()

    palabras = re.findall(r'[a-záéíóúüñ]+', texto.lower())
    return {p for p in palabras if len(p) >= longitud_minima and p not in STOPWORDS_ES}


def extraer_primer_numero(texto):
    """Primer número entero encontrado en el texto (p. ej. años de experiencia)."""
    if not texto:
        return None

    coincidencia = re.search(r'\d+', texto)
    return int(coincidencia.group()) if coincidencia else None


def comparar_habilidades(habilidades_oferta, texto_candidato):
    """
    Compara las tecnologías detectadas en la oferta frente a las del candidato.
    Devuelve (coincidentes, faltantes), ambas listas ordenadas.
    """
    requeridas = set(detectar_keywords(habilidades_oferta))
    disponibles = set(detectar_keywords(texto_candidato))

    coincidentes = sorted(requeridas & disponibles)
    faltantes = sorted(requeridas - disponibles)

    return coincidentes, faltantes


def comparar_palabras_clave(texto_oferta, texto_candidato):
    """Palabras significativas presentes tanto en la oferta como en el candidato."""
    palabras_oferta = extraer_palabras_clave(texto_oferta)
    palabras_candidato = extraer_palabras_clave(texto_candidato)
    return sorted(palabras_oferta & palabras_candidato)


def evaluar_experiencia(experiencia_requerida, experiencia_candidato):
    """
    Compatibilidad de experiencia. Si tanto la oferta como el candidato
    expresan una cifra (años), se comparan directamente; si no se puede
    extraer un número, se considera compatible cuando el candidato aporta
    contenido de experiencia sustancial.
    """
    requerida = (experiencia_requerida or '').strip()
    candidato = (experiencia_candidato or '').strip()

    if not requerida:
        return True

    if not candidato:
        return False

    anios_requeridos = extraer_primer_numero(requerida)
    anios_candidato = extraer_primer_numero(candidato)

    if anios_requeridos is not None and anios_candidato is not None:
        return anios_candidato >= anios_requeridos

    return len(candidato) >= 100


def evaluar_estudios(estudios_requeridos, estudios_candidato):
    """Compatibilidad de formación académica por solapamiento de palabras clave."""
    requeridos = (estudios_requeridos or '').strip()
    candidato = (estudios_candidato or '').strip()

    if not requeridos:
        return True

    if not candidato:
        return False

    return bool(extraer_palabras_clave(requeridos) & extraer_palabras_clave(candidato))


def calcular_porcentaje_match(
    habilidades_coincidentes,
    habilidades_faltantes,
    experiencia_compatible,
    estudios_compatibles,
    palabras_clave_coincidentes,
):
    """
    Puntuación objetiva 0-100 a partir de señales de compatibilidad.
    Reparto de peso: habilidades 40, experiencia 25, estudios 20, palabras clave 15.
    """
    total_habilidades = len(habilidades_coincidentes) + len(habilidades_faltantes)

    if total_habilidades > 0:
        puntos_habilidades = 40 * (len(habilidades_coincidentes) / total_habilidades)
    else:
        puntos_habilidades = 40

    puntos_experiencia = 25 if experiencia_compatible else 0
    puntos_estudios = 20 if estudios_compatibles else 0
    puntos_palabras_clave = min(len(palabras_clave_coincidentes), 5) / 5 * 15

    total = puntos_habilidades + puntos_experiencia + puntos_estudios + puntos_palabras_clave
    return max(0, min(100, round(total)))


def clasificar_match(porcentaje):
    """Etiqueta cualitativa a partir del porcentaje de compatibilidad."""
    for minimo, etiqueta in CLASIFICACIONES:
        if porcentaje >= minimo:
            return etiqueta
    return CLASIFICACIONES[-1][1]


def generar_recomendaciones(
    habilidades_faltantes,
    experiencia_compatible,
    estudios_compatibles,
    palabras_clave_coincidentes,
    tiene_cv,
):
    """Sugerencias accionables a partir de las brechas detectadas."""
    recomendaciones = []

    for habilidad in habilidades_faltantes:
        recomendaciones.append(f"Aprender {habilidad}.")

    if not experiencia_compatible:
        recomendaciones.append(
            "Añade o detalla experiencia relacionada con los requisitos de la oferta."
        )

    if not estudios_compatibles:
        recomendaciones.append(
            "Añade formación académica relacionada con los requisitos de la oferta."
        )

    if len(palabras_clave_coincidentes) < 3:
        recomendaciones.append(
            "Adapta el vocabulario de tu perfil y tu CV a los términos de la oferta."
        )

    if not tiene_cv:
        recomendaciones.append("Sube tu CV para obtener una comparación más precisa.")

    return recomendaciones


def comparar_oferta(oferta: DatosOferta, candidato: DatosCandidato) -> dict:
    """
    Reglas de comparación (sin IA). Devuelve el mismo formato que usará
    `comparar_oferta_ia()` cuando en el Sprint 10 se sustituya por OpenAI.
    """
    texto_candidato_completo = " ".join(filter(None, [
        candidato.habilidades, candidato.experiencia, candidato.estudios, candidato.texto_cv,
    ]))
    texto_oferta_completo = " ".join(filter(None, [
        oferta.descripcion, oferta.requisitos, oferta.habilidades,
    ]))

    habilidades_coincidentes, habilidades_faltantes = comparar_habilidades(
        oferta.habilidades, texto_candidato_completo
    )
    palabras_clave_coincidentes = comparar_palabras_clave(
        texto_oferta_completo, texto_candidato_completo
    )
    experiencia_compatible = evaluar_experiencia(
        oferta.experiencia_requerida,
        f"{candidato.experiencia} {candidato.texto_cv}".strip(),
    )
    estudios_compatibles = evaluar_estudios(oferta.estudios_requeridos, candidato.estudios)

    porcentaje = calcular_porcentaje_match(
        habilidades_coincidentes,
        habilidades_faltantes,
        experiencia_compatible,
        estudios_compatibles,
        palabras_clave_coincidentes,
    )

    recomendaciones = generar_recomendaciones(
        habilidades_faltantes,
        experiencia_compatible,
        estudios_compatibles,
        palabras_clave_coincidentes,
        tiene_cv=bool(candidato.texto_cv.strip()),
    )

    return {
        "habilidades_coincidentes": habilidades_coincidentes,
        "habilidades_faltantes": habilidades_faltantes,
        "palabras_clave_coincidentes": palabras_clave_coincidentes,
        "experiencia_compatible": experiencia_compatible,
        "estudios_compatibles": estudios_compatibles,
        "porcentaje_match": porcentaje,
        "clasificacion": clasificar_match(porcentaje),
        "recomendaciones": recomendaciones,
    }


def comparar_oferta_ia(oferta: DatosOferta, candidato: DatosCandidato) -> dict:
    """
    Punto de entrada principal de la comparación.
    De momento usa reglas propias (comparar_oferta), misma arquitectura
    que analizar_perfil_ia() y analizar_cv_ia(). En el Sprint 10 esta
    función delegará en OpenAI si existe OPENAI_API_KEY, manteniendo
    exactamente la misma firma y forma de resultado.
    """
    openai_key = os.environ.get("OPENAI_API_KEY", "")

    if openai_key:
        # Futura integración con OpenAI (Sprint 10).
        pass

    return comparar_oferta(oferta, candidato)
