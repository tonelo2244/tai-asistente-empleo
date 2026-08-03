from django.db import models
from django.contrib.auth.models import User

# Opciones de rol disponibles en la aplicación
ROLES = [
    ('usuario', 'Usuario'),
    ('orientador', 'Orientador'),
    ('administrador', 'Administrador'),
]


class Perfil(models.Model):
    # Cada perfil está ligado a un User de Django (relación 1 a 1)
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    rol = models.CharField(max_length=20, choices=ROLES, default='usuario')

    def __str__(self):
        return f"{self.usuario.username} - {self.rol}"


class PerfilProfesional(models.Model):
    # Relación 1 a 1 con User — cada usuario tiene un solo perfil profesional
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    nombre_completo = models.CharField(max_length=150, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    ciudad = models.CharField(max_length=100, blank=True)
    estudios = models.TextField(blank=True)
    experiencia = models.TextField(blank=True)
    habilidades = models.TextField(blank=True)

    def __str__(self):
        return f"Perfil profesional de {self.usuario.username}"


class ResultadoAnalisis(models.Model):
    # Un usuario puede tener muchos análisis guardados
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)

    # Resultado del análisis
    resumen = models.TextField(blank=True)
    fortalezas = models.JSONField(default=list)
    aspectos_mejora = models.JSONField(default=list)
    recomendaciones = models.JSONField(default=list)

    # Porcentaje de completitud del perfil
    puntuacion_completitud = models.IntegerField(default=0)

    # Fecha de creación automática
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_creacion']

    def __str__(self):
        return (
            f"Análisis de {self.usuario.username} — "
            f"{self.fecha_creacion.strftime('%d/%m/%Y %H:%M')}"
        )


def ruta_cv(instance, filename):
    return f'cv/{instance.usuario_id}/{filename}'


class Curriculum(models.Model):
    # Un usuario puede subir y analizar varios CV a lo largo del tiempo
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)

    archivo = models.FileField(upload_to=ruta_cv)
    nombre_archivo = models.CharField(max_length=255, blank=True)
    texto_extraido = models.TextField(blank=True)

    # Resultado del análisis — misma filosofía que ResultadoAnalisis
    resumen = models.TextField(blank=True)
    puntuacion = models.IntegerField(default=0)
    fortalezas = models.JSONField(default=list)
    debilidades = models.JSONField(default=list)
    recomendaciones = models.JSONField(default=list)

    fecha_subida = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_subida']

    def __str__(self):
        return (
            f"CV de {self.usuario.username} — "
            f"{self.fecha_subida.strftime('%d/%m/%Y %H:%M')}"
        )