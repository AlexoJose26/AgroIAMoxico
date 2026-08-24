from django.urls import path

from . import views


app_name = "categorias"


urlpatterns = [

    # ========================================================
    # CRIAR CATEGORIA
    # ========================================================
    path(
        "criar/",
        views.categoria_criar,
        name="categoria_criar",
    ),

    # ========================================================
    # DETALHES DA CATEGORIA
    # ========================================================
    path(
        "<int:pk>/",
        views.categoria_detalhes,
        name="categoria_detalhes",
    ),

    # ========================================================
    # EDITAR CATEGORIA
    # ========================================================
    path(
        "<int:pk>/editar/",
        views.categoria_editar,
        name="categoria_editar",
    ),

    # ========================================================
    # ELIMINAR CATEGORIA
    # ========================================================
    path(
        "<int:pk>/eliminar/",
        views.categoria_eliminar,
        name="categoria_eliminar",
    ),
]
