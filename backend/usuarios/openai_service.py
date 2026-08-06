"""
Servicio centralizado de comunicación con OpenAI (Sprint 9).

Este es el ÚNICO módulo de la aplicación que importa el SDK de OpenAI o
realiza llamadas de red hacia su API. Ninguna vista, serializer ni modelo
llama a OpenAI directamente: siempre pasan por las funciones públicas de
este archivo.

Cada función pública (`analizar_perfil`, `analizar_cv`, `comparar_oferta`,
`optimizar_linkedin`, `evaluar_entrevista`) corresponde a uno de los motores
de reglas existentes (`utils.py`, `comparador.py`, `optimizador_linkedin.py`,
`evaluador_entrevista.py`) y:

- Devuelve un dict con el contenido cualitativo generado por IA si
  `OPENAI_API_KEY` está configurada y la llamada tiene éxito.
- Devuelve `None` ante cualquier problema: clave ausente, error de
  autenticación, límite de uso, error de conexión, timeout, excepción
  inesperada del SDK o respuesta con formato inválido. Nunca lanza
  excepciones hacia quien la llama.

Los módulos de reglas (`utils.py`, `comparador.py`, etc.) son responsables
de usar este resultado como sustituto opcional y de recurrir al motor de
reglas cuando el resultado es `None`. Ese es el único punto de decisión
IA/reglas, tal y como exige la arquitectura del Sprint 9.
"""
import json
import logging
import os

from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)

from . import openai_prompts as prompts

logger = logging.getLogger(__name__)

MODELO_POR_DEFECTO = "gpt-4o-mini"
TIMEOUT_SEGUNDOS = 20.0


def openai_disponible():
    """True si hay una API key de OpenAI configurada (no vacía)."""
    return bool(os.environ.get("OPENAI_API_KEY", "").strip())


def _cliente():
    return OpenAI(api_key=os.environ["OPENAI_API_KEY"])


def _modelo():
    return os.environ.get("OPENAI_MODEL", "").strip() or MODELO_POR_DEFECTO


def _completar_json(system_prompt, user_prompt, claves_esperadas):
    """
    Llama a OpenAI pidiendo una respuesta en formato JSON y devuelve el
    dict ya parseado, o None si ocurre cualquier error o la respuesta no
    contiene las claves esperadas. Esta función nunca propaga excepciones:
    cualquier fallo se registra en el log (sin incluir la API key) y se
    traduce en un None, que el llamante interpreta como "usar reglas".
    """
    if not openai_disponible():
        return None

    try:
        respuesta = _cliente().chat.completions.create(
            model=_modelo(),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.4,
            timeout=TIMEOUT_SEGUNDOS,
        )
        contenido = respuesta.choices[0].message.content
        datos = json.loads(contenido)
    except AuthenticationError:
        logger.warning("OpenAI: clave de API inválida o rechazada. Se usa el motor de reglas.")
        return None
    except RateLimitError:
        logger.warning("OpenAI: límite de uso alcanzado. Se usa el motor de reglas.")
        return None
    except APITimeoutError:
        logger.warning("OpenAI: tiempo de espera agotado. Se usa el motor de reglas.")
        return None
    except APIConnectionError:
        logger.warning("OpenAI: error de conexión con la API. Se usa el motor de reglas.")
        return None
    except (json.JSONDecodeError, ValueError, TypeError, IndexError, AttributeError):
        logger.warning("OpenAI: respuesta con formato inesperado. Se usa el motor de reglas.")
        return None
    except Exception:
        logger.exception("OpenAI: error inesperado en la llamada a la API. Se usa el motor de reglas.")
        return None

    if not isinstance(datos, dict) or not claves_esperadas.issubset(datos.keys()):
        logger.warning("OpenAI: la respuesta no contiene las claves esperadas. Se usa el motor de reglas.")
        return None

    return datos


