from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', include('inicio.urls')),
    path('culturas/', include('culturas.urls')),
    path('diagnostico/', include('diagnostico.urls')),
]
