import io
import json
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import httpx
import openai
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from rest_framework.authtoken.models import Token

from . import evaluador_entrevista as ee
from . import openai_service
from . import optimizador_linkedin as li
from .comparador import (
    DatosCandidato,
    DatosOferta,
    calcular_porcentaje_match,
    clasificar_match,
    comparar_habilidades,
    comparar_oferta,
    comparar_oferta_ia,
    evaluar_estudios,
    evaluar_experiencia,
)
from .models import (
    Curriculum,
    Oferta,
    OptimizacionLinkedIn,
    Perfil,
    PerfilProfesional,
    PreguntaRespuesta,
    ResultadoAnalisis,
    SimulacionEntrevista,
)
from .utils import (
    analizar_cv,
    analizar_cv_ia,
    analizar_perfil,
    analizar_perfil_ia,
    calcular_puntuacion,
)


def crear_pdf(lineas=None):
    """Construye un PDF real en memoria (opcionalmente con texto seleccionable)."""
    writer = PdfWriter()
    page = writer.add_blank_page(width=400, height=600)

    if lineas:
        y = 550
        comandos = []
        for linea in lineas:
            escapado = linea.replace('\\', r'\\').replace('(', r'\(').replace(')', r'\)')
            comandos.append(f"BT /Helv 12 Tf 20 {y} Td ({escapado}) Tj ET")
            y -= 20

        stream_obj = DecodedStreamObject()
        stream_obj.set_data("\n".join(comandos).encode('latin-1'))
        content_ref = writer._add_object(stream_obj)

        font_dict = DictionaryObject()
        font_dict[NameObject("/Type")] = NameObject("/Font")
        font_dict[NameObject("/Subtype")] = NameObject("/Type1")
        font_dict[NameObject("/BaseFont")] = NameObject("/Helvetica")
        font_ref = writer._add_object(font_dict)

        resources = DictionaryObject()
        font_res = DictionaryObject()
        font_res[NameObject("/Helv")] = font_ref
        resources[NameObject("/Font")] = font_res

        page[NameObject("/Contents")] = content_ref
        page[NameObject("/Resources")] = resources

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


class PingTests(TestCase):
    def test_ping_raiz(self):
        respuesta = self.client.get('/api/ping/')
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json(), {"message": "Backend TAI funcionando"})

    def test_ping_usuarios(self):
        respuesta = self.client.get('/api/usuarios/ping/')
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json(), {"message": "Backend TAI funcionando"})


class RegistroTests(TestCase):
    def test_registro_correcto(self):
        respuesta = self.client.post('/api/usuarios/registro/', {
            'username': 'juan',
            'email': 'juan@example.com',
            'password': 'clave12345',
            'rol': 'usuario',
        }, content_type='application/json')

        self.assertEqual(respuesta.status_code, 201)
        self.assertIn('token', respuesta.json())
        self.assertTrue(User.objects.filter(username='juan').exists())
        self.assertTrue(
            Perfil.objects.filter(usuario__username='juan', rol='usuario').exists()
        )

    def test_registro_usuario_duplicado(self):
        User.objects.create_user(username='juan', password='clave12345')

        respuesta = self.client.post('/api/usuarios/registro/', {
            'username': 'juan',
            'email': 'otro@example.com',
            'password': 'otraclave123',
            'rol': 'usuario',
        }, content_type='application/json')

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('username', respuesta.json())
        self.assertEqual(User.objects.filter(username='juan').count(), 1)


class LoginTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='juan', password='clave12345')
        Perfil.objects.create(usuario=self.user, rol='orientador')

    def test_login_correcto(self):
        respuesta = self.client.post('/api/usuarios/login/', {
            'username': 'juan',
            'password': 'clave12345',
        }, content_type='application/json')

        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertIn('token', datos)
        self.assertEqual(datos['rol'], 'orientador')
        self.assertEqual(datos['username'], 'juan')

    def test_login_credenciales_incorrectas(self):
        respuesta = self.client.post('/api/usuarios/login/', {
            'username': 'juan',
            'password': 'incorrecta',
        }, content_type='application/json')

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('non_field_errors', respuesta.json())


class AccesoProtegidoTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='juan', password='clave12345')
        Perfil.objects.create(usuario=self.user, rol='usuario')
        self.token = Token.objects.create(user=self.user)

    def test_acceso_sin_token_es_rechazado(self):
        respuesta = self.client.get('/api/usuarios/yo/')
        self.assertEqual(respuesta.status_code, 401)

    def test_acceso_con_token_valido(self):
        respuesta = self.client.get(
            '/api/usuarios/yo/',
            HTTP_AUTHORIZATION=f'Token {self.token.key}',
        )

        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertEqual(datos['username'], 'juan')
        self.assertEqual(datos['rol'], 'usuario')


