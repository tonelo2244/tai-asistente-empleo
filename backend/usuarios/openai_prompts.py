"""
Prompts para la integración con OpenAI (Sprint 9).

Cada función de este módulo construye el par (system_prompt, user_prompt)
para un dominio concreto de la aplicación. No contiene lógica de llamada a
la API ni de manejo de errores: eso vive en `openai_service.py`, que es el
único módulo que habla realmente con OpenAI.

Reglas seguidas por todos los prompts de este archivo:
- Solo se incluyen datos reales del usuario ya calculados por el motor de
  reglas correspondiente (utils.py, comparador.py, optimizador_linkedin.py,
  evaluador_entrevista.py). Nunca se pide a la IA que invente tecnologías,
  experiencia, certificaciones o datos personales no presentes en la
  entrada.
- Se pide siempre una respuesta JSON estricta, con las claves exactas que
  espera `openai_service.py`, para poder validarla de forma segura.
- Los campos numéricos u objetivos (puntuaciones, porcentajes de match,
  clasificación, listas de habilidades coincidentes/faltantes) se calculan
  siempre mediante el motor de reglas, no mediante la IA: se le pasan a la
  IA como contexto de apoyo (grounding) para que su redacción no los
  contradiga, pero la IA solo redacta el contenido cualitativo (resúmenes,
  fortalezas, debilidades/aspectos de mejora y recomendaciones).
"""

INSTRUCCION_JSON = (
    "Responde ÚNICAMENTE con un objeto JSON válido (sin texto adicional, sin "
    "explicaciones, sin bloques de código markdown), con exactamente estas "
    "claves: {claves}."
)

INSTRUCCION_NO_INVENTAR = (
    "No inventes tecnologías, experiencia, formación, certificaciones ni "
    "datos personales que no aparezcan explícitamente en los datos "
    "proporcionados. Basa tu respuesta únicamente en la información real "
    "indicada a continuación."
)


def _lista_o_vacio(texto, etiqueta):
    texto = (texto or '').strip()
    return f"{etiqueta}: {texto}" if texto else f"{etiqueta}: (sin datos)"


# -----------------------------
# Perfil profesional
# -----------------------------

def prompt_analizar_perfil(perfil, resultado_reglas):
    """
    perfil: instancia de PerfilProfesional (nombre_completo, telefono,
    ciudad, estudios, experiencia, habilidades).
    resultado_reglas: dict ya calculado por utils.analizar_perfil(), usado
    como referencia (p. ej. puntuacion_completitud) para que la IA no la
    contradiga.
    """
    system = (
        "Eres un asesor profesional de empleo que analiza el perfil "
        "profesional de un candidato dentro de la aplicación TAI. "
        f"{INSTRUCCION_NO_INVENTAR}"
    )

    claves = "resumen, fortalezas, aspectos_mejora, recomendaciones"
    user = "\n".join([
        "Analiza el siguiente perfil profesional y genera una evaluación "
        "cualitativa en español, cercana y constructiva.",
        "",
        _lista_o_vacio(perfil.nombre_completo, "Nombre completo"),
        _lista_o_vacio(perfil.telefono, "Teléfono"),
        _lista_o_vacio(perfil.ciudad, "Ciudad"),
        _lista_o_vacio(perfil.estudios, "Estudios"),
        _lista_o_vacio(perfil.experiencia, "Experiencia"),
        _lista_o_vacio(perfil.habilidades, "Habilidades"),
        "",
        f"Porcentaje de completitud del perfil (ya calculado, no lo "
        f"recalcules): {resultado_reglas.get('puntuacion_completitud', 0)}%.",
        "",
        "Genera:",
        "- resumen: un párrafo breve (2-3 frases) valorando el perfil en "
        "conjunto, mencionando el porcentaje de completitud indicado.",
        "- fortalezas: lista de frases cortas con los puntos fuertes "
        "reales del perfil.",
        "- aspectos_mejora: lista de frases cortas con carencias reales "
        "detectadas (campos vacíos o insuficientemente detallados).",
        "- recomendaciones: lista de frases cortas y accionables para "
        "mejorar el perfil.",
        "",
        INSTRUCCION_JSON.format(claves=claves),
    ])
    return system, user


# -----------------------------
# CV
# -----------------------------

