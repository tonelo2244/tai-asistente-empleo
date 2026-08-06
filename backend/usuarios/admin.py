from django.contrib import admin

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

# Registro simple para poder inspeccionar los datos desde el panel de
# administración; sin personalización adicional (list_display, filtros, etc.).
admin.site.register(Perfil)
admin.site.register(PerfilProfesional)
admin.site.register(ResultadoAnalisis)
admin.site.register(Curriculum)
admin.site.register(Oferta)
admin.site.register(OptimizacionLinkedIn)
admin.site.register(SimulacionEntrevista)
admin.site.register(PreguntaRespuesta)
