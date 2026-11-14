# TAI — Asistente de Búsqueda de Empleo

Trabajo de Fin de Máster (TFM). Aplicación web que ayuda a un candidato a preparar su búsqueda de empleo: perfil profesional, análisis de CV, comparación con ofertas, optimización de LinkedIn y simulación de entrevistas, con feedback generado por reglas propias y, opcionalmente, por IA (OpenAI).

## Descripción

TAI es una aplicación **Django + Django REST Framework** (backend) y **React + TypeScript** (frontend) pensada como asistente personal de búsqueda de empleo. Un usuario se registra, completa su perfil profesional, sube su CV, compara ofertas de empleo reales, optimiza su perfil de LinkedIn y practica con un simulador de entrevistas — cada módulo genera un análisis con puntuación, fortalezas, aspectos de mejora y recomendaciones, y guarda un historial propio y privado por usuario.

## Objetivo

Ofrecer una herramienta única que acompañe todo el proceso de búsqueda de empleo (perfil → CV → ofertas → LinkedIn → entrevistas), con análisis explicables y deterministas por defecto (motor de reglas propio), y la posibilidad de enriquecer ese feedback con IA real (OpenAI) sin cambiar en ningún momento el comportamiento ni la disponibilidad de la aplicación si la IA no está configurada o falla.

## Tecnologías utilizadas

**Backend**
- Python 3 + Django 6.0.6
- Django REST Framework 3.17.1 (API REST, autenticación por token)
- django-cors-headers 4.9.0
- pypdf 6.14.2 (extracción de texto de CV en PDF)
- python-dotenv 1.2.2 (carga de variables de entorno desde `.env`)

**Frontend**
- React 19 + TypeScript
- Vite (bundler y servidor de desarrollo)
- React Router v7 (enrutado)
- lucide-react (iconografía)

**Base de datos**
- SQLite (`db.sqlite3`), a través del ORM de Django — sin configuración adicional necesaria.

**OpenAI**
- SDK oficial `openai` 2.53.0, integrado como servicio centralizado (`backend/usuarios/openai_service.py`). Es **opcional**: si no se configura una clave de API, o la llamada falla por cualquier motivo (clave inválida, límite de uso, timeout, error de conexión...), la aplicación usa automáticamente su propio motor de reglas y sigue funcionando con normalidad.

## Requisitos

- Python 3.10 o superior
- Node.js 18 o superior y npm
- (Opcional) una clave de API de OpenAI, solo si se quiere activar el análisis con IA real

## Instalación

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Frontend

```bash
cd frontend
npm install
```

## Configuración del `.env`

El backend carga automáticamente un archivo `.env` en `backend/.env` (si existe). Copia la plantilla incluida:

```bash
cd backend
cp .env.example .env
```

Variables disponibles:

| Variable | Obligatoria | Descripción |
|---|---|---|
| `DJANGO_SECRET_KEY` | No | Clave secreta de Django. Si se deja vacía, se usa una clave de desarrollo por defecto y el proyecto sigue funcionando igual. |
| `OPENAI_API_KEY` | No | Clave de tu cuenta de OpenAI. Si se deja vacía, todos los análisis usan el motor de reglas propio. |
| `OPENAI_MODEL` | No | Modelo de OpenAI a usar (por defecto `gpt-4o-mini`). |

El archivo `.env` **nunca** debe subirse al repositorio (ya está en `.gitignore`).

## Ejecución del backend

```bash
cd backend
source venv/bin/activate
python manage.py runserver
```

El backend queda disponible en `http://127.0.0.1:8000`.

## Ejecución del frontend

En otra terminal:

```bash
cd frontend
npm run dev
```

El frontend queda disponible en `http://localhost:5173` (o el puerto que indique Vite) y consume el backend en `http://127.0.0.1:8000`.

## Migraciones

Las migraciones ya están incluidas en el repositorio. Para aplicarlas sobre una base de datos nueva:

```bash
cd backend
source venv/bin/activate
python manage.py migrate
```

