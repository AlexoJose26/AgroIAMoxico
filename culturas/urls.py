from django.urls import path

from . import views


app_name = "culturas"


urlpatterns = [

    # ========================================================
    # PRODUTOS
    # ========================================================

    path(
        "",
        views.produtos,
        name="produtos",
    ),

    path(
        "produtos/",
        views.produtos,
        name="produtos_agricolas",
    ),

    # ========================================================
    # CRIAR
    # ========================================================

    path(
        "criar/",
        views.criar_produto,
        name="criar_produto",
    ),

    # ========================================================
    # DETALHES
    # ========================================================

    path(
        "<int:pk>/",
        views.detalhe_produto,
        name="detalhe_produto",
    ),

    # ========================================================
    # EDITAR
    # ========================================================

    path(
        "<int:pk>/editar/",
        views.editar_produto,
        name="editar_produto",
    ),

    # ========================================================
    # ELIMINAR
    # ========================================================

    path(
        "<int:pk>/eliminar/",
        views.eliminar_produto,
        name="eliminar_produto",
    ),
]