def prompt_analizar_cv(texto_cv, resultado_reglas):
    """
    texto_cv: texto plano extraído del PDF del CV.
    resultado_reglas: dict ya calculado por utils.analizar_cv(), incluye
    la puntuación objetiva (0-100) ya calculada por reglas.
    """
    system = (
        "Eres un experto en revisión de currículums (CV) que ayuda a "
        "candidatos a mejorar su CV dentro de la aplicación TAI. "
        f"{INSTRUCCION_NO_INVENTAR}"
    )

    claves = "resumen, fortalezas, debilidades, recomendaciones"
    user = "\n".join([
        "Analiza el siguiente texto extraído de un CV real y genera una "
        "evaluación cualitativa en español, cercana y constructiva.",
        "",
        "Texto del CV:",
        texto_cv.strip(),
        "",
        f"Puntuación objetiva ya calculada (0-100, no la recalcules): "
        f"{resultado_reglas.get('puntuacion', 0)}.",
        "",
        "Genera:",
        "- resumen: un párrafo breve (2-3 frases) valorando el CV en "
        "conjunto, coherente con la puntuación indicada.",
        "- fortalezas: lista de frases cortas con los puntos fuertes "
        "reales detectados en el CV.",
        "- debilidades: lista de frases cortas con carencias reales del "
        "CV (secciones ausentes, poco desarrollo, falta de contacto...).",
        "- recomendaciones: lista de frases cortas y accionables para "
        "mejorar el CV.",
        "",
        INSTRUCCION_JSON.format(claves=claves),
    ])
    return system, user


# -----------------------------
# Comparación con ofertas
# -----------------------------

def prompt_comparar_oferta(oferta, candidato, resultado_reglas):
    """
    oferta: DatosOferta. candidato: DatosCandidato.
    resultado_reglas: dict ya calculado por comparador.comparar_oferta(),
    incluye habilidades_coincidentes/faltantes, porcentaje_match y
    clasificacion ya calculados de forma objetiva (no se le pide a la IA
    que los recalcule, solo que redacte recomendaciones coherentes con
    ellos).
    """
    system = (
        "Eres un asesor de carrera que ayuda a un candidato a entender qué "
        "tan compatible es con una oferta de empleo real, dentro de la "
        f"aplicación TAI. {INSTRUCCION_NO_INVENTAR}"
    )

    claves = "recomendaciones"
    user = "\n".join([
        "Se ha comparado el perfil de un candidato con una oferta de "
        "empleo mediante un motor de reglas. Estos son los datos ya "
        "calculados de forma objetiva:",
        "",
        _lista_o_vacio(oferta.descripcion, "Descripción de la oferta"),
        _lista_o_vacio(oferta.requisitos, "Requisitos de la oferta"),
        _lista_o_vacio(oferta.habilidades, "Habilidades requeridas"),
        _lista_o_vacio(oferta.experiencia_requerida, "Experiencia requerida"),
        _lista_o_vacio(oferta.estudios_requeridos, "Estudios requeridos"),
        "",
        _lista_o_vacio(candidato.experiencia, "Experiencia del candidato"),
        _lista_o_vacio(candidato.estudios, "Estudios del candidato"),
        _lista_o_vacio(candidato.habilidades, "Habilidades del candidato"),
        "",
        f"Porcentaje de match ya calculado (no lo recalcules): "
        f"{resultado_reglas.get('porcentaje_match', 0)}% "
        f"({resultado_reglas.get('clasificacion', '')}).",
        f"Habilidades coincidentes: "
        f"{', '.join(resultado_reglas.get('habilidades_coincidentes', [])) or '(ninguna)'}.",
        f"Habilidades faltantes: "
        f"{', '.join(resultado_reglas.get('habilidades_faltantes', [])) or '(ninguna)'}.",
        "",
        "Genera únicamente:",
        "- recomendaciones: lista de frases cortas y accionables para que "
        "el candidato mejore su compatibilidad con esta oferta concreta, "
        "coherentes con el porcentaje de match y las habilidades "
        "faltantes indicadas.",
        "",
        INSTRUCCION_JSON.format(claves=claves),
    ])
    return system, user


# -----------------------------
# Optimización de LinkedIn
# -----------------------------

