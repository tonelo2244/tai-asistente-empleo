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


# Clasificaciones posibles del porcentaje de compatibilidad (Fase 7)
CLASIFICACIONES_MATCH = [
    ('Excelente', 'Excelente'),
    ('Muy buena', 'Muy buena'),
    ('Buena', 'Buena'),
    ('Mejorable', 'Mejorable'),
    ('Insuficiente', 'Insuficiente'),
]


class Oferta(models.Model):
    # Un usuario puede comparar varias ofertas de empleo a lo largo del tiempo
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)

    # Datos de la oferta de empleo introducidos por el usuario
    titulo_puesto = models.CharField(max_length=150)
    empresa = models.CharField(max_length=150)
    ubicacion = models.CharField(max_length=100, blank=True)
    descripcion = models.TextField()
    requisitos = models.TextField(blank=True)
    habilidades = models.TextField(blank=True)
    estudios_requeridos = models.CharField(max_length=255, blank=True)
    experiencia_requerida = models.CharField(max_length=255, blank=True)

    # Resultado de la comparación — misma filosofía que ResultadoAnalisis/Curriculum
    habilidades_coincidentes = models.JSONField(default=list)
    habilidades_faltantes = models.JSONField(default=list)
    palabras_clave_coincidentes = models.JSONField(default=list)
    experiencia_compatible = models.BooleanField(default=False)
    estudios_compatibles = models.BooleanField(default=False)
    porcentaje_match = models.IntegerField(default=0)
    clasificacion = models.CharField(
        max_length=20, choices=CLASIFICACIONES_MATCH, default='Insuficiente'
    )
    recomendaciones = models.JSONField(default=list)

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"{self.titulo_puesto} en {self.empresa} — {self.usuario.username}"


class OptimizacionLinkedIn(models.Model):
    # Un usuario puede optimizar su perfil de LinkedIn varias veces
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)

    # Datos originales del perfil de LinkedIn introducidos por el usuario
    titular_actual = models.CharField(max_length=220, blank=True)
    extracto = models.TextField()
    experiencia = models.TextField(blank=True)
    estudios = models.TextField(blank=True)
    habilidades = models.TextField(blank=True)

    # Resultado del análisis — misma filosofía que Curriculum/Oferta
    puntuacion = models.IntegerField(default=0)
    clasificacion = models.CharField(
        max_length=20, choices=CLASIFICACIONES_MATCH, default='Insuficiente'
    )
    titular_optimizado = models.CharField(max_length=300, blank=True)
    fortalezas = models.JSONField(default=list)
    debilidades = models.JSONField(default=list)
    plan_mejora = models.JSONField(default=list)

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_creacion']

    def __str__(self):
        return (
            f"Optimización LinkedIn de {self.usuario.username} — "
            f"{self.fecha_creacion.strftime('%d/%m/%Y %H:%M')}"
        )


class SimulacionEntrevista(models.Model):
    # Un usuario puede realizar varias simulaciones de entrevista
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)

    # Resultado del feedback — misma filosofía que ResultadoAnalisis/Curriculum/Oferta/OptimizacionLinkedIn
    puntuacion = models.IntegerField(default=0)
    clasificacion = models.CharField(
        max_length=20, choices=CLASIFICACIONES_MATCH, default='Insuficiente'
    )
    fortalezas = models.JSONField(default=list)
    aspectos_mejora = models.JSONField(default=list)
    recomendaciones = models.JSONField(default=list)

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_creacion']

    def __str__(self):
        return (
            f"Simulación de entrevista de {self.usuario.username} — "
            f"{self.fecha_creacion.strftime('%d/%m/%Y %H:%M')}"
        )


class PreguntaRespuesta(models.Model):
    # Cada pregunta respondida pertenece a una única simulación
    simulacion = models.ForeignKey(
        SimulacionEntrevista, on_delete=models.CASCADE, related_name='preguntas'
    )

    # El tipo se valida en el motor de reglas (evaluador_entrevista.py), que
    # debe permanecer independiente de Django; por eso no se usa `choices`
    # aquí para no duplicar ni acoplar esa lista al ORM.
    tipo = models.CharField(max_length=30)
    pregunta = models.TextField()
    respuesta = models.TextField(blank=True)
    orden = models.PositiveIntegerField()

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['orden']

    def __str__(self):
        return f"Pregunta {self.orden} de la simulación #{self.simulacion_id}"