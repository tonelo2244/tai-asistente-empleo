import re
import os

from pypdf import PdfReader

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


# -----------------------------
# Análisis de CV (Fase 6)
# -----------------------------

SECCIONES_CV = {
    'experiencia': ['experiencia laboral', 'experiencia profesional', 'work experience', 'experiencia'],
    'formacion': ['formación académica', 'formacion academica', 'educación', 'educacion', 'estudios', 'education'],
    'habilidades': ['habilidades', 'competencias', 'skills'],
    'contacto': ['contacto', 'contact'],
}


def extraer_texto_pdf(archivo):
    """
    Extrae el texto de un PDF (objeto tipo archivo). Devuelve '' si el PDF
    no tiene texto seleccionable (p.ej. es un documento escaneado) o si no
    se puede leer. Nunca inventa contenido.
    """
    try:
        lector = PdfReader(archivo)
        paginas_texto = [pagina.extract_text() or '' for pagina in lector.pages]
    except Exception:
        return ''
    finally:
        try:
            archivo.seek(0)
        except (AttributeError, ValueError):
            pass

    return '\n'.join(paginas_texto).strip()


def detectar_secciones(texto):
    if not texto:
        return []

    texto_lower = texto.lower()
    detectadas = set()

    for seccion, variantes in SECCIONES_CV.items():
        for variante in variantes:
            if variante in texto_lower:
                detectadas.add(seccion)
                break

    return sorted(detectadas)


def analizar_cv(texto):
    """
    Analiza el texto extraído de un CV con reglas propias.
    Misma filosofía que analizar_perfil(): sin inventar contenido,
    basado únicamente en lo detectado en el texto real.
    """
    texto_limpio = (texto or '').strip()

    if not texto_limpio:
        return {
            "resumen": (
                "No se ha podido extraer texto de este PDF. Puede tratarse de "
                "un documento escaneado sin texto seleccionable."
            ),
            "puntuacion": 0,
            "fortalezas": [],
            "debilidades": ["No se ha podido leer contenido textual del CV."],
            "recomendaciones": [
                "Sube un PDF con texto seleccionable en lugar de una imagen escaneada."
            ],
        }

    fortalezas = []
    debilidades = []
    recomendaciones = []
    puntuacion = 0

    palabras = len(texto_limpio.split())
    secciones = detectar_secciones(texto_limpio)
    keywords = detectar_keywords(texto_limpio)
    tiene_email = bool(re.search(r'[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}', texto_limpio))
    tiene_telefono = bool(re.search(r'(\+?\d[\d\s\-()]{7,}\d)', texto_limpio))

    if palabras >= 150:
        fortalezas.append("El CV tiene un contenido extenso y detallado.")
        puntuacion += 25
    elif palabras >= 60:
        puntuacion += 15
        recomendaciones.append("Amplía el contenido de tu CV con más detalles de tu trayectoria.")
    else:
        debilidades.append("El CV tiene muy poco contenido de texto.")
        recomendaciones.append("Añade más información: experiencia, formación y habilidades.")

    if tiene_email or tiene_telefono:
        fortalezas.append("El CV incluye datos de contacto.")
        puntuacion += 15
    else:
        debilidades.append("No se detectan datos de contacto claros (email o teléfono).")
        recomendaciones.append("Incluye un email y un teléfono de contacto visibles.")

    if 'experiencia' in secciones:
        fortalezas.append("Se detecta una sección de experiencia profesional.")
        puntuacion += 20
    else:
        debilidades.append("No se detecta una sección clara de experiencia profesional.")
        recomendaciones.append("Añade una sección de experiencia profesional bien diferenciada.")

    if 'formacion' in secciones:
        fortalezas.append("Se detecta una sección de formación académica.")
        puntuacion += 15
    else:
        debilidades.append("No se detecta una sección clara de formación académica.")
        recomendaciones.append("Añade una sección de formación académica.")

    if 'habilidades' in secciones or keywords:
        fortalezas.append("Se detecta una sección de habilidades.")
        puntuacion += 15

        if keywords:
            fortalezas.append(f"Se detectaron habilidades técnicas: {', '.join(keywords)}.")
        else:
            recomendaciones.append("Incluye habilidades técnicas concretas como lenguajes o herramientas.")
    else:
        debilidades.append("No se detecta una sección clara de habilidades.")
        recomendaciones.append("Añade una sección de habilidades técnicas y profesionales.")

    puntuacion = min(puntuacion, 100)

    if puntuacion >= 80:
        resumen = f"Tu CV obtiene una puntuación de {puntuacion}/100. Está bien estructurado."
    elif puntuacion >= 50:
        resumen = f"Tu CV obtiene una puntuación de {puntuacion}/100. Tiene una buena base, pero puede mejorar."
    else:
        resumen = f"Tu CV obtiene una puntuación de {puntuacion}/100. Te recomendamos reforzarlo antes de enviarlo."

    return {
        "resumen": resumen,
        "puntuacion": puntuacion,
        "fortalezas": fortalezas,
        "debilidades": debilidades,
        "recomendaciones": recomendaciones,
    }


def analizar_cv_ia(texto):
    """
    Punto de entrada principal para el análisis de CV.
    De momento usa reglas propias.
    Más adelante podrá usar OpenAI si existe OPENAI_API_KEY (misma
    arquitectura que analizar_perfil_ia).
    """
    openai_key = os.environ.get("OPENAI_API_KEY", "")

    if openai_key:
        # Futura integración con OpenAI.
        pass

    return analizar_cv(texto)