def prompt_optimizar_linkedin(datos, contexto, resultado_reglas):
    """
    datos: DatosLinkedIn. contexto: DatosContexto.
    resultado_reglas: dict ya calculado por optimizador_linkedin
    .optimizar_linkedin(), incluye puntuacion, clasificacion y el
    titular_optimizado generado por reglas (usado como referencia mínima).
    """
    system = (
        "Eres un experto en optimización de perfiles de LinkedIn dentro de "
        f"la aplicación TAI. {INSTRUCCION_NO_INVENTAR} El titular que "
        "propongas debe basarse exclusivamente en las tecnologías, "
        "experiencia y titular actuales indicados a continuación."
    )

    claves = "titular_optimizado, fortalezas, debilidades, plan_mejora"
    user = "\n".join([
        _lista_o_vacio(datos.titular_actual, "Titular actual de LinkedIn"),
        _lista_o_vacio(datos.extracto, "Extracto (\"Acerca de\") actual"),
        _lista_o_vacio(datos.experiencia, "Experiencia en LinkedIn"),
        _lista_o_vacio(datos.estudios, "Estudios en LinkedIn"),
        _lista_o_vacio(datos.habilidades, "Habilidades en LinkedIn"),
        "",
        _lista_o_vacio(contexto.perfil_experiencia, "Experiencia (Perfil TAI)"),
        _lista_o_vacio(contexto.perfil_estudios, "Estudios (Perfil TAI)"),
        _lista_o_vacio(contexto.perfil_habilidades, "Habilidades (Perfil TAI)"),
        "",
        f"Puntuación objetiva ya calculada (0-100, no la recalcules): "
        f"{resultado_reglas.get('puntuacion', 0)} "
        f"({resultado_reglas.get('clasificacion', '')}).",
        "",
        "Genera:",
        "- titular_optimizado: un titular profesional de LinkedIn mejorado "
        "(una sola línea), usando solo las tecnologías y datos reales "
        "indicados arriba.",
        "- fortalezas: lista de frases cortas con los puntos fuertes "
        "reales del perfil de LinkedIn actual.",
        "- debilidades: lista de frases cortas con carencias reales "
        "detectadas.",
        "- plan_mejora: lista de frases cortas y accionables para mejorar "
        "el perfil de LinkedIn.",
        "",
        INSTRUCCION_JSON.format(claves=claves),
    ])
    return system, user


# -----------------------------
# Simulador de entrevistas
# -----------------------------

def prompt_evaluar_entrevista(respuestas, contexto, resultado_reglas):
    """
    respuestas: lista de RespuestaEntrevista (tipo, pregunta, respuesta,
    orden). contexto: ContextoEntrevista.
    resultado_reglas: dict ya calculado por evaluador_entrevista
    .evaluar_entrevista(), incluye puntuacion y clasificacion ya
    calculados de forma objetiva y determinista.
    """
    system = (
        "Eres un entrevistador de RRHH experto que da feedback "
        "constructivo tras una simulación de entrevista de trabajo, "
        f"dentro de la aplicación TAI. {INSTRUCCION_NO_INVENTAR}"
    )

    preguntas_respuestas = "\n".join(
        f"{item.orden}. [{item.tipo}] {item.pregunta}\n"
        f"   Respuesta: {(item.respuesta or '').strip() or '(sin responder)'}"
        for item in respuestas
    )

    claves = "fortalezas, aspectos_mejora, recomendaciones"
    user = "\n".join([
        "Estas son las preguntas y respuestas de una simulación de "
        "entrevista de trabajo:",
        "",
        preguntas_respuestas,
        "",
        _lista_o_vacio(contexto.perfil_experiencia, "Experiencia (Perfil TAI)"),
        _lista_o_vacio(contexto.texto_cv, "CV analizado"),
        _lista_o_vacio(contexto.oferta_titulo, "Oferta comparada"),
        _lista_o_vacio(contexto.linkedin_titular, "Titular de LinkedIn"),
        "",
        f"Puntuación objetiva ya calculada (0-100, no la recalcules): "
        f"{resultado_reglas.get('puntuacion', 0)} "
        f"({resultado_reglas.get('clasificacion', '')}).",
        "",
        "Genera:",
        "- fortalezas: lista de frases cortas señalando qué ha hecho bien "
        "el candidato en sus respuestas.",
        "- aspectos_mejora: lista de frases cortas señalando carencias "
        "reales en las respuestas (vacías, demasiado breves, poco claras "
        "o poco relacionadas con su perfil real).",
        "- recomendaciones: lista de frases cortas y accionables para "
        "mejorar en una próxima entrevista.",
        "",
        INSTRUCCION_JSON.format(claves=claves),
    ])
    return system, user
