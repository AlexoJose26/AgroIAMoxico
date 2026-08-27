# ============================================================
# AGROIA MOXICO
# URLS PRINCIPAIS DO PROJETO
# ============================================================

from django.contrib import admin
from django.urls import include, path

from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [

    # ========================================================
    # ADMINISTRADOR DJANGO
    # ========================================================
    path(
        "admin/",
        admin.site.urls,
    ),

    # ========================================================
    # INÍCIO
    # ========================================================
    path(
        "",
        include("inicio.urls"),
    ),

    # ========================================================
    # PRODUTOS AGRÍCOLAS
    # ========================================================
    path(
        "produtos/",
        include("produtos.urls"),
    ),

    # ========================================================
    # CATEGORIAS
    # ========================================================
    path(
        "categorias/",
        include("categorias.urls"),
    ),

    # ========================================================
    # DIAGNÓSTICO IA
    # ========================================================
    path(
        "diagnostico/",
        include("diagnostico.urls"),
    ),
]


# ============================================================
# ARQUIVOS DE MEDIA — DESENVOLVIMENTO
# ============================================================

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
