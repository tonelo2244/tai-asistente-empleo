"""
Motor de generación de una búsqueda optimizada de ofertas de empleo en
LinkedIn Jobs, a partir del perfil profesional y el CV del usuario.

Todas las funciones de este módulo son Python puro (sin dependencias de
Django ni acceso a base de datos), igual que `utils.py`, `comparador.py`,
`optimizador_linkedin.py` y `evaluador_entrevista.py`, para que sean
testeables de forma aislada y fáciles de sustituir.

No usa la API de LinkedIn, no hace scraping y no automatiza ningún inicio
de sesión: únicamente construye la URL pública y oficial de búsqueda de
LinkedIn Jobs (`https://www.linkedin.com/jobs/search/`) con los parámetros
de consulta que la propia página acepta. Es el usuario quien decide si
abre esa URL; el backend nunca hace ninguna petición a LinkedIn.

Punto de sustitución para IA: `generar_busqueda_empleo_ia()` mantiene la
firma y la forma del resultado; hoy delega en `generar_busqueda_empleo()`
(reglas propias) y, si hay IA disponible, mejora únicamente el puesto
sugerido y el texto de la consulta — nunca las tecnologías detectadas.
"""
from dataclasses import dataclass
from urllib.parse import urlencode

from . import openai_service
from .comparador import extraer_primer_numero
from .utils import detectar_keywords

LINKEDIN_JOBS_URL = "https://www.linkedin.com/jobs/search/"

MODALIDADES_VALIDAS = ('cualquiera', 'presencial', 'hibrido', 'remoto')

# Código del parámetro f_WT (Workplace Type) que acepta la propia búsqueda
# pública de LinkedIn Jobs; 'cualquiera' no añade ningún filtro de modalidad.
CODIGOS_MODALIDAD = {
    'presencial': '1',
    'remoto': '2',
    'hibrido': '3',
}

# Nombres de tecnología con el casing real de marca (mismo criterio que
# optimizador_linkedin.py y evaluador_entrevista.py).
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

# Agrupación propia de este motor a partir de las tecnologías ya
# reconocidas por detectar_keywords() (utils.py); no se define ninguna
# tecnología nueva, solo se reagrupan las 11 ya existentes en toda la app.
CATEGORIAS_PUESTO = {
    'frontend': {'react', 'typescript', 'javascript', 'html', 'css'},
    'backend': {'python', 'django'},
    'datos': {'sql', 'postgresql'},
    'devops': {'docker', 'git'},
}

PUESTOS_POR_CATEGORIA = {
    'frontend': 'Desarrollador/a Frontend',
    'backend': 'Desarrollador/a Backend',
    'full_stack': 'Desarrollador/a Full Stack',
    'datos': 'Desarrollador/a de Datos',
    'devops': 'DevOps',
}

PUESTO_GENERICO = 'Desarrollador/a de Software'

# Máximo de tecnologías que se incluyen en la consulta de búsqueda.
MAX_TECNOLOGIAS_CONSULTA = 5

# Indicios reales de un perfil junior: formación reciente, prácticas o
# primera experiencia. Nunca se infiere "senior": sin estos indicios, se
# deja el nivel sin especificar en vez de inventar una seniority.
PALABRAS_JUNIOR = (
    'práctica', 'practicas', 'becari', 'junior', 'recién titulad',
    'recien titulad', 'sin experiencia', 'primer empleo', 'en formación',
    'en formacion', 'estudiante',
)

LONGITUD_MAXIMA_CAMPO = 100
LONGITUD_MAXIMA_CONSULTA = 150


@dataclass
class DatosBusqueda:
    """Datos introducidos por el usuario para la búsqueda."""
    puesto_objetivo: str = ''
    ubicacion: str = ''
    modalidad: str = 'cualquiera'


@dataclass
class ContextoBusqueda:
    """Datos reales del usuario (Perfil Profesional + CV) usados para
    inferir el puesto, el nivel y las tecnologías prioritarias."""
    perfil_experiencia: str = ''
    perfil_estudios: str = ''
    perfil_habilidades: str = ''
    texto_cv: str = ''


def _nombre_visible(keyword):
    return NOMBRES_VISIBLES.get(keyword, keyword.capitalize())


def _validar_modalidad(modalidad):
    """Modalidad normalizada contra las opciones admitidas; cualquier
    valor no reconocido se trata como 'cualquiera'."""
    modalidad = (modalidad or '').strip().lower()
    return modalidad if modalidad in MODALIDADES_VALIDAS else 'cualquiera'