class PerfilProfesionalTests(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username='juan', password='clave12345')
        Perfil.objects.create(usuario=self.user_a, rol='usuario')
        self.token_a = Token.objects.create(user=self.user_a)

        self.user_b = User.objects.create_user(username='maria', password='clave12345')
        Perfil.objects.create(usuario=self.user_b, rol='usuario')
        self.token_b = Token.objects.create(user=self.user_b)

    def auth_headers(self, token):
        return {'HTTP_AUTHORIZATION': f'Token {token.key}'}

    def test_acceso_sin_token_es_rechazado(self):
        respuesta = self.client.get('/api/usuarios/perfil-profesional/')
        self.assertEqual(respuesta.status_code, 401)

    def test_get_crea_o_recupera_el_perfil_automaticamente(self):
        self.assertFalse(PerfilProfesional.objects.filter(usuario=self.user_a).exists())

        respuesta = self.client.get(
            '/api/usuarios/perfil-profesional/', **self.auth_headers(self.token_a)
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()['username'], 'juan')
        self.assertTrue(PerfilProfesional.objects.filter(usuario=self.user_a).exists())

    def test_lectura_del_perfil_propio(self):
        PerfilProfesional.objects.create(
            usuario=self.user_a, nombre_completo='Juan Pérez', ciudad='Madrid'
        )

        respuesta = self.client.get(
            '/api/usuarios/perfil-profesional/', **self.auth_headers(self.token_a)
        )

        datos = respuesta.json()
        self.assertEqual(datos['nombre_completo'], 'Juan Pérez')
        self.assertEqual(datos['ciudad'], 'Madrid')

    def test_actualizacion_correcta(self):
        respuesta = self.client.put(
            '/api/usuarios/perfil-profesional/',
            data={
                'nombre_completo': '  Juan Pérez  ',
                'telefono': '+34 912 345 678',
                'ciudad': 'Madrid',
                'estudios': 'Grado en Ingeniería Informática',
                'experiencia': 'Desarrollador backend, 3 años',
                'habilidades': 'Python, Django, React',
            },
            content_type='application/json',
            **self.auth_headers(self.token_a),
        )

        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        # La sanitización básica debe recortar espacios sobrantes
        self.assertEqual(datos['nombre_completo'], 'Juan Pérez')

        perfil = PerfilProfesional.objects.get(usuario=self.user_a)
        self.assertEqual(perfil.ciudad, 'Madrid')
        self.assertEqual(perfil.habilidades, 'Python, Django, React')

    def test_usuario_no_accede_al_perfil_de_otro(self):
        PerfilProfesional.objects.create(
            usuario=self.user_a, nombre_completo='Juan Pérez'
        )
        PerfilProfesional.objects.create(
            usuario=self.user_b, nombre_completo='María López'
        )

        respuesta_a = self.client.get(
            '/api/usuarios/perfil-profesional/', **self.auth_headers(self.token_a)
        )
        respuesta_b = self.client.get(
            '/api/usuarios/perfil-profesional/', **self.auth_headers(self.token_b)
        )

        self.assertEqual(respuesta_a.json()['nombre_completo'], 'Juan Pérez')
        self.assertEqual(respuesta_b.json()['nombre_completo'], 'María López')

        # Actualizar como usuario B no debe afectar al perfil de A
        self.client.put(
            '/api/usuarios/perfil-profesional/',
            data={'nombre_completo': 'María Modificada'},
            content_type='application/json',
            **self.auth_headers(self.token_b),
        )
        perfil_a = PerfilProfesional.objects.get(usuario=self.user_a)
        self.assertEqual(perfil_a.nombre_completo, 'Juan Pérez')

    def test_telefono_con_caracteres_no_permitidos_es_rechazado(self):
        respuesta = self.client.put(
            '/api/usuarios/perfil-profesional/',
            data={'telefono': 'llámame ya!!'},
            content_type='application/json',
            **self.auth_headers(self.token_a),
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('telefono', respuesta.json())

    def test_estudios_supera_longitud_maxima_es_rechazado(self):
        respuesta = self.client.put(
            '/api/usuarios/perfil-profesional/',
            data={'estudios': 'x' * 2001},
            content_type='application/json',
            **self.auth_headers(self.token_a),
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('estudios', respuesta.json())


class FakePerfil:
    """Objeto mínimo con los mismos atributos que PerfilProfesional, sin tocar la BD."""

    def __init__(self, **kwargs):
        for campo in ('nombre_completo', 'telefono', 'ciudad', 'estudios', 'experiencia', 'habilidades'):
            setattr(self, campo, kwargs.get(campo, ''))


class CalcularPuntuacionTests(SimpleTestCase):
    def test_puntuacion_perfil_vacio_es_cero(self):
        self.assertEqual(calcular_puntuacion(FakePerfil()), 0)

    def test_puntuacion_perfil_completo_es_cien(self):
        perfil = FakePerfil(
            nombre_completo='Juan', telefono='600111222', ciudad='Madrid',
            estudios='Grado', experiencia='3 años', habilidades='Python',
        )
        self.assertEqual(calcular_puntuacion(perfil), 100)

    def test_puntuacion_siempre_entre_0_y_100(self):
        combinaciones = [
            {},
            {'nombre_completo': 'Juan'},
            {'nombre_completo': 'Juan', 'telefono': '600111222'},
            {'nombre_completo': 'Juan', 'telefono': '600111222', 'ciudad': 'Madrid'},
        ]
        for datos in combinaciones:
            puntuacion = calcular_puntuacion(FakePerfil(**datos))
            self.assertGreaterEqual(puntuacion, 0)
            self.assertLessEqual(puntuacion, 100)


class AnalisisPerfilLegacyTests(TestCase):
    """Endpoint heredado de la Fase 4 (`GET /analisis-perfil/`), se mantiene
    para no romper enlaces existentes: análisis por reglas sin persistir."""

    def setUp(self):
        self.user = User.objects.create_user(username='juan', password='clave12345')
        Perfil.objects.create(usuario=self.user, rol='usuario')
        self.token = Token.objects.create(user=self.user)

    def test_acceso_sin_token_es_rechazado(self):
        respuesta = self.client.get('/api/usuarios/analisis-perfil/')
        self.assertEqual(respuesta.status_code, 401)

    def test_analisis_perfil_devuelve_resultado_por_reglas(self):
        respuesta = self.client.get(
            '/api/usuarios/analisis-perfil/',
            HTTP_AUTHORIZATION=f'Token {self.token.key}',
        )
        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertIn('resumen', datos)
        self.assertIn('fortalezas', datos)
        self.assertIn('aspectos_mejora', datos)
        self.assertIn('recomendaciones', datos)


class AnalisisTests(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username='juan', password='clave12345')
        Perfil.objects.create(usuario=self.user_a, rol='usuario')
        self.token_a = Token.objects.create(user=self.user_a)

        self.user_b = User.objects.create_user(username='maria', password='clave12345')
        Perfil.objects.create(usuario=self.user_b, rol='usuario')
        self.token_b = Token.objects.create(user=self.user_b)

    def auth_headers(self, token):
        return {'HTTP_AUTHORIZATION': f'Token {token.key}'}

    def test_acceso_sin_token_es_rechazado(self):
        self.assertEqual(self.client.post('/api/usuarios/analisis/generar/').status_code, 401)
        self.assertEqual(self.client.get('/api/usuarios/analisis/ultimo/').status_code, 401)
        self.assertEqual(self.client.get('/api/usuarios/analisis/historial/').status_code, 401)

    def test_generar_analisis_con_perfil_vacio(self):
        respuesta = self.client.post(
            '/api/usuarios/analisis/generar/', **self.auth_headers(self.token_a)
        )

        self.assertEqual(respuesta.status_code, 201)
        datos = respuesta.json()
        self.assertEqual(datos['puntuacion_completitud'], 0)
        self.assertEqual(datos['fortalezas'], [])
        self.assertGreater(len(datos['aspectos_mejora']), 0)
        self.assertGreater(len(datos['recomendaciones']), 0)
        self.assertTrue(datos['resumen'])

    def test_generar_analisis_con_perfil_completo(self):
        PerfilProfesional.objects.create(
            usuario=self.user_a,
            nombre_completo='Juan Pérez',
            telefono='600111222',
            ciudad='Madrid',
            estudios='Grado en Ingeniería Informática',
            experiencia=(
                'Desarrollador backend durante 3 años en distintas empresas, '
                'liderando proyectos con Django y PostgreSQL.'
            ),
            habilidades='Python, Django, PostgreSQL, Docker, Git',
        )

        respuesta = self.client.post(
            '/api/usuarios/analisis/generar/', **self.auth_headers(self.token_a)
        )

        datos = respuesta.json()
        self.assertEqual(datos['puntuacion_completitud'], 100)
        self.assertEqual(datos['aspectos_mejora'], [])
        self.assertGreater(len(datos['fortalezas']), 0)

    def test_analisis_solo_usa_el_perfil_del_usuario_autenticado(self):
        PerfilProfesional.objects.create(
            usuario=self.user_a, nombre_completo='Juan Pérez', ciudad='Madrid'
        )
        # user_b no tiene perfil relleno todavía

        respuesta_b = self.client.post(
            '/api/usuarios/analisis/generar/', **self.auth_headers(self.token_b)
        )

        self.assertEqual(respuesta_b.json()['puntuacion_completitud'], 0)

    def test_persistencia_del_analisis(self):
        self.client.post('/api/usuarios/analisis/generar/', **self.auth_headers(self.token_a))
        self.assertEqual(
            ResultadoAnalisis.objects.filter(usuario=self.user_a).count(), 1
        )

    def test_aislamiento_entre_usuarios(self):
        self.client.post('/api/usuarios/analisis/generar/', **self.auth_headers(self.token_a))

        respuesta_b = self.client.get(
            '/api/usuarios/analisis/ultimo/', **self.auth_headers(self.token_b)
        )
        self.assertEqual(respuesta_b.status_code, 404)

        historial_b = self.client.get(
            '/api/usuarios/analisis/historial/', **self.auth_headers(self.token_b)
        )
        self.assertEqual(historial_b.json(), [])

    def test_ultimo_analisis_sin_resultados_devuelve_404(self):
        respuesta = self.client.get(
            '/api/usuarios/analisis/ultimo/', **self.auth_headers(self.token_a)
        )
        self.assertEqual(respuesta.status_code, 404)

    def test_ultimo_analisis_devuelve_el_mas_reciente(self):
        primero = self.client.post(
            '/api/usuarios/analisis/generar/', **self.auth_headers(self.token_a)
        ).json()

        segundo = self.client.post(
            '/api/usuarios/analisis/generar/', **self.auth_headers(self.token_a)
        ).json()

        ultimo = self.client.get(
            '/api/usuarios/analisis/ultimo/', **self.auth_headers(self.token_a)
        ).json()

        self.assertNotEqual(primero['id'], segundo['id'])
        self.assertEqual(ultimo['id'], segundo['id'])

    def test_historial_ordenado_por_fecha_descendente(self):
        for _ in range(3):
            self.client.post('/api/usuarios/analisis/generar/', **self.auth_headers(self.token_a))

        historial = self.client.get(
            '/api/usuarios/analisis/historial/', **self.auth_headers(self.token_a)
        ).json()

        ids = [item['id'] for item in historial]
        self.assertEqual(ids, sorted(ids, reverse=True))


TEMP_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class CurriculumTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.user_a = User.objects.create_user(username='juan', password='clave12345')
        Perfil.objects.create(usuario=self.user_a, rol='usuario')
        self.token_a = Token.objects.create(user=self.user_a)

        self.user_b = User.objects.create_user(username='maria', password='clave12345')
        Perfil.objects.create(usuario=self.user_b, rol='usuario')
        self.token_b = Token.objects.create(user=self.user_b)

    def auth_headers(self, token):
        return {'HTTP_AUTHORIZATION': f'Token {token.key}'}

    def pdf_con_contenido(self, nombre='cv.pdf'):
        contenido = crear_pdf([
            "Juan Perez",
            "contacto: juan@example.com telefono 600111222",
            "Experiencia profesional",
            "Desarrollador backend durante 3 anios con Python y Django",
            "Formacion academica",
            "Grado en Ingenieria Informatica",
            "Habilidades",
            "Python, Django, Docker, Git",
        ])
        return SimpleUploadedFile(nombre, contenido, content_type='application/pdf')

    def test_acceso_sin_token_es_rechazado(self):
        self.assertEqual(self.client.post('/api/usuarios/cv/subir/').status_code, 401)
        self.assertEqual(self.client.get('/api/usuarios/cv/ultimo/').status_code, 401)
        self.assertEqual(self.client.get('/api/usuarios/cv/historial/').status_code, 401)

    def test_subida_correcta(self):
        respuesta = self.client.post(
            '/api/usuarios/cv/subir/',
            {'archivo': self.pdf_con_contenido()},
            **self.auth_headers(self.token_a),
        )

        self.assertEqual(respuesta.status_code, 201)
        datos = respuesta.json()
        self.assertEqual(datos['nombre_archivo'], 'cv.pdf')
        self.assertTrue(Curriculum.objects.filter(usuario=self.user_a).exists())

    def test_rechazo_archivo_no_pdf(self):
        archivo = SimpleUploadedFile(
            'cv.txt', b'esto no es un pdf', content_type='text/plain'
        )

        respuesta = self.client.post(
            '/api/usuarios/cv/subir/',
            {'archivo': archivo},
            **self.auth_headers(self.token_a),
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('archivo', respuesta.json())
        self.assertFalse(Curriculum.objects.filter(usuario=self.user_a).exists())

    def test_rechazo_pdf_falso_con_extension_correcta(self):
        # Extensión .pdf pero contenido no válido: debe rechazarse igualmente.
        archivo = SimpleUploadedFile(
            'falso.pdf', b'esto no es un pdf real', content_type='application/pdf'
        )

        respuesta = self.client.post(
            '/api/usuarios/cv/subir/',
            {'archivo': archivo},
            **self.auth_headers(self.token_a),
        )

        self.assertEqual(respuesta.status_code, 400)

    def test_archivo_obligatorio(self):
        respuesta = self.client.post(
            '/api/usuarios/cv/subir/', {}, **self.auth_headers(self.token_a)
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('archivo', respuesta.json())

    def test_archivo_supera_tamano_maximo_es_rechazado(self):
        contenido_grande = b'%PDF-1.4\n' + b'0' * (6 * 1024 * 1024)
        archivo = SimpleUploadedFile(
            'grande.pdf', contenido_grande, content_type='application/pdf'
        )

        respuesta = self.client.post(
            '/api/usuarios/cv/subir/',
            {'archivo': archivo},
            **self.auth_headers(self.token_a),
        )

        self.assertEqual(respuesta.status_code, 400)

    def test_extraccion_de_texto(self):
        respuesta = self.client.post(
            '/api/usuarios/cv/subir/',
            {'archivo': self.pdf_con_contenido()},
            **self.auth_headers(self.token_a),
        )

        curriculum = Curriculum.objects.get(usuario=self.user_a)
        self.assertIn('Experiencia profesional', curriculum.texto_extraido)
        self.assertIn('Python', curriculum.texto_extraido)
        self.assertEqual(respuesta.json()['texto_extraido'], curriculum.texto_extraido)

    def test_pdf_sin_texto_no_inventa_contenido(self):
        archivo = SimpleUploadedFile(
            'escaneado.pdf', crear_pdf(), content_type='application/pdf'
        )

        respuesta = self.client.post(
            '/api/usuarios/cv/subir/',
            {'archivo': archivo},
            **self.auth_headers(self.token_a),
        )

        self.assertEqual(respuesta.status_code, 201)
        datos = respuesta.json()
        self.assertEqual(datos['texto_extraido'], '')
        self.assertEqual(datos['puntuacion'], 0)
        self.assertEqual(datos['fortalezas'], [])
        self.assertGreater(len(datos['debilidades']), 0)

    def test_creacion_del_analisis(self):
        respuesta = self.client.post(
            '/api/usuarios/cv/subir/',
            {'archivo': self.pdf_con_contenido()},
            **self.auth_headers(self.token_a),
        )

        datos = respuesta.json()
        self.assertGreater(datos['puntuacion'], 0)
        self.assertLessEqual(datos['puntuacion'], 100)
        self.assertGreater(len(datos['fortalezas']), 0)
        self.assertGreater(len(datos['recomendaciones']), 0)
        self.assertTrue(datos['resumen'])

    def test_historial(self):
        for _ in range(3):
            self.client.post(
                '/api/usuarios/cv/subir/',
                {'archivo': self.pdf_con_contenido()},
                **self.auth_headers(self.token_a),
            )

        respuesta = self.client.get(
            '/api/usuarios/cv/historial/', **self.auth_headers(self.token_a)
        )

        historial = respuesta.json()
        self.assertEqual(len(historial), 3)
        ids = [item['id'] for item in historial]
        self.assertEqual(ids, sorted(ids, reverse=True))

    def test_ultimo_cv_sin_subidas_devuelve_404(self):
        respuesta = self.client.get(
            '/api/usuarios/cv/ultimo/', **self.auth_headers(self.token_a)
        )
        self.assertEqual(respuesta.status_code, 404)

    def test_aislamiento_entre_usuarios(self):
        self.client.post(
            '/api/usuarios/cv/subir/',
            {'archivo': self.pdf_con_contenido()},
            **self.auth_headers(self.token_a),
        )

        respuesta_b = self.client.get(
            '/api/usuarios/cv/ultimo/', **self.auth_headers(self.token_b)
        )
        self.assertEqual(respuesta_b.status_code, 404)

        historial_b = self.client.get(
            '/api/usuarios/cv/historial/', **self.auth_headers(self.token_b)
        )
        self.assertEqual(historial_b.json(), [])


class ComparadorOfertaTests(SimpleTestCase):
    """Tests unitarios del motor de reglas, sin BD (usuarios/comparador.py)."""

    def test_comparar_habilidades_coincidentes_y_faltantes(self):
        coincidentes, faltantes = comparar_habilidades(
            "Python, Django, Docker, React",
            "Experiencia con Python y Django en proyectos web",
        )
        self.assertEqual(coincidentes, ['django', 'python'])
        self.assertEqual(faltantes, ['docker', 'react'])

    def test_evaluar_experiencia_compatible_por_anios(self):
        self.assertTrue(
            evaluar_experiencia("3 años de experiencia", "5 años como desarrollador backend")
        )

    def test_evaluar_experiencia_incompatible_por_anios(self):
        self.assertFalse(
            evaluar_experiencia("5 años de experiencia", "1 año como becario")
        )

    def test_evaluar_experiencia_sin_requisito_es_compatible(self):
        self.assertTrue(evaluar_experiencia("", "cualquier experiencia"))

    def test_evaluar_experiencia_sin_candidato_es_incompatible(self):
        self.assertFalse(evaluar_experiencia("3 años", ""))

    def test_evaluar_experiencia_sin_numero_usa_longitud_del_contenido(self):
        experiencia_larga = "Desarrollador backend " * 10
        self.assertTrue(evaluar_experiencia("Experiencia demostrable", experiencia_larga))
        self.assertFalse(evaluar_experiencia("Experiencia demostrable", "poca cosa"))

    def test_evaluar_estudios_compatible(self):
        self.assertTrue(
            evaluar_estudios("Grado en Informática", "Grado en Ingeniería Informática")
        )

    def test_evaluar_estudios_incompatible(self):
        self.assertFalse(
            evaluar_estudios("Doctorado en Física Cuántica", "Grado en Marketing")
        )

    def test_evaluar_estudios_sin_requisito_es_compatible(self):
        self.assertTrue(evaluar_estudios("", "Grado en Informática"))

    def test_calcular_porcentaje_match_maximo(self):
        porcentaje = calcular_porcentaje_match(
            habilidades_coincidentes=['python', 'django'],
            habilidades_faltantes=[],
            experiencia_compatible=True,
            estudios_compatibles=True,
            palabras_clave_coincidentes=['a', 'b', 'c', 'd', 'e'],
        )
        self.assertEqual(porcentaje, 100)

    def test_calcular_porcentaje_match_minimo(self):
        porcentaje = calcular_porcentaje_match(
            habilidades_coincidentes=[],
            habilidades_faltantes=['python', 'django'],
            experiencia_compatible=False,
            estudios_compatibles=False,
            palabras_clave_coincidentes=[],
        )
        self.assertEqual(porcentaje, 0)

    def test_calcular_porcentaje_match_siempre_entre_0_y_100(self):
        combinaciones = [
            ([], [], True, True, []),
            (['python'], ['react', 'docker'], False, True, ['a']),
            (['python', 'django', 'docker'], [], True, False, ['a', 'b', 'c', 'd', 'e', 'f']),
        ]
        for coincidentes, faltantes, exp, edu, palabras in combinaciones:
            porcentaje = calcular_porcentaje_match(coincidentes, faltantes, exp, edu, palabras)
            self.assertGreaterEqual(porcentaje, 0)
            self.assertLessEqual(porcentaje, 100)

    def test_clasificar_match_umbrales(self):
        self.assertEqual(clasificar_match(90), "Excelente")
        self.assertEqual(clasificar_match(89), "Muy buena")
        self.assertEqual(clasificar_match(75), "Muy buena")
        self.assertEqual(clasificar_match(74), "Buena")
        self.assertEqual(clasificar_match(55), "Buena")
        self.assertEqual(clasificar_match(54), "Mejorable")
        self.assertEqual(clasificar_match(35), "Mejorable")
        self.assertEqual(clasificar_match(34), "Insuficiente")
        self.assertEqual(clasificar_match(0), "Insuficiente")

    def test_comparar_oferta_completo(self):
        oferta = DatosOferta(
            habilidades="Python, Django, Docker",
            experiencia_requerida="2 años",
            estudios_requeridos="Grado en Informática",
            descripcion="Buscamos desarrollador backend con Python y Django",
            requisitos="Experiencia con bases de datos SQL",
        )
        candidato = DatosCandidato(
            habilidades="Python, Django, Git",
            experiencia="3 años como desarrollador backend con Python y Django",
            estudios="Grado en Ingeniería Informática",
            texto_cv="Desarrollador backend con experiencia en Python, Django y SQL",
        )

        resultado = comparar_oferta(oferta, candidato)

        self.assertIn('python', resultado['habilidades_coincidentes'])
        self.assertIn('django', resultado['habilidades_coincidentes'])
        self.assertIn('docker', resultado['habilidades_faltantes'])
        self.assertTrue(resultado['experiencia_compatible'])
        self.assertTrue(resultado['estudios_compatibles'])
        self.assertGreaterEqual(resultado['porcentaje_match'], 0)
        self.assertLessEqual(resultado['porcentaje_match'], 100)
        self.assertIn(resultado['clasificacion'], [
            'Excelente', 'Muy buena', 'Buena', 'Mejorable', 'Insuficiente'
        ])

    def test_comparar_oferta_sin_cv_recomienda_subirlo(self):
        oferta = DatosOferta(habilidades="Python")
        candidato = DatosCandidato(habilidades="Python", texto_cv="")

        resultado = comparar_oferta(oferta, candidato)

        self.assertTrue(
            any('Sube tu CV' in r for r in resultado['recomendaciones'])
        )

    def test_comparar_oferta_habilidad_faltante_genera_recomendacion(self):
        oferta = DatosOferta(habilidades="Docker")
        candidato = DatosCandidato(habilidades="Python")

        resultado = comparar_oferta(oferta, candidato)

        self.assertIn("Aprender docker.", resultado['recomendaciones'])


class OfertaTests(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username='juan', password='clave12345')
        Perfil.objects.create(usuario=self.user_a, rol='usuario')
        self.token_a = Token.objects.create(user=self.user_a)

        self.user_b = User.objects.create_user(username='maria', password='clave12345')
        Perfil.objects.create(usuario=self.user_b, rol='usuario')
        self.token_b = Token.objects.create(user=self.user_b)

    def auth_headers(self, token):
        return {'HTTP_AUTHORIZATION': f'Token {token.key}'}

    def oferta_valida(self, **overrides):
        datos = {
            'titulo_puesto': 'Desarrollador Backend',
            'empresa': 'TechCorp',
            'ubicacion': 'Madrid',
            'descripcion': 'Buscamos desarrollador backend con experiencia en Python y Django.',
            'requisitos': 'Experiencia con bases de datos relacionales.',
            'habilidades': 'Python, Django, Docker',
            'estudios_requeridos': 'Grado en Informática',
            'experiencia_requerida': '2 años',
        }
        datos.update(overrides)
        return datos

    def test_acceso_sin_token_es_rechazado(self):
        self.assertEqual(
            self.client.post('/api/usuarios/ofertas/crear/', {}, content_type='application/json').status_code,
            401,
        )
        self.assertEqual(self.client.get('/api/usuarios/ofertas/historial/').status_code, 401)

    def test_titulo_puesto_obligatorio(self):
        respuesta = self.client.post(
            '/api/usuarios/ofertas/crear/',
            self.oferta_valida(titulo_puesto=''),
            content_type='application/json',
            **self.auth_headers(self.token_a),
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('titulo_puesto', respuesta.json())

    def test_empresa_obligatoria(self):
        respuesta = self.client.post(
            '/api/usuarios/ofertas/crear/',
            self.oferta_valida(empresa='   '),
            content_type='application/json',
            **self.auth_headers(self.token_a),
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('empresa', respuesta.json())

    def test_descripcion_obligatoria(self):
        respuesta = self.client.post(
            '/api/usuarios/ofertas/crear/',
            self.oferta_valida(descripcion=''),
            content_type='application/json',
            **self.auth_headers(self.token_a),
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('descripcion', respuesta.json())

    def test_crear_oferta_valida_persiste_y_compara(self):
        PerfilProfesional.objects.create(
            usuario=self.user_a,
            experiencia='3 años como desarrollador backend con Python y Django',
            estudios='Grado en Ingeniería Informática',
            habilidades='Python, Django, Git',
        )

        respuesta = self.client.post(
            '/api/usuarios/ofertas/crear/',
            self.oferta_valida(),
            content_type='application/json',
            **self.auth_headers(self.token_a),
        )

        self.assertEqual(respuesta.status_code, 201)
        datos = respuesta.json()
        self.assertIn('python', datos['habilidades_coincidentes'])
        self.assertIn('docker', datos['habilidades_faltantes'])
        self.assertTrue(datos['experiencia_compatible'])
        self.assertTrue(datos['estudios_compatibles'])
        self.assertGreaterEqual(datos['porcentaje_match'], 0)
        self.assertLessEqual(datos['porcentaje_match'], 100)
        self.assertTrue(datos['clasificacion'])
        self.assertTrue(Oferta.objects.filter(usuario=self.user_a).exists())

    def test_comparacion_sin_perfil_ni_cv_no_falla(self):
        respuesta = self.client.post(
            '/api/usuarios/ofertas/crear/',
            self.oferta_valida(),
            content_type='application/json',
            **self.auth_headers(self.token_a),
        )

        self.assertEqual(respuesta.status_code, 201)
        datos = respuesta.json()
        self.assertEqual(datos['habilidades_coincidentes'], [])
        self.assertGreater(len(datos['recomendaciones']), 0)

    def test_historial_ordenado_por_fecha_descendente(self):
        for i in range(3):
            self.client.post(
                '/api/usuarios/ofertas/crear/',
                self.oferta_valida(titulo_puesto=f'Puesto {i}'),
                content_type='application/json',
                **self.auth_headers(self.token_a),
            )

        historial = self.client.get(
            '/api/usuarios/ofertas/historial/', **self.auth_headers(self.token_a)
        ).json()

        ids = [item['id'] for item in historial]
        self.assertEqual(len(ids), 3)
        self.assertEqual(ids, sorted(ids, reverse=True))

    def test_aislamiento_entre_usuarios(self):
        self.client.post(
            '/api/usuarios/ofertas/crear/',
            self.oferta_valida(),
            content_type='application/json',
            **self.auth_headers(self.token_a),
        )

        historial_b = self.client.get(
            '/api/usuarios/ofertas/historial/', **self.auth_headers(self.token_b)
        )
        self.assertEqual(historial_b.json(), [])


class OptimizadorLinkedInTests(SimpleTestCase):
    """Tests unitarios del motor de reglas, sin BD (usuarios/optimizador_linkedin.py)."""

    def test_evaluar_titular_vacio(self):
        puntos, fortalezas, debilidades, recomendaciones = li.evaluar_titular('', '')
        self.assertEqual(puntos, 0)
        self.assertEqual(fortalezas, [])
        self.assertGreater(len(debilidades), 0)
        self.assertGreater(len(recomendaciones), 0)

    def test_evaluar_titular_completo_con_keywords(self):
        puntos, fortalezas, debilidades, recomendaciones = li.evaluar_titular(
            'Desarrollador Backend con Python y Django', ''
        )
        self.assertEqual(puntos, 15)
        self.assertEqual(len(fortalezas), 2)
        self.assertEqual(debilidades, [])

    def test_evaluar_extracto_niveles(self):
        corto, *_ = li.evaluar_extracto('Breve descripción.')
        medio, *_ = li.evaluar_extracto('palabra ' * 80)
        largo, *_ = li.evaluar_extracto('palabra ' * 160)

        self.assertEqual(corto, 0)
        self.assertEqual(medio, 12)
        self.assertEqual(largo, 20)

    def test_evaluar_palabras_clave_niveles(self):
        sin_keywords, *_ = li.evaluar_palabras_clave('perfil profesional sin tecnologías')
        pocas, *_ = li.evaluar_palabras_clave('Trabajo con Python')
        muchas, *_ = li.evaluar_palabras_clave('Python, Django, React, TypeScript, Docker')

        self.assertEqual(sin_keywords, 0)
        self.assertEqual(pocas, 8)
        self.assertEqual(muchas, 15)

    def test_evaluar_habilidades(self):
        vacio, *_ = li.evaluar_habilidades('')
        sin_keywords, *_ = li.evaluar_habilidades('Trabajo en equipo, comunicación')
        con_keywords, *_ = li.evaluar_habilidades('Python, Django, Git')

        self.assertEqual(vacio, 0)
        self.assertEqual(sin_keywords, 5)
        self.assertEqual(con_keywords, 15)

    def test_evaluar_experiencia(self):
        vacio, *_ = li.evaluar_experiencia('')
        breve, *_ = li.evaluar_experiencia('Becario 3 meses.')
        detallada, *_ = li.evaluar_experiencia('Desarrollador backend ' * 10)

        self.assertEqual(vacio, 0)
        self.assertEqual(breve, 7)
        self.assertEqual(detallada, 15)

    def test_evaluar_estudios(self):
        vacio, *_ = li.evaluar_estudios('')
        con_texto, *_ = li.evaluar_estudios('Grado en Ingeniería Informática')

        self.assertEqual(vacio, 0)
        self.assertEqual(con_texto, 10)

    def test_evaluar_coherencia_perfil_sin_perfil_no_penaliza(self):
        puntos, fortalezas, debilidades, recomendaciones = li.evaluar_coherencia_perfil(
            'Python Django', ''
        )
        self.assertEqual(puntos, 5)
        self.assertEqual(debilidades, [])

    def test_evaluar_coherencia_perfil_coincide(self):
        puntos, fortalezas, debilidades, recomendaciones = li.evaluar_coherencia_perfil(
            'Desarrollador con experiencia en Python', 'Experiencia en Python y Django'
        )
        self.assertEqual(puntos, 5)
        self.assertGreater(len(fortalezas), 0)

    def test_evaluar_coherencia_perfil_no_coincide(self):
        puntos, fortalezas, debilidades, recomendaciones = li.evaluar_coherencia_perfil(
            'Diseñador gráfico creativo', 'Contable con experiencia fiscal'
        )
        self.assertEqual(puntos, 0)
        self.assertGreater(len(debilidades), 0)

    def test_evaluar_coherencia_cv_sin_cv_no_penaliza(self):
        puntos, fortalezas, debilidades, recomendaciones = li.evaluar_coherencia_cv(
            'Python Django', ''
        )
        self.assertEqual(puntos, 5)
        self.assertEqual(debilidades, [])

    def test_generar_titular_optimizado_con_datos_reales(self):
        datos = li.DatosLinkedIn(
            titular_actual='Desarrollador Full Stack',
            habilidades='Python, Django, React, TypeScript',
        )
        contexto = li.DatosContexto()

        titular = li.generar_titular_optimizado(datos, contexto)

        self.assertIn('Desarrollador Full Stack', titular)
        self.assertIn('Django', titular)
        self.assertIn('React', titular)
        self.assertIn('Desarrollo Web', titular)

    def test_generar_titular_optimizado_sin_datos_devuelve_vacio(self):
        titular = li.generar_titular_optimizado(li.DatosLinkedIn(), li.DatosContexto())
        self.assertEqual(titular, '')

    def test_generar_titular_optimizado_no_inventa_tecnologias(self):
        datos = li.DatosLinkedIn(titular_actual='Analista de datos', habilidades='Python')
        contexto = li.DatosContexto()

        titular = li.generar_titular_optimizado(datos, contexto)

        self.assertNotIn('React', titular)
        self.assertNotIn('Docker', titular)
        self.assertNotIn('Django', titular)

    def test_optimizar_linkedin_completo(self):
        datos = li.DatosLinkedIn(
            titular_actual='Desarrollador Backend',
            extracto='Desarrollador backend con experiencia en Python y Django. ' * 10,
            experiencia='Desarrollador en TechCorp durante 3 años trabajando con Python y Django. ' * 2,
            estudios='Grado en Ingeniería Informática',
            habilidades='Python, Django, SQL, Git',
        )
        contexto = li.DatosContexto(
            perfil_experiencia='Desarrollador backend con Python',
            perfil_estudios='Grado en Ingeniería Informática',
            perfil_habilidades='Python, Django',
            texto_cv='Desarrollador backend con experiencia en Python y Django',
        )

        resultado = li.optimizar_linkedin(datos, contexto)

        self.assertGreaterEqual(resultado['puntuacion'], 0)
        self.assertLessEqual(resultado['puntuacion'], 100)
        self.assertIn(resultado['clasificacion'], [
            'Excelente', 'Muy buena', 'Buena', 'Mejorable', 'Insuficiente'
        ])
        self.assertTrue(resultado['titular_optimizado'])
        self.assertGreater(len(resultado['fortalezas']), 0)

    def test_optimizar_linkedin_sin_contexto_no_falla(self):
        datos = li.DatosLinkedIn(extracto='Breve extracto de prueba.')
        contexto = li.DatosContexto()

        resultado = li.optimizar_linkedin(datos, contexto)

        self.assertGreaterEqual(resultado['puntuacion'], 0)
        self.assertLessEqual(resultado['puntuacion'], 100)
        self.assertGreater(len(resultado['plan_mejora']), 0)


class OptimizacionLinkedInTests(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username='juan', password='clave12345')
        Perfil.objects.create(usuario=self.user_a, rol='usuario')
        self.token_a = Token.objects.create(user=self.user_a)

        self.user_b = User.objects.create_user(username='maria', password='clave12345')
        Perfil.objects.create(usuario=self.user_b, rol='usuario')
        self.token_b = Token.objects.create(user=self.user_b)

    def auth_headers(self, token):
        return {'HTTP_AUTHORIZATION': f'Token {token.key}'}

    def datos_validos(self, **overrides):
        datos = {
            'titular_actual': 'Desarrollador Backend',
            'extracto': 'Desarrollador backend con experiencia en Python y Django. ' * 10,
            'experiencia': 'Desarrollador en TechCorp durante 3 años. ' * 5,
            'estudios': 'Grado en Ingeniería Informática',
            'habilidades': 'Python, Django, SQL, Git',
        }
        datos.update(overrides)
        return datos

    def test_acceso_sin_token_es_rechazado(self):
        self.assertEqual(
            self.client.post(
                '/api/usuarios/linkedin/crear/', {}, content_type='application/json'
            ).status_code,
            401,
        )
        self.assertEqual(self.client.get('/api/usuarios/linkedin/historial/').status_code, 401)

    def test_extracto_obligatorio(self):
        respuesta = self.client.post(
            '/api/usuarios/linkedin/crear/',
            self.datos_validos(extracto=''),
            content_type='application/json',
            **self.auth_headers(self.token_a),
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('extracto', respuesta.json())

    def test_crear_optimizacion_valida_persiste(self):
        respuesta = self.client.post(
            '/api/usuarios/linkedin/crear/',
            self.datos_validos(),
            content_type='application/json',
            **self.auth_headers(self.token_a),
        )

        self.assertEqual(respuesta.status_code, 201)
        datos = respuesta.json()
        self.assertGreaterEqual(datos['puntuacion'], 0)
        self.assertLessEqual(datos['puntuacion'], 100)
        self.assertIn(datos['clasificacion'], [
            'Excelente', 'Muy buena', 'Buena', 'Mejorable', 'Insuficiente'
        ])
        self.assertTrue(datos['titular_optimizado'])
        self.assertTrue(
            OptimizacionLinkedIn.objects.filter(usuario=self.user_a).exists()
        )

    def test_optimizacion_con_perfil_vacio_no_falla(self):
        # El perfil profesional se crea vacío automáticamente (get_or_create)
        respuesta = self.client.post(
            '/api/usuarios/linkedin/crear/',
            self.datos_validos(),
            content_type='application/json',
            **self.auth_headers(self.token_a),
        )
        self.assertEqual(respuesta.status_code, 201)

    def test_optimizacion_sin_cv_no_falla(self):
        # No se sube ningún CV para este usuario
        respuesta = self.client.post(
            '/api/usuarios/linkedin/crear/',
            self.datos_validos(),
            content_type='application/json',
            **self.auth_headers(self.token_a),
        )
        self.assertEqual(respuesta.status_code, 201)

    def test_usuario_no_puede_indicar_propietario(self):
        respuesta = self.client.post(
            '/api/usuarios/linkedin/crear/',
            self.datos_validos(usuario=self.user_b.id),
            content_type='application/json',
            **self.auth_headers(self.token_a),
        )

        self.assertEqual(respuesta.status_code, 201)
        optimizacion = OptimizacionLinkedIn.objects.get(id=respuesta.json()['id'])
        self.assertEqual(optimizacion.usuario, self.user_a)

    def test_historial_ordenado_por_fecha_descendente(self):
        for i in range(3):
            self.client.post(
                '/api/usuarios/linkedin/crear/',
                self.datos_validos(titular_actual=f'Titular {i}'),
                content_type='application/json',
                **self.auth_headers(self.token_a),
            )

        historial = self.client.get(
            '/api/usuarios/linkedin/historial/', **self.auth_headers(self.token_a)
        ).json()

        ids = [item['id'] for item in historial]
        self.assertEqual(len(ids), 3)
        self.assertEqual(ids, sorted(ids, reverse=True))

    def test_aislamiento_entre_usuarios(self):
        self.client.post(
            '/api/usuarios/linkedin/crear/',
            self.datos_validos(),
            content_type='application/json',
            **self.auth_headers(self.token_a),
        )

        historial_b = self.client.get(
            '/api/usuarios/linkedin/historial/', **self.auth_headers(self.token_b)
        )
        self.assertEqual(historial_b.json(), [])


class EvaluadorEntrevistaTests(SimpleTestCase):
    """Tests unitarios del motor de reglas, sin BD (usuarios/evaluador_entrevista.py)."""

    RESPUESTA_ADECUADA = (
        "En mi experiencia profesional he liderado varios proyectos de desarrollo, "
        "trabajando siempre en equipo con gran responsabilidad y compromiso para "
        "alcanzar los objetivos marcados, mejorando la comunicación y colaboración "
        "con el cliente para lograr resultados de calidad."
    )

    def test_generar_preguntas_genera_los_diez_tipos(self):
        preguntas = ee.generar_preguntas(ee.ContextoEntrevista())
        self.assertEqual(len(preguntas), 10)
        self.assertEqual({p['tipo'] for p in preguntas}, set(ee.TIPOS_PREGUNTA_ORDEN))

    def test_generar_preguntas_orden_correcto(self):
        preguntas = ee.generar_preguntas(ee.ContextoEntrevista())
        self.assertEqual([p['orden'] for p in preguntas], list(range(1, 11)))

    def test_generar_preguntas_se_adapta_a_la_oferta(self):
        contexto = ee.ContextoEntrevista(oferta_empresa='TechCorp', oferta_titulo='Backend Developer')
        preguntas = ee.generar_preguntas(contexto)
        pregunta_motivacion = next(p for p in preguntas if p['tipo'] == 'motivacion')
        self.assertIn('TechCorp', pregunta_motivacion['pregunta'])

    def test_generar_preguntas_sin_contexto_no_falla(self):
        preguntas = ee.generar_preguntas(ee.ContextoEntrevista())
        self.assertEqual(len(preguntas), 10)
        for pregunta in preguntas:
            self.assertTrue(pregunta['pregunta'])

    def test_evaluar_respuesta_vacia(self):
        resultado = ee.evaluar_respuesta('', '')
        self.assertEqual(resultado['puntuacion'], 0)
        self.assertEqual(resultado['estado_longitud'], 'vacia')

    def test_evaluar_respuesta_corta(self):
        resultado = ee.evaluar_respuesta('Trabajo bien en equipo.', '')
        self.assertEqual(resultado['estado_longitud'], 'corta')
        self.assertLess(resultado['puntuacion'], 50)

    def test_evaluar_respuesta_larga(self):
        resultado = ee.evaluar_respuesta('palabra ' * 300, '')
        self.assertEqual(resultado['estado_longitud'], 'larga')

    def test_evaluar_respuesta_adecuada_con_vocabulario(self):
        resultado = ee.evaluar_respuesta(self.RESPUESTA_ADECUADA, '')
        self.assertEqual(resultado['estado_longitud'], 'adecuada')
        self.assertGreaterEqual(len(resultado['vocabulario_profesional']), 3)
        self.assertGreaterEqual(resultado['puntuacion'], 70)

    def test_evaluar_respuesta_puntuacion_siempre_entre_0_y_100(self):
        for respuesta in ('', 'a', 'palabra ' * 400, self.RESPUESTA_ADECUADA):
            resultado = ee.evaluar_respuesta(respuesta, '')
            self.assertGreaterEqual(resultado['puntuacion'], 0)
            self.assertLessEqual(resultado['puntuacion'], 100)

    def test_evaluar_entrevista_resultado_determinista(self):
        respuestas = [
            ee.RespuestaEntrevista(tipo='presentacion', pregunta='p1', respuesta=self.RESPUESTA_ADECUADA, orden=1),
            ee.RespuestaEntrevista(tipo='experiencia', pregunta='p2', respuesta='', orden=2),
        ]
        contexto = ee.ContextoEntrevista(perfil_habilidades='Python, Django')

        resultado1 = ee.evaluar_entrevista(respuestas, contexto)
        resultado2 = ee.evaluar_entrevista(respuestas, contexto)

        self.assertEqual(resultado1, resultado2)

    def test_evaluar_entrevista_puntuacion_y_clasificacion_validas(self):
        respuestas = [
            ee.RespuestaEntrevista(tipo=tipo, pregunta='pregunta', respuesta=self.RESPUESTA_ADECUADA, orden=i)
            for i, tipo in enumerate(ee.TIPOS_PREGUNTA_ORDEN, start=1)
        ]
        resultado = ee.evaluar_entrevista(respuestas, ee.ContextoEntrevista())

        self.assertGreaterEqual(resultado['puntuacion'], 0)
        self.assertLessEqual(resultado['puntuacion'], 100)
        self.assertIn(resultado['clasificacion'], [
            'Excelente', 'Muy buena', 'Buena', 'Mejorable', 'Insuficiente'
        ])

    def test_evaluar_entrevista_respuestas_vacias_genera_recomendaciones(self):
        respuestas = [
            ee.RespuestaEntrevista(tipo='presentacion', pregunta='p', respuesta='', orden=1),
        ]
        resultado = ee.evaluar_entrevista(respuestas, ee.ContextoEntrevista())

        self.assertGreater(len(resultado['aspectos_mejora']), 0)
        self.assertGreater(len(resultado['recomendaciones']), 0)

    def test_coherencia_con_perfil_profesional(self):
        respuestas = [ee.RespuestaEntrevista(
            tipo='habilidades', pregunta='p',
            respuesta='Tengo experiencia con Python y Django en proyectos reales.', orden=1,
        )]
        contexto = ee.ContextoEntrevista(perfil_habilidades='Python, Django')
        resultado = ee.evaluar_entrevista(respuestas, contexto)
        self.assertTrue(any('Perfil Profesional' in f for f in resultado['fortalezas']))

    def test_coherencia_con_cv(self):
        respuestas = [ee.RespuestaEntrevista(
            tipo='habilidades', pregunta='p',
            respuesta='Trabajo con React y TypeScript habitualmente en mi día a día.', orden=1,
        )]
        contexto = ee.ContextoEntrevista(texto_cv='Desarrollador con experiencia en React y TypeScript')
        resultado = ee.evaluar_entrevista(respuestas, contexto)
        self.assertTrue(any('CV analizado' in f for f in resultado['fortalezas']))

    def test_coherencia_con_oferta(self):
        respuestas = [ee.RespuestaEntrevista(
            tipo='motivacion', pregunta='p',
            respuesta='Me interesa mucho el puesto de Backend Developer en esta empresa.', orden=1,
        )]
        contexto = ee.ContextoEntrevista(oferta_titulo='Backend Developer', oferta_empresa='TechCorp')
        resultado = ee.evaluar_entrevista(respuestas, contexto)
        self.assertTrue(any('oferta de empleo' in f for f in resultado['fortalezas']))

    def test_coherencia_con_linkedin(self):
        respuestas = [ee.RespuestaEntrevista(
            tipo='objetivos', pregunta='p',
            respuesta='Mi objetivo es seguir creciendo como desarrollador full stack.', orden=1,
        )]
        contexto = ee.ContextoEntrevista(linkedin_titular='Desarrollador Full Stack')
        resultado = ee.evaluar_entrevista(respuestas, contexto)
        self.assertTrue(any('LinkedIn' in f for f in resultado['fortalezas']))

    def test_coherencia_sin_fuentes_no_penaliza(self):
        respuestas = [ee.RespuestaEntrevista(
            tipo='presentacion', pregunta='p', respuesta=self.RESPUESTA_ADECUADA, orden=1,
        )]
        resultado = ee.evaluar_entrevista(respuestas, ee.ContextoEntrevista())
        # Sin Perfil, CV, Oferta ni LinkedIn con contenido, no debe generarse
        # ninguna recomendación de coherencia (crédito íntegro, no penaliza).
        self.assertFalse(any('coherentes con' in r or 'relacionar tus respuestas' in r
                              for r in resultado['recomendaciones']))


class SimulacionEntrevistaTests(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username='juan', password='clave12345')
        Perfil.objects.create(usuario=self.user_a, rol='usuario')
        self.token_a = Token.objects.create(user=self.user_a)

        self.user_b = User.objects.create_user(username='maria', password='clave12345')
        Perfil.objects.create(usuario=self.user_b, rol='usuario')
        self.token_b = Token.objects.create(user=self.user_b)

    def auth_headers(self, token):
        return {'HTTP_AUTHORIZATION': f'Token {token.key}'}

    def respuestas_validas(self):
        return {
            'respuestas': [
                {
                    'tipo': tipo,
                    'pregunta': f'Pregunta sobre {tipo}',
                    'respuesta': (
                        'Esta es una respuesta de ejemplo con contenido suficiente, '
                        'mostrando responsabilidad, compromiso y trabajo en equipo.'
                    ),
                    'orden': i,
                }
                for i, tipo in enumerate(ee.TIPOS_PREGUNTA_ORDEN, start=1)
            ]
        }

    def test_acceso_sin_token_es_rechazado(self):
        self.assertEqual(self.client.post('/api/usuarios/entrevista/iniciar/').status_code, 401)
        self.assertEqual(
            self.client.post(
                '/api/usuarios/entrevista/finalizar/', {}, content_type='application/json'
            ).status_code,
            401,
        )
        self.assertEqual(self.client.get('/api/usuarios/entrevista/historial/').status_code, 401)

    def test_iniciar_entrevista_genera_diez_preguntas(self):
        respuesta = self.client.post(
            '/api/usuarios/entrevista/iniciar/', **self.auth_headers(self.token_a)
        )
        self.assertEqual(respuesta.status_code, 200)
        preguntas = respuesta.json()['preguntas']
        self.assertEqual(len(preguntas), 10)
        for pregunta in preguntas:
            self.assertIn('tipo', pregunta)
            self.assertIn('pregunta', pregunta)
            self.assertIn('orden', pregunta)

    def test_finalizar_entrevista_requiere_respuestas(self):
        respuesta = self.client.post(
            '/api/usuarios/entrevista/finalizar/',
            {'respuestas': []},
            content_type='application/json',
            **self.auth_headers(self.token_a),
        )
        self.assertEqual(respuesta.status_code, 400)

    def test_finalizar_entrevista_crea_y_persiste(self):
        respuesta = self.client.post(
            '/api/usuarios/entrevista/finalizar/',
            self.respuestas_validas(),
            content_type='application/json',
            **self.auth_headers(self.token_a),
        )

        self.assertEqual(respuesta.status_code, 201)
        datos = respuesta.json()
        self.assertGreaterEqual(datos['puntuacion'], 0)
        self.assertLessEqual(datos['puntuacion'], 100)
        self.assertEqual(len(datos['preguntas']), 10)
        self.assertTrue(SimulacionEntrevista.objects.filter(usuario=self.user_a).exists())
        self.assertEqual(
            PreguntaRespuesta.objects.filter(simulacion__usuario=self.user_a).count(), 10
        )

    def test_usuario_sin_perfil_no_falla(self):
        # PerfilProfesional se crea automáticamente vacío (get_or_create)
        respuesta = self.client.post(
            '/api/usuarios/entrevista/finalizar/',
            self.respuestas_validas(),
            content_type='application/json',
            **self.auth_headers(self.token_a),
        )
        self.assertEqual(respuesta.status_code, 201)

    def test_usuario_sin_cv_no_falla(self):
        # No se ha subido ningún Curriculum para este usuario
        respuesta = self.client.post(
            '/api/usuarios/entrevista/finalizar/',
            self.respuestas_validas(),
            content_type='application/json',
            **self.auth_headers(self.token_a),
        )
        self.assertEqual(respuesta.status_code, 201)

    def test_usuario_sin_oferta_no_falla(self):
        # No se ha comparado ninguna Oferta para este usuario
        respuesta = self.client.post(
            '/api/usuarios/entrevista/finalizar/',
            self.respuestas_validas(),
            content_type='application/json',
            **self.auth_headers(self.token_a),
        )
        self.assertEqual(respuesta.status_code, 201)

    def test_usuario_sin_linkedin_no_falla(self):
        # No existe ninguna OptimizacionLinkedIn para este usuario
        respuesta = self.client.post(
            '/api/usuarios/entrevista/finalizar/',
            self.respuestas_validas(),
            content_type='application/json',
            **self.auth_headers(self.token_a),
        )
        self.assertEqual(respuesta.status_code, 201)

    def test_usuario_no_puede_indicar_propietario(self):
        payload = self.respuestas_validas()
        payload['usuario'] = self.user_b.id

        respuesta = self.client.post(
            '/api/usuarios/entrevista/finalizar/',
            payload,
            content_type='application/json',
            **self.auth_headers(self.token_a),
        )

        self.assertEqual(respuesta.status_code, 201)
        simulacion = SimulacionEntrevista.objects.get(id=respuesta.json()['id'])
        self.assertEqual(simulacion.usuario, self.user_a)

    def test_historial_ordenado_por_fecha_descendente(self):
        for _ in range(3):
            self.client.post(
                '/api/usuarios/entrevista/finalizar/',
                self.respuestas_validas(),
                content_type='application/json',
                **self.auth_headers(self.token_a),
            )

        historial = self.client.get(
            '/api/usuarios/entrevista/historial/', **self.auth_headers(self.token_a)
        ).json()

        ids = [item['id'] for item in historial]
        self.assertEqual(len(ids), 3)
        self.assertEqual(ids, sorted(ids, reverse=True))

    def test_aislamiento_entre_usuarios(self):
        self.client.post(
            '/api/usuarios/entrevista/finalizar/',
            self.respuestas_validas(),
            content_type='application/json',
            **self.auth_headers(self.token_a),
        )

        historial_b = self.client.get(
            '/api/usuarios/entrevista/historial/', **self.auth_headers(self.token_b)
        )
        self.assertEqual(historial_b.json(), [])


# -----------------------------
# Sprint 9 — Integración con OpenAI
# -----------------------------

def _respuesta_openai(contenido):
    """Imita la forma de una respuesta de la API de OpenAI: un objeto con
    .choices[0].message.content igual al texto indicado."""
    mensaje = MagicMock()
    mensaje.content = contenido
    choice = MagicMock()
    choice.message = mensaje
    respuesta = MagicMock()
    respuesta.choices = [choice]
    return respuesta


def _cliente_mock(create_side_effect=None, create_return_value=None):
    """Cliente OpenAI simulado: nunca realiza ninguna llamada de red real."""
    cliente = MagicMock()
    if create_side_effect is not None:
        cliente.chat.completions.create.side_effect = create_side_effect
    else:
        cliente.chat.completions.create.return_value = create_return_value
    return cliente


class OpenAIServiceTests(SimpleTestCase):
    """
    Tests del servicio centralizado openai_service.py: disponibilidad de la
    clave, manejo de todos los errores exigidos por el checklist del
    Sprint 9 y validación estricta de la forma de la respuesta. El cliente
    real de OpenAI se sustituye siempre por un mock: estos tests no
    realizan ninguna llamada de red.
    """

    def setUp(self):
        self.perfil = PerfilProfesional(
            nombre_completo='Ana Pérez',
            telefono='600111222',
            ciudad='Madrid',
            estudios='Grado en Ingeniería Informática',
            experiencia='3 años como desarrolladora backend en Django.',
            habilidades='Python, Django, SQL',
        )
        self.resultado_reglas_perfil = analizar_perfil(self.perfil)
        self.resultado_reglas_perfil['puntuacion_completitud'] = calcular_puntuacion(self.perfil)

    # --- disponibilidad ---

    def test_no_disponible_sin_clave(self):
        with patch.dict('os.environ', {'OPENAI_API_KEY': ''}, clear=False):
            self.assertFalse(openai_service.openai_disponible())

    def test_disponible_con_clave(self):
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'sk-test'}, clear=False):
            self.assertTrue(openai_service.openai_disponible())

    def test_analizar_perfil_clave_ausente_devuelve_none(self):
        with patch.dict('os.environ', {'OPENAI_API_KEY': ''}, clear=False):
            resultado = openai_service.analizar_perfil(self.perfil, self.resultado_reglas_perfil)
        self.assertIsNone(resultado)

    # --- respuestas válidas / inválidas ---

    def test_analizar_perfil_respuesta_valida(self):
        contenido = json.dumps({
            "resumen": "Resumen generado por IA.",
            "fortalezas": ["Fortaleza IA 1"],
            "aspectos_mejora": ["Aspecto IA 1"],
            "recomendaciones": ["Recomendación IA 1"],
        })
        cliente = _cliente_mock(create_return_value=_respuesta_openai(contenido))

        with patch.dict('os.environ', {'OPENAI_API_KEY': 'sk-test'}, clear=False), \
                patch.object(openai_service, '_cliente', return_value=cliente):
            resultado = openai_service.analizar_perfil(self.perfil, self.resultado_reglas_perfil)

        self.assertEqual(resultado, {
            "resumen": "Resumen generado por IA.",
            "fortalezas": ["Fortaleza IA 1"],
            "aspectos_mejora": ["Aspecto IA 1"],
            "recomendaciones": ["Recomendación IA 1"],
        })

    def test_respuesta_json_invalido(self):
        cliente = _cliente_mock(create_return_value=_respuesta_openai("esto no es json"))
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'sk-test'}, clear=False), \
                patch.object(openai_service, '_cliente', return_value=cliente):
            resultado = openai_service.analizar_perfil(self.perfil, self.resultado_reglas_perfil)
        self.assertIsNone(resultado)

    def test_respuesta_sin_claves_esperadas(self):
        contenido = json.dumps({"resumen": "Solo resumen, faltan las demás claves."})
        cliente = _cliente_mock(create_return_value=_respuesta_openai(contenido))
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'sk-test'}, clear=False), \
                patch.object(openai_service, '_cliente', return_value=cliente):
            resultado = openai_service.analizar_perfil(self.perfil, self.resultado_reglas_perfil)
        self.assertIsNone(resultado)

    def test_respuesta_con_tipos_incorrectos(self):
        contenido = json.dumps({
            "resumen": "Resumen válido.",
            "fortalezas": "no es una lista, es un string",
            "aspectos_mejora": [],
            "recomendaciones": [],
        })
        cliente = _cliente_mock(create_return_value=_respuesta_openai(contenido))
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'sk-test'}, clear=False), \
                patch.object(openai_service, '_cliente', return_value=cliente):
            resultado = openai_service.analizar_perfil(self.perfil, self.resultado_reglas_perfil)
        self.assertIsNone(resultado)

    # --- manejo de errores del SDK ---

    def test_error_autenticacion(self):
        request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
        response = httpx.Response(401, request=request)
        error = openai.AuthenticationError("Invalid API key", response=response, body=None)
        cliente = _cliente_mock(create_side_effect=error)
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'sk-test'}, clear=False), \
                patch.object(openai_service, '_cliente', return_value=cliente):
            resultado = openai_service.analizar_perfil(self.perfil, self.resultado_reglas_perfil)
        self.assertIsNone(resultado)

    def test_error_limite_uso(self):
        request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
        response = httpx.Response(429, request=request)
        error = openai.RateLimitError("Rate limit exceeded", response=response, body=None)
        cliente = _cliente_mock(create_side_effect=error)
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'sk-test'}, clear=False), \
                patch.object(openai_service, '_cliente', return_value=cliente):
            resultado = openai_service.analizar_perfil(self.perfil, self.resultado_reglas_perfil)
        self.assertIsNone(resultado)

    def test_error_conexion(self):
        request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
        error = openai.APIConnectionError(request=request)
        cliente = _cliente_mock(create_side_effect=error)
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'sk-test'}, clear=False), \
                patch.object(openai_service, '_cliente', return_value=cliente):
            resultado = openai_service.analizar_perfil(self.perfil, self.resultado_reglas_perfil)
        self.assertIsNone(resultado)

    def test_error_timeout(self):
        request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
        error = openai.APITimeoutError(request=request)
        cliente = _cliente_mock(create_side_effect=error)
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'sk-test'}, clear=False), \
                patch.object(openai_service, '_cliente', return_value=cliente):
            resultado = openai_service.analizar_perfil(self.perfil, self.resultado_reglas_perfil)
        self.assertIsNone(resultado)

    def test_error_inesperado_no_se_propaga(self):
        cliente = _cliente_mock(create_side_effect=RuntimeError("fallo inesperado del SDK"))
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'sk-test'}, clear=False), \
                patch.object(openai_service, '_cliente', return_value=cliente):
            # No debe lanzar ninguna excepción: se captura y se devuelve None.
            resultado = openai_service.analizar_perfil(self.perfil, self.resultado_reglas_perfil)
        self.assertIsNone(resultado)

    # --- otros dominios y casos límite ---

    def test_comparar_oferta_devuelve_solo_recomendaciones(self):
        oferta = DatosOferta(habilidades='Python, Django', descripcion='Backend con Django')
        candidato = DatosCandidato(habilidades='Python', experiencia='2 años', estudios='FP DAM')
        resultado_reglas = comparar_oferta(oferta, candidato)

        contenido = json.dumps({"recomendaciones": ["Aprende Django en profundidad."]})
        cliente = _cliente_mock(create_return_value=_respuesta_openai(contenido))

        with patch.dict('os.environ', {'OPENAI_API_KEY': 'sk-test'}, clear=False), \
                patch.object(openai_service, '_cliente', return_value=cliente):
            resultado = openai_service.comparar_oferta(oferta, candidato, resultado_reglas)

        self.assertEqual(resultado, {"recomendaciones": ["Aprende Django en profundidad."]})

    def test_analizar_cv_sin_texto_no_intenta_llamar_a_la_api(self):
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'sk-test'}, clear=False), \
                patch.object(openai_service, '_cliente') as cliente_constructor:
            resultado = openai_service.analizar_cv('', {'puntuacion': 0})

        self.assertIsNone(resultado)
        cliente_constructor.assert_not_called()


