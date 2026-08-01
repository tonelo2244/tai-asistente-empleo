from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth import authenticate

from .models import (
    Perfil,
    ROLES,
    PerfilProfesional,
    ResultadoAnalisis,
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

class PerfilProfesionalSerializer(serializers.ModelSerializer):
    username = serializers.CharField(
        source="usuario.username",
        read_only=True
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
        