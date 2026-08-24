from django.urls import path

from . import views


app_name = "diagnostico"


urlpatterns = [

    # ========================================================
    # REALIZAR DIAGNÓSTICO
    # ========================================================

    path(
        "<int:produto_id>/",
        views.diagnostico,
        name="diagnostico",
    ),

    # ========================================================
    # EXECUTAR IA
    # ========================================================

    path(
        "<int:produto_id>/analisar/",
        views.analisar,
        name="analisar",
    ),

    # ========================================================
    # HISTÓRICO GERAL
    # ========================================================

    path(
        "historico/",
        views.historico,
        name="historico",
    ),

    # ========================================================
    # HISTÓRICO DE UM PRODUTO
    # ========================================================

    path(
        "<int:produto_id>/historico/",
        views.historico_produto,
        name="historico_produto",
    ),

    # ========================================================
    # DETALHE DE UM DIAGNÓSTICO
    # ========================================================

    path(
        "resultado/<int:diagnostico_id>/",
        views.detalhe_diagnostico,
        name="detalhe",
    ),
]
