from django.urls import path

from . import views


app_name = "inicio"


urlpatterns = [

    path(
        "",
        views.home,
        name="home",
    ),


    path(
        "login/",
        views.login_view,
        name="login",
    ),

    path(
        "cadastro/",
        views.cadastro,
        name="cadastro",
    ),

    path(
        "logout/",
        views.logout_view,
        name="logout",
    ),


    path(
        "perfil/",
        views.perfil,
        name="perfil",
    ),

    path(
        "perfil/editar/",
        views.editar_perfil,
        name="editar_perfil",
    ),

    path(
        "perfil/remover-foto/",
        views.remover_foto_perfil,
        name="remover_foto_perfil",
    ),

    path(
        "produtos/",
        views.produtos,
        name="produtos",
    ),

    path(
        "produtos/pesquisar/",
        views.pesquisar_produtos,
        name="pesquisar_produtos",
    ),

    path(
        "produtos/<int:pk>/",
        views.detalhe_produto,
        name="detalhe_produto",
    ),

    path(
        "sobre/",
        views.sobre,
        name="sobre",
    ),
]
