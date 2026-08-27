from django.urls import path

from . import views


app_name = "diagnostico"


urlpatterns = [

    path(
        "",
        views.diagnostico,
        name="diagnostico",
    ),

    path(
        "produto/<int:produto_id>/",
        views.diagnostico,
        name="diagnostico_produto",
    ),


    path(
        "produto/<int:produto_id>/analisar/",
        views.analisar,
        name="analisar",
    ),


    path(
        "analisar/",
        views.analisar,
        name="analisar_geral",
    ),

    path(
        "historico/produto/<int:produto_id>/",
        views.historico_produto,
        name="historico_produto",
    ),

    path(
        "detalhe/<int:diagnostico_id>/",
        views.detalhe_diagnostico,
        name="detalhe",
    ),
]