class MotorIAWrapperTests(SimpleTestCase):
    """
    Tests de los 5 puntos de entrada exigidos por el checklist
    (analizar_perfil_ia, analizar_cv_ia, comparar_oferta_ia,
    optimizar_linkedin_ia, evaluar_entrevista_ia): deben limitarse a
    decidir entre IA y reglas sin romper la forma del resultado que
    consumen las vistas, y deben caer siempre en el motor de reglas si la
    IA no está disponible o falla (openai_service devuelve None).
    """

    def test_analizar_perfil_ia_fallback_cuando_ia_no_disponible(self):
        perfil = PerfilProfesional(
            nombre_completo='Luis', experiencia='', estudios='', habilidades='',
            telefono='', ciudad='',
        )
        with patch.object(openai_service, 'analizar_perfil', return_value=None) as mock_ia:
            resultado = analizar_perfil_ia(perfil)

        esperado = analizar_perfil(perfil)
        esperado['puntuacion_completitud'] = calcular_puntuacion(perfil)
        self.assertEqual(resultado, esperado)
        mock_ia.assert_called_once()

    def test_analizar_perfil_ia_usa_resultado_de_ia_cuando_esta_disponible(self):
        perfil = PerfilProfesional(
            nombre_completo='Luis', experiencia='Backend', estudios='FP',
            habilidades='Python', telefono='600111222', ciudad='Madrid',
        )
        resultado_ia = {
            "resumen": "Resumen IA.",
            "fortalezas": ["F-IA"],
            "aspectos_mejora": ["A-IA"],
            "recomendaciones": ["R-IA"],
        }
        with patch.object(openai_service, 'analizar_perfil', return_value=resultado_ia):
            resultado = analizar_perfil_ia(perfil)

        self.assertEqual(resultado['resumen'], "Resumen IA.")
        self.assertEqual(resultado['fortalezas'], ["F-IA"])
        # La puntuación de completitud siempre es la calculada por reglas.
        self.assertEqual(resultado['puntuacion_completitud'], calcular_puntuacion(perfil))

    def test_analizar_cv_ia_fallback(self):
        texto = "Experiencia laboral: 5 años. Formación académica: Grado. Habilidades: Python."
        with patch.object(openai_service, 'analizar_cv', return_value=None):
            resultado = analizar_cv_ia(texto)
        self.assertEqual(resultado, analizar_cv(texto))

    def test_analizar_cv_ia_usa_resultado_de_ia(self):
        texto = "Experiencia laboral: 5 años. Formación académica: Grado. Habilidades: Python."
        resultado_ia = {"resumen": "R-IA", "fortalezas": [], "debilidades": [], "recomendaciones": []}
        with patch.object(openai_service, 'analizar_cv', return_value=resultado_ia):
            resultado = analizar_cv_ia(texto)
        self.assertEqual(resultado['resumen'], "R-IA")
        # La puntuación objetiva del CV siempre es la calculada por reglas.
        self.assertEqual(resultado['puntuacion'], analizar_cv(texto)['puntuacion'])

    def test_comparar_oferta_ia_fallback(self):
        oferta = DatosOferta(habilidades='Python', descripcion='desc')
        candidato = DatosCandidato(habilidades='Python', experiencia='2 años', estudios='FP')
        with patch.object(openai_service, 'comparar_oferta', return_value=None):
            resultado = comparar_oferta_ia(oferta, candidato)
        self.assertEqual(resultado, comparar_oferta(oferta, candidato))

    def test_comparar_oferta_ia_usa_ia_solo_para_recomendaciones(self):
        oferta = DatosOferta(habilidades='Python', descripcion='desc')
        candidato = DatosCandidato(habilidades='Python', experiencia='2 años', estudios='FP')
        base = comparar_oferta(oferta, candidato)

        with patch.object(openai_service, 'comparar_oferta', return_value={"recomendaciones": ["R-IA"]}):
            resultado = comparar_oferta_ia(oferta, candidato)

        self.assertEqual(resultado['recomendaciones'], ["R-IA"])
        # Los datos objetivos (match, habilidades) nunca los decide la IA.
        self.assertEqual(resultado['porcentaje_match'], base['porcentaje_match'])
        self.assertEqual(resultado['habilidades_coincidentes'], base['habilidades_coincidentes'])
        self.assertEqual(resultado['clasificacion'], base['clasificacion'])

    def test_optimizar_linkedin_ia_fallback(self):
        datos = li.DatosLinkedIn(titular_actual='Dev', extracto='texto largo ' * 20, habilidades='Python')
        contexto = li.DatosContexto()
        with patch.object(openai_service, 'optimizar_linkedin', return_value=None):
            resultado = li.optimizar_linkedin_ia(datos, contexto)
        self.assertEqual(resultado, li.optimizar_linkedin(datos, contexto))

    def test_optimizar_linkedin_ia_usa_resultado_de_ia(self):
        datos = li.DatosLinkedIn(titular_actual='Dev', extracto='texto largo ' * 20, habilidades='Python')
        contexto = li.DatosContexto()
        base = li.optimizar_linkedin(datos, contexto)
        resultado_ia = {
            "titular_optimizado": "Backend Developer | Python",
            "fortalezas": ["F-IA"],
            "debilidades": ["D-IA"],
            "plan_mejora": ["P-IA"],
        }
        with patch.object(openai_service, 'optimizar_linkedin', return_value=resultado_ia):
            resultado = li.optimizar_linkedin_ia(datos, contexto)

        self.assertEqual(resultado['titular_optimizado'], "Backend Developer | Python")
        # La puntuación/clasificación objetivas nunca las decide la IA.
        self.assertEqual(resultado['puntuacion'], base['puntuacion'])
        self.assertEqual(resultado['clasificacion'], base['clasificacion'])

    def test_evaluar_entrevista_ia_fallback(self):
        contexto = ee.ContextoEntrevista()
        respuestas = [ee.RespuestaEntrevista(tipo='presentacion', pregunta='¿?', respuesta='Hola, soy Ana.', orden=1)]
        with patch.object(openai_service, 'evaluar_entrevista', return_value=None):
            resultado = ee.evaluar_entrevista_ia(respuestas, contexto)
        self.assertEqual(resultado, ee.evaluar_entrevista(respuestas, contexto))

    def test_evaluar_entrevista_ia_usa_resultado_de_ia(self):
        contexto = ee.ContextoEntrevista()
        respuestas = [ee.RespuestaEntrevista(tipo='presentacion', pregunta='¿?', respuesta='Hola, soy Ana.', orden=1)]
        base = ee.evaluar_entrevista(respuestas, contexto)
        resultado_ia = {"fortalezas": ["F-IA"], "aspectos_mejora": ["A-IA"], "recomendaciones": ["R-IA"]}
        with patch.object(openai_service, 'evaluar_entrevista', return_value=resultado_ia):
            resultado = ee.evaluar_entrevista_ia(respuestas, contexto)

        self.assertEqual(resultado['fortalezas'], ["F-IA"])
        # La puntuación/clasificación de la entrevista siempre son las
        # calculadas por reglas (deterministas y auditables).
        self.assertEqual(resultado['puntuacion'], base['puntuacion'])
        self.assertEqual(resultado['clasificacion'], base['clasificacion'])