Para comprobar que no faltan migraciones por generar:

```bash
python manage.py makemigrations --check --dry-run
```

## Tests

```bash
cd backend
source venv/bin/activate
python manage.py test
```

La batería cubre: autenticación, perfil profesional, análisis de perfil (reglas e IA), CV, comparación con ofertas, optimización de LinkedIn, simulador de entrevistas, aislamiento de datos entre usuarios (IDOR) y el servicio de integración con OpenAI (claves válidas/ausentes, errores del SDK, fallback a reglas).

## Estructura del proyecto

```
tai/
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── tai_project/          # configuración de Django (settings, urls)
│   └── usuarios/             # única app Django: todo el dominio de TAI
│       ├── models.py         # Perfil, PerfilProfesional, ResultadoAnalisis,
│       │                     # Curriculum, Oferta, OptimizacionLinkedIn,
│       │                     # SimulacionEntrevista, PreguntaRespuesta
│       ├── views.py          # endpoints de la API
│       ├── serializers.py
│       ├── urls.py
│       ├── admin.py
│       ├── utils.py                  # motor de reglas: perfil y CV
│       ├── comparador.py             # motor de reglas: ofertas
│       ├── optimizador_linkedin.py   # motor de reglas: LinkedIn
│       ├── evaluador_entrevista.py   # motor de reglas: entrevistas
│       ├── openai_service.py         # único punto de contacto con OpenAI
│       ├── openai_prompts.py         # prompts usados por openai_service
│       ├── tests.py
│       └── migrations/
└── frontend/
    ├── src/
    │   ├── pages/             # Login, Register, Dashboard, PerfilProfesional,
    │   │                      # AnalisisPerfil, AnalisisCV, CompararOferta,
    │   │                      # OptimizarLinkedIn, SimuladorEntrevista
    │   ├── components/        # Spinner, Alert (reutilizados en toda la app)
    │   ├── context/           # AuthContext (token, login, logout)
    │   ├── services/          # api.ts (todas las llamadas al backend)
    │   └── App.tsx            # rutas protegidas
    └── package.json
```

## Funcionalidades implementadas

- **Autenticación**: registro, login y logout con Token Authentication de DRF; rutas protegidas tanto en la API como en el frontend.
- **Perfil profesional**: creación/edición con validaciones de formato y longitud.
- **Análisis del perfil**: puntuación de completitud, fortalezas, aspectos de mejora y recomendaciones (reglas o IA), con historial.
- **Análisis de CV**: subida de PDF, extracción de texto real (sin inventar contenido), puntuación y feedback (reglas o IA), con historial.
- **Comparación con ofertas de empleo**: porcentaje de match, habilidades coincidentes/faltantes, compatibilidad de experiencia y estudios (siempre por reglas, deterministas), recomendaciones (reglas o IA).
- **Optimización de LinkedIn**: puntuación, titular optimizado, fortalezas/debilidades y plan de mejora (reglas o IA), sin inventar tecnologías ni experiencia no aportada por el usuario.
- **Simulador de entrevistas**: generación de 10 preguntas adaptadas a los datos reales del usuario (perfil, CV, oferta comparada, LinkedIn), registro de respuestas, evaluación con puntuación determinista por reglas y feedback cualitativo (reglas o IA), historial completo de simulaciones.
- **Integración con OpenAI**: servicio centralizado con manejo de errores (clave ausente, autenticación, límite de uso, timeout, conexión, respuesta inválida) y fallback automático y transparente al motor de reglas.
- **Aislamiento de datos**: cada usuario solo puede ver y modificar sus propios datos en todos los módulos (perfil, CV, ofertas, LinkedIn, entrevistas).
- **Panel de administración de Django**: los 8 modelos del dominio registrados para poder inspeccionar los datos.

## Autor

Antonio González — [GitHub](https://github.com/tonelo2244) · [LinkedIn](https://www.linkedin.com/in/antonio-gonzalez-seisdedos)
