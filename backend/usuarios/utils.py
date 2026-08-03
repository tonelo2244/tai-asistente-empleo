import re
import os

KEYWORDS_TECNICAS = {
    'python': ['python', 'py'],
    'django': ['django', 'drf', 'django rest'],
    'react': ['react', 'reactjs', 'react.js'],
    'typescript': ['typescript', 'ts'],
    'javascript': ['javascript', 'js'],
    'html': ['html', 'html5'],
    'css': ['css', 'css3'],
    'sql': ['sql'],
    'postgresql': ['postgresql', 'postgres'],
    'docker': ['docker'],
    'git': ['git', 'github'],
}


def detectar_keywords(texto):
    if not texto:
        return []

    texto_lower = texto.lower()
    detectadas = set()

    for categoria, variantes in KEYWORDS_TECNICAS.items():
        for variante in variantes:
            if re.search(rf'\b{re.escape(variante)}\b', texto_lower):
                detectadas.add(categoria)
                break

    return sorted(list(detectadas))


def calcular_puntuacion(perfil):
    campos = [
        perfil.nombre_completo,
        perfil.telefono,
        perfil.ciudad,
        perfil.estudios,
        perfil.experiencia,
        perfil.habilidades,
    ]

    total = len(campos)
    rellenos = sum(1 for campo in campos if campo and str(campo).strip())

    return int((rellenos / total) * 100)


def analizar_perfil(perfil):
    fortalezas = []
    aspectos_mejora = []
    recomendaciones = []

    puntuacion = calcular_puntuacion(perfil)

    if perfil.nombre_completo.strip():
        fortalezas.append("Tu perfil tiene nombre completo, lo que genera más confianza.")
    else:
        aspectos_mejora.append("No has añadido tu nombre completo.")
        recomendaciones.append("Añade tu nombre completo para que tu perfil sea más profesional.")

    if perfil.telefono.strip():
        fortalezas.append("Has incluido teléfono de contacto.")
    else:
        aspectos_mejora.append("Falta el teléfono de contacto.")
        recomendaciones.append("Añade un teléfono de contacto.")

    if perfil.ciudad.strip():
        fortalezas.append(f"Has indicado que estás en {perfil.ciudad}, útil para ofertas locales.")
    else:
        aspectos_mejora.append("No has indicado tu ciudad.")
        recomendaciones.append("Añade tu ciudad para recibir recomendaciones más ajustadas.")

    if perfil.estudios.strip():
        fortalezas.append("Has descrito tu formación académica.")
    else:
        aspectos_mejora.append("El campo de estudios está vacío.")
        recomendaciones.append("Añade tu formación académica.")

    if perfil.experiencia.strip():
        fortalezas.append("Has añadido experiencia profesional.")
        if len(perfil.experiencia.strip()) < 100:
            aspectos_mejora.append("La experiencia profesional está descrita de forma muy breve.")
            recomendaciones.append("Intenta detallar más tu experiencia: empresa, rol y logros concretos.")
    else:
        aspectos_mejora.append("No has descrito tu experiencia profesional.")
        recomendaciones.append("Añade experiencia laboral, prácticas o proyectos personales.")

    if perfil.habilidades.strip():
        fortalezas.append("Has listado tus habilidades técnicas o profesionales.")
        keywords = detectar_keywords(perfil.habilidades)

        if keywords:
            fortalezas.append(f"Se detectaron habilidades técnicas: {', '.join(keywords)}.")
        else:
            aspectos_mejora.append("Las habilidades no incluyen tecnologías o herramientas reconocibles.")
            recomendaciones.append("Añade habilidades técnicas concretas como lenguajes o herramientas.")
    else:
        aspectos_mejora.append("No has añadido habilidades.")
        recomendaciones.append("Lista tus habilidades técnicas, idiomas o herramientas.")

    if puntuacion == 100:
        resumen = "Tu perfil está completo al 100%. Estás en una posición excelente para buscar empleo."
    elif puntuacion >= 66:
        resumen = f"Tu perfil está completo al {puntuacion}%. Tienes una buena base, pero aún puedes mejorar algunos campos."
    elif puntuacion >= 33:
        resumen = f"Tu perfil está completo al {puntuacion}%. Es un buen comienzo, pero faltan datos importantes."
    else:
        resumen = f"Tu perfil está completo al {puntuacion}%. Te recomendamos completar tu perfil antes de buscar empleo."

    return {
        "resumen": resumen,
        "fortalezas": fortalezas,
        "aspectos_mejora": aspectos_mejora,
        "recomendaciones": recomendaciones,
    }


def analizar_perfil_ia(perfil):
    """
    Punto de entrada principal para el análisis.
    De momento usa reglas propias.
    Más adelante podrá usar OpenAI si existe OPENAI_API_KEY.
    """
    openai_key = os.environ.get("OPENAI_API_KEY", "")

    if openai_key:
        # Futura integración con OpenAI.
        pass

    resultado = analizar_perfil(perfil)
    resultado["puntuacion_completitud"] = calcular_puntuacion(perfil)

    return resultado