def _tecnologias_prioritarias(contexto: ContextoBusqueda) -> list:
    """Tecnologías reales detectadas en el perfil y el CV, sin duplicados
    y limitadas a las más relevantes. Nunca inventa tecnologías: solo
    reconoce las ya presentes en KEYWORDS_TECNICAS (utils.py)."""
    texto_completo = " ".join(filter(None, [
        contexto.perfil_habilidades, contexto.perfil_experiencia, contexto.texto_cv,
    ]))
    keywords = detectar_keywords(texto_completo)
    return [_nombre_visible(k) for k in keywords[:MAX_TECNOLOGIAS_CONSULTA]]


def _inferir_categoria(contexto: ContextoBusqueda) -> str:
    """Categoría de puesto inferida únicamente de las tecnologías reales
    detectadas en el perfil y el CV."""
    texto_completo = " ".join(filter(None, [
        contexto.perfil_habilidades, contexto.perfil_experiencia, contexto.texto_cv,
    ]))
    detectadas = set(detectar_keywords(texto_completo))

    tiene_frontend = bool(detectadas & CATEGORIAS_PUESTO['frontend'])
    tiene_backend = bool(detectadas & CATEGORIAS_PUESTO['backend'])
    tiene_datos = bool(detectadas & CATEGORIAS_PUESTO['datos'])
    tiene_devops = bool(detectadas & CATEGORIAS_PUESTO['devops'])

    if tiene_frontend and tiene_backend:
        return 'full_stack'
    if tiene_backend:
        return 'backend'
    if tiene_frontend:
        return 'frontend'
    if tiene_datos:
        return 'datos'
    if tiene_devops:
        return 'devops'
    return ''


def _inferir_puesto_sugerido(datos: DatosBusqueda, contexto: ContextoBusqueda) -> str:
    """Prioriza siempre el puesto objetivo escrito por el usuario; si no
    existe, infiere una categoría únicamente a partir de tecnologías reales."""
    puesto_objetivo = (datos.puesto_objetivo or '').strip()
    if puesto_objetivo:
        return puesto_objetivo[:LONGITUD_MAXIMA_CAMPO]

    categoria = _inferir_categoria(contexto)
    return PUESTOS_POR_CATEGORIA.get(categoria, PUESTO_GENERICO)


def _inferir_nivel(contexto: ContextoBusqueda) -> str:
    """'junior' si el contenido real indica formación reciente, prácticas
    o experiencia limitada (0-1 años, o ninguna experiencia aportada); en
    caso contrario se deja sin especificar — nunca se infiere "senior": sin
    indicios claros, no se inventa una seniority que el usuario no ha
    demostrado."""
    texto_completo = " ".join(filter(None, [
        contexto.perfil_experiencia, contexto.perfil_estudios, contexto.texto_cv,
    ])).lower()

    if any(palabra in texto_completo for palabra in PALABRAS_JUNIOR):
        return 'junior'

    texto_experiencia = " ".join(filter(None, [
        contexto.perfil_experiencia, contexto.texto_cv,
    ])).strip()
    if not texto_experiencia:
        return 'junior'

    anios = extraer_primer_numero(texto_experiencia)
    if anios is not None and anios <= 1:
        return 'junior'

    return ''


def _construir_consulta(puesto_sugerido, tecnologias_prioritarias, nivel_sugerido) -> str:
    """Texto de búsqueda sin palabras duplicadas (p. ej. si el puesto
    objetivo ya menciona una tecnología que también aparece en
    tecnologias_prioritarias); nunca queda vacío porque siempre incluye al
    menos el puesto sugerido, que a su vez nunca es vacío. El deduplicado
    se hace palabra a palabra, no por segmento completo, para detectar
    también los duplicados que cruzan dos partes distintas."""
    partes = [puesto_sugerido] + list(tecnologias_prioritarias)
    if nivel_sugerido:
        partes.append(nivel_sugerido.capitalize())

    palabras = " ".join(parte.strip() for parte in partes if parte and parte.strip()).split()

    vistas = set()
    palabras_unicas = []
    for palabra in palabras:
        clave = palabra.lower()
        if clave not in vistas:
            vistas.add(clave)
            palabras_unicas.append(palabra)

    consulta = " ".join(palabras_unicas).strip()
    return consulta[:LONGITUD_MAXIMA_CONSULTA] or puesto_sugerido


def _construir_url_linkedin(consulta, ubicacion, modalidad) -> str:
    """URL pública y oficial de búsqueda de LinkedIn Jobs, con tildes,
    espacios y caracteres especiales codificados correctamente mediante
    `urlencode`. No se realiza ninguna petición a LinkedIn."""
    parametros = {'keywords': consulta}

    ubicacion = (ubicacion or '').strip()
    if ubicacion:
        parametros['location'] = ubicacion

    codigo_modalidad = CODIGOS_MODALIDAD.get(modalidad)
    if codigo_modalidad:
        parametros['f_WT'] = codigo_modalidad

    return f"{LINKEDIN_JOBS_URL}?{urlencode(parametros)}"


def generar_busqueda_empleo(datos: DatosBusqueda, contexto: ContextoBusqueda) -> dict:
    """
    Reglas de generación (sin IA) de una búsqueda optimizada de LinkedIn
    Jobs. Devuelve el mismo formato que usará `generar_busqueda_empleo_ia()`
    si la IA está disponible. Resultado determinista: sin aleatoriedad.
    """
    modalidad = _validar_modalidad(datos.modalidad)
    tecnologias_prioritarias = _tecnologias_prioritarias(contexto)
    puesto_sugerido = _inferir_puesto_sugerido(datos, contexto)
    nivel_sugerido = _inferir_nivel(contexto)
    consulta = _construir_consulta(puesto_sugerido, tecnologias_prioritarias, nivel_sugerido)
    ubicacion = (datos.ubicacion or '').strip()[:LONGITUD_MAXIMA_CAMPO]

    return {
        "puesto_sugerido": puesto_sugerido,
        "nivel_sugerido": nivel_sugerido,
        "tecnologias_prioritarias": tecnologias_prioritarias,
        "consulta": consulta,
        "ubicacion": ubicacion,
        "modalidad": modalidad,
        "linkedin_url": _construir_url_linkedin(consulta, ubicacion, modalidad),
    }


def _tecnologias_respetadas(consulta_ia, tecnologias_prioritarias) -> bool:
    """True si la consulta generada por IA no menciona ninguna de las
    tecnologías reconocidas por la aplicación (KEYWORDS_TECNICAS en
    utils.py) que no esté ya en tecnologias_prioritarias. Es la barrera
    que impide que la IA proponga una tecnología reconocida que el
    usuario no tiene detectada en su perfil o CV real. Comparte la misma
    limitación que el resto de motores de la aplicación: solo puede
    detectar tecnologías dentro del vocabulario ya reconocido por
    detectar_keywords(); no puede evaluar términos completamente ajenos a
    ese vocabulario, para eso el prompt (INSTRUCCION_NO_INVENTAR) es la
    única barrera disponible, igual que en comparador.py y
    optimizador_linkedin.py."""
    permitidas = set()
    for tecnologia in tecnologias_prioritarias:
        permitidas.update(detectar_keywords(tecnologia))

    detectadas_en_ia = set(detectar_keywords(consulta_ia))
    return detectadas_en_ia <= permitidas


def generar_busqueda_empleo_ia(datos: DatosBusqueda, contexto: ContextoBusqueda) -> dict:
    """
    Punto de entrada principal. El motor de reglas (generar_busqueda_empleo)
    se calcula siempre: la ubicación, la modalidad y las tecnologías
    prioritarias son siempre las calculadas por reglas. Si hay una clave de
    OpenAI configurada y la llamada tiene éxito, y la consulta generada no
    menciona ninguna tecnología fuera de tecnologias_prioritarias, se
    sustituyen únicamente el puesto sugerido y la consulta por la versión
    mejorada por IA. Si la IA falla, no está disponible, o intenta
    introducir una tecnología no detectada por reglas, se conserva el
    resultado de reglas.
    """
    resultado = generar_busqueda_empleo(datos, contexto)

    resultado_ia = openai_service.generar_busqueda_empleo(datos, contexto, resultado)
    if resultado_ia is not None and _tecnologias_respetadas(
        resultado_ia["consulta"], resultado["tecnologias_prioritarias"]
    ):
        resultado["puesto_sugerido"] = resultado_ia["puesto_sugerido"]
        resultado["consulta"] = resultado_ia["consulta"]
        resultado["linkedin_url"] = _construir_url_linkedin(
            resultado["consulta"], resultado["ubicacion"], resultado["modalidad"]
        )

    return resultado
