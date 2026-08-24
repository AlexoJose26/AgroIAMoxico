from django.urls import path

from . import views


app_name = "produtos"


urlpatterns = [

    # ============================================================
    # PÁGINA PRINCIPAL DOS PRODUTOS
    # URL: /produtos/
    # ============================================================
    path(
        "",
        views.produtos,
        name="produtos",
    ),

    # ============================================================
    # PÁGINA DE PRODUTOS — ALIAS
    # URL: /produtos/produtos/
    #
    # Mantido para compatibilidade com links antigos.
    # ============================================================
    path(
        "produtos/",
        views.produtos,
        name="produtos_agricolas",
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
    # URL: /produtos/<id>/
    # ============================================================
    path(
        "<int:pk>/",
        views.detalhe_produto,
        name="detalhe_produto",
    ),

    # ============================================================
    # EDITAR PRODUTO
    # URL: /produtos/<id>/editar/
    # ============================================================
    path(
        "<int:pk>/editar/",
        views.editar_produto,
        name="editar_produto",
    ),

    # ============================================================
    # ELIMINAR PRODUTO
    # URL: /produtos/<id>/eliminar/
    # ============================================================
    path(
        "<int:pk>/eliminar/",
        views.eliminar_produto,
        name="eliminar_produto",
    ),
]