def _es_lista_de_str(valor):
    return isinstance(valor, list) and all(isinstance(item, str) for item in valor)


def _validar(datos, campos_texto=(), campos_lista=()):
    """True si `datos` tiene los tipos esperados: str en campos_texto y
    list[str] en campos_lista. Cualquier desviación se considera una
    respuesta inválida (se registra y se descarta, nunca se usa a medias)."""
    for campo in campos_texto:
        if not isinstance(datos.get(campo), str) or not datos[campo].strip():
            return False
    for campo in campos_lista:
        if not _es_lista_de_str(datos.get(campo)):
            return False
    return True


def analizar_perfil(perfil, resultado_reglas):
    """Análisis cualitativo del perfil profesional. None si falla o no hay IA."""
    system, user = prompts.prompt_analizar_perfil(perfil, resultado_reglas)
    claves = ("resumen", "fortalezas", "aspectos_mejora", "recomendaciones")
    datos = _completar_json(system, user, set(claves))

    if datos is None or not _validar(datos, campos_texto=("resumen",), campos_lista=claves[1:]):
        if datos is not None:
            logger.warning("OpenAI: análisis de perfil con formato inválido. Se usa el motor de reglas.")
        return None

    return {clave: datos[clave] for clave in claves}


def analizar_cv(texto_cv, resultado_reglas):
    """Análisis cualitativo del CV. None si falla, no hay IA o no hay texto."""
    if not (texto_cv or '').strip():
        return None

    system, user = prompts.prompt_analizar_cv(texto_cv, resultado_reglas)
    claves = ("resumen", "fortalezas", "debilidades", "recomendaciones")
    datos = _completar_json(system, user, set(claves))

    if datos is None or not _validar(datos, campos_texto=("resumen",), campos_lista=claves[1:]):
        if datos is not None:
            logger.warning("OpenAI: análisis de CV con formato inválido. Se usa el motor de reglas.")
        return None

    return {clave: datos[clave] for clave in claves}


def comparar_oferta(oferta, candidato, resultado_reglas):
    """Recomendaciones cualitativas de la comparación con una oferta. None si falla o no hay IA."""
    system, user = prompts.prompt_comparar_oferta(oferta, candidato, resultado_reglas)
    claves = ("recomendaciones",)
    datos = _completar_json(system, user, set(claves))

    if datos is None or not _validar(datos, campos_lista=claves):
        if datos is not None:
            logger.warning("OpenAI: recomendaciones de oferta con formato inválido. Se usa el motor de reglas.")
        return None

    return {clave: datos[clave] for clave in claves}


def optimizar_linkedin(datos_linkedin, contexto, resultado_reglas):
    """Optimización cualitativa del perfil de LinkedIn. None si falla o no hay IA."""
    system, user = prompts.prompt_optimizar_linkedin(datos_linkedin, contexto, resultado_reglas)
    claves = ("titular_optimizado", "fortalezas", "debilidades", "plan_mejora")
    datos = _completar_json(system, user, set(claves))

    if datos is None or not _validar(datos, campos_texto=("titular_optimizado",), campos_lista=claves[1:]):
        if datos is not None:
            logger.warning("OpenAI: optimización de LinkedIn con formato inválido. Se usa el motor de reglas.")
        return None

    return {clave: datos[clave] for clave in claves}


def evaluar_entrevista(respuestas, contexto, resultado_reglas):
    """Feedback cualitativo de la simulación de entrevista. None si falla o no hay IA."""
    system, user = prompts.prompt_evaluar_entrevista(respuestas, contexto, resultado_reglas)
    claves = ("fortalezas", "aspectos_mejora", "recomendaciones")
    datos = _completar_json(system, user, set(claves))

    if datos is None or not _validar(datos, campos_lista=claves):
        if datos is not None:
            logger.warning("OpenAI: feedback de entrevista con formato inválido. Se usa el motor de reglas.")
        return None

    return {clave: datos[clave] for clave in claves}
