from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from rest_framework.authtoken.models import Token

from .models import Perfil, PerfilProfesional, ResultadoAnalisis
from .utils import calcular_puntuacion


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
