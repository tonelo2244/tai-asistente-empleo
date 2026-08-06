# Manual de usuario — TAI

Guía rápida para usar la aplicación TAI con el backend y el frontend en marcha (ver `README.md` para la puesta en marcha). Pensada para poder recorrer todas las funcionalidades sin conocer el código.

## 1. Registro

1. Abre `http://localhost:5173` (o el puerto que indique Vite) — se redirige automáticamente a `/login`.
2. Pulsa el enlace para ir a la pantalla de registro (`/registro`).
3. Rellena usuario, email y contraseña, y confirma.
4. Al registrarte, se te asigna automáticamente un rol (`usuario` por defecto) y quedas identificado con un token de sesión.

## 2. Login

1. En `/login`, introduce el usuario y la contraseña con los que te registraste.
2. Si las credenciales son correctas, entras directamente al Dashboard. Si son incorrectas, se muestra un mensaje de error sin detalles técnicos.
3. El token de sesión se guarda en el navegador; mientras exista, las rutas protegidas (todas salvo login/registro) son accesibles.

## 3. Dashboard

Pantalla principal tras iniciar sesión (`/dashboard`). Muestra una tarjeta de acceso a cada módulo de la aplicación: Perfil, Análisis, CV, Ofertas, LinkedIn y Entrevistas, además de tu nombre de usuario y el botón para cerrar sesión.

## 4. Perfil profesional

1. Entra en la tarjeta "Perfil" (`/perfil`).
2. Rellena tus datos: nombre completo, teléfono, ciudad, estudios, experiencia y habilidades.
3. Guarda los cambios. El perfil es siempre el tuyo — no existe forma de ver ni editar el de otro usuario.
4. Estos datos son la base que usan el resto de módulos (análisis, comparación de ofertas, entrevistas) para generar resultados personalizados y sin inventar información que no hayas indicado tú.

## 5. Análisis del perfil

1. Entra en la tarjeta "Análisis" (`/analisis`).
2. Pulsa el botón para generar un nuevo análisis.
3. Verás un resumen, un porcentaje de completitud, tus fortalezas, los aspectos a mejorar y recomendaciones concretas basadas en lo que hayas rellenado en tu perfil.
4. Cada análisis que generes queda guardado en tu historial (ver punto 10).

## 6. CV

1. Entra en la tarjeta "CV" (`/cv`).
2. Sube tu currículum en formato PDF (máximo 5 MB; debe tener texto seleccionable, no una imagen escaneada).
3. La aplicación extrae el texto real de tu PDF y genera una puntuación, fortalezas, debilidades y recomendaciones basadas únicamente en lo que detecta en tu documento.
4. Cada CV subido queda guardado en tu historial.

## 7. Ofertas de empleo

1. Entra en la tarjeta "Ofertas" (`/ofertas`).
2. Rellena los datos de una oferta real (título del puesto, empresa, descripción, requisitos, habilidades pedidas, etc.).
3. La aplicación compara automáticamente esa oferta con tu perfil y tu último CV subido, y te muestra un porcentaje de compatibilidad ("match"), las habilidades que coinciden, las que te faltan, y recomendaciones para mejorar tu candidatura a esa oferta concreta.
4. Puedes comparar tantas ofertas como quieras; todas quedan en tu historial.

## 8. Optimización de LinkedIn

1. Entra en la tarjeta "LinkedIn" (`/linkedin`).
2. Introduce el contenido actual de tu perfil de LinkedIn (titular, extracto/"Acerca de", experiencia, estudios, habilidades).
3. La aplicación te da una puntuación, un titular optimizado (construido solo con tecnologías y datos que tú ya tienes, nunca inventados), tus fortalezas, tus debilidades y un plan de mejora.
4. Cada optimización queda guardada en tu historial.

## 9. Simulador de entrevistas

1. Entra en la tarjeta "Entrevistas" (`/entrevista`).
2. Pulsa "Iniciar simulación": se generan 10 preguntas (presentación, experiencia, formación, habilidades, fortalezas, debilidades, motivación, trabajo en equipo, resolución de problemas y objetivos), adaptadas a tu perfil, tu CV, la última oferta que hayas comparado y tu LinkedIn, si los tienes rellenos.
3. Responde cada pregunta y avanza a la siguiente. En la última se te permite finalizar la entrevista.
4. Al finalizar verás tu puntuación, clasificación, fortalezas, aspectos de mejora y recomendaciones sobre tus respuestas.
5. Cada simulación completa queda guardada en tu historial, con todas las preguntas y respuestas.

## 10. IA y fallback

- Todos los módulos de análisis (Perfil, CV, Ofertas, LinkedIn, Entrevistas) pueden generar su parte de texto (resúmenes, fortalezas, debilidades, recomendaciones) usando **IA real (OpenAI)** si el administrador de la aplicación ha configurado una clave válida en `backend/.env` (variable `OPENAI_API_KEY`).
- **Si no hay ninguna clave configurada, o la llamada a OpenAI falla por cualquier motivo** (clave inválida, límite de uso alcanzado, error de conexión, tiempo de espera agotado...), la aplicación **no se rompe ni muestra ningún error**: usa automáticamente su propio motor de reglas y el resultado tiene exactamente el mismo formato.
- Las puntuaciones, porcentajes de compatibilidad y clasificaciones **siempre** se calculan por reglas propias, deterministas y auditables, se use IA o no — nunca los decide la IA, precisamente para que sean coherentes y verificables.
- Como usuario no necesitas hacer nada distinto en ningún caso: la experiencia de uso es idéntica con o sin IA activada.

## 11. Historiales

Cada uno de los cinco módulos (Análisis, CV, Ofertas, LinkedIn, Entrevistas) tiene su propio historial, accesible desde la propia pantalla del módulo:

- Se muestra en orden cronológico, del más reciente al más antiguo.
- Cada usuario solo ve su propio historial — nunca el de otro usuario, aunque lo intente forzar manualmente.
- En el caso de Entrevistas, el historial incluye además el detalle completo de preguntas y respuestas de cada simulación.

## 12. Cerrar sesión

Pulsa el botón "Cerrar sesión" en el Dashboard. Se elimina tu token de la sesión del navegador y vuelves a la pantalla de login; para volver a entrar necesitas iniciar sesión de nuevo con tu usuario y contraseña.
