from django.urls import path
from . import views

urlpatterns = [
    # Fase 1
    path('ping/',                views.ping),

    # Fase 2
    path('registro/',            views.registro),
    path('login/',               views.login),
    path('yo/',                  views.yo),

    # Fase 3
    path('perfil-profesional/',  views.perfil_profesional),

    # Fase 4 — se mantiene para no romper enlaces existentes
    path('analisis-perfil/',     views.analisis_perfil),

    # Fase 5 — análisis persistente
    path('analisis/generar/',    views.generar_analisis),
    path('analisis/ultimo/',     views.ultimo_analisis),
    path('analisis/historial/',  views.historial_analisis),

    # Fase 6 — análisis de CV
    path('cv/subir/',            views.subir_cv),
    path('cv/ultimo/',           views.ultimo_cv),
    path('cv/historial/',        views.historial_cv),

    # Fase 7 — comparación con ofertas de empleo
    path('ofertas/crear/',       views.crear_oferta),
    path('ofertas/historial/',   views.historial_ofertas),
]