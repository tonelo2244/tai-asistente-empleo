from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.authtoken.models import Token

from .models import Perfil


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
