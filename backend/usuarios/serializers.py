from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.core.validators import RegexValidator
from pypdf import PdfReader

from .models import (
    Perfil,
    ROLES,
    PerfilProfesional,
    ResultadoAnalisis,
    Curriculum,
)


# -----------------------------
# Registro
# -----------------------------

class RegistroSerializer(serializers.Serializer):
    username = serializers.CharField()
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    rol = serializers.ChoiceField(choices=ROLES, default='usuario')

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Ese nombre de usuario ya existe.")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
        )

        Perfil.objects.create(
            usuario=user,
            rol=validated_data["rol"]
        )

        return user


# -----------------------------
# Login
# -----------------------------

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(
            username=data["username"],
            password=data["password"]
        )

        if not user:
            raise serializers.ValidationError("Credenciales incorrectas.")

        data["user"] = user
        return data


# -----------------------------
# Perfil de usuario
# -----------------------------

class PerfilSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="usuario.username")
    email = serializers.CharField(source="usuario.email")

    class Meta:
        model = Perfil
        fields = [
            "username",
            "email",
            "rol",
        ]


# -----------------------------
# Perfil profesional
# -----------------------------

TELEFONO_VALIDATOR = RegexValidator(
    regex=r'^[0-9+\-\s()]*$',
    message="El teléfono solo puede contener números, espacios y los símbolos + - ( )."
)


class PerfilProfesionalSerializer(serializers.ModelSerializer):
    username = serializers.CharField(
        source="usuario.username",
        read_only=True
    )

    # Los tres campos de texto libre son TextField sin límite en el modelo;
    # se acota aquí para evitar entradas desproporcionadas sin necesitar migración.
    estudios = serializers.CharField(
        required=False, allow_blank=True, max_length=2000
    )
    experiencia = serializers.CharField(
        required=False, allow_blank=True, max_length=4000
    )
    habilidades = serializers.CharField(
        required=False, allow_blank=True, max_length=2000
    )
    telefono = serializers.CharField(
        required=False, allow_blank=True, max_length=20,
        validators=[TELEFONO_VALIDATOR]
    )

    class Meta:
        model = PerfilProfesional
        fields = [
            "username",
            "nombre_completo",
            "telefono",
            "ciudad",
            "estudios",
            "experiencia",
            "habilidades",
        ]

    def validate(self, data):
        # Sanitización básica: quitar espacios sobrantes en los campos de texto recibidos.
        for campo in ("nombre_completo", "telefono", "ciudad", "estudios", "experiencia", "habilidades"):
            if campo in data and isinstance(data[campo], str):
                data[campo] = data[campo].strip()
        return data


# -----------------------------
# Resultado de análisis
# -----------------------------

class ResultadoAnalisisSerializer(serializers.ModelSerializer):
    fecha_creacion = serializers.DateTimeField(
        format="%d/%m/%Y %H:%M",
        read_only=True
    )

    class Meta:
        model = ResultadoAnalisis
        fields = [
            "id",
            "resumen",
            "fortalezas",
            "aspectos_mejora",
            "recomendaciones",
            "puntuacion_completitud",
            "fecha_creacion",
        ]


# -----------------------------
# Curriculum (CV) — Fase 6
# -----------------------------

MAX_CV_SIZE_MB = 5
MAX_CV_SIZE_BYTES = MAX_CV_SIZE_MB * 1024 * 1024


class CurriculumUploadSerializer(serializers.Serializer):
    archivo = serializers.FileField()

    def validate_archivo(self, value):
        nombre = (value.name or '').lower()

        if not nombre.endswith('.pdf'):
            raise serializers.ValidationError("Solo se admiten archivos PDF.")

        content_type = getattr(value, 'content_type', '') or ''
        if content_type and content_type not in ('application/pdf', 'application/x-pdf'):
            raise serializers.ValidationError("Solo se admiten archivos PDF.")

        if value.size > MAX_CV_SIZE_BYTES:
            raise serializers.ValidationError(
                f"El archivo supera el tamaño máximo permitido ({MAX_CV_SIZE_MB} MB)."
            )

        try:
            PdfReader(value)
        except Exception:
            raise serializers.ValidationError("El archivo no es un PDF válido o está dañado.")
        finally:
            value.seek(0)

        return value


class CurriculumSerializer(serializers.ModelSerializer):
    fecha_subida = serializers.DateTimeField(
        format="%d/%m/%Y %H:%M",
        read_only=True
    )

    class Meta:
        model = Curriculum
        fields = [
            "id",
            "nombre_archivo",
            "texto_extraido",
            "resumen",
            "puntuacion",
            "fortalezas",
            "debilidades",
            "recomendaciones",
            "fecha_subida",
        ]
