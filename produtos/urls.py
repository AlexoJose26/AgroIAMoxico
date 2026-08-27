from django.urls import path

from . import views


app_name = "produtos"


urlpatterns = [
    # ============================================================
    # LISTA DE PRODUTOS
    # URL: /produtos/
    # ============================================================
    path(
        "",
        views.produtos,
        name="produtos",
    ),

    # ============================================================
    # CRIAR PRODUTO
    # URL: /produtos/criar/
    # ============================================================
    path(
        "criar/",
        views.criar_produto,
        name="criar_produto",
    ),

    # ============================================================
    # DETALHES DO PRODUTO
    # URL: /produtos/2/
    # ============================================================
    path(
        "<int:pk>/",
        views.detalhe_produto,
        name="detalhe_produto",
    ),

    # ============================================================
    # EDITAR PRODUTO
    # URL: /produtos/2/editar/
    # ============================================================
    path(
        "<int:pk>/editar/",
        views.editar_produto,
        name="editar_produto",
    ),

    # ============================================================
    # ELIMINAR PRODUTO
    # URL: /produtos/2/eliminar/
    # ============================================================
    path(
        "<int:pk>/eliminar/",
        views.eliminar_produto,
        name="eliminar_produto",
    ),
]
