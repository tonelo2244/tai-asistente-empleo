from django.contrib import admin
from django.urls import path, include
from usuarios.views import ping

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/ping/', ping),
    path('api/usuarios/', include('usuarios.urls')),
]