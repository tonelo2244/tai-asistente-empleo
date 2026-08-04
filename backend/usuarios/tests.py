import io
import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from rest_framework.authtoken.models import Token

from .comparador import (
    DatosCandidato,
    DatosOferta,
    calcular_porcentaje_match,
    clasificar_match,
    comparar_habilidades,
    comparar_oferta,
    evaluar_estudios,
    evaluar_experiencia,
)
from .models import Curriculum, Oferta, Perfil, PerfilProfesional, ResultadoAnalisis
from .utils import calcular_puntuacion


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
