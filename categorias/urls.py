from django.urls import path

from . import views

app_name = "categorias"

urlpatterns = [
    path("", views.categorias, name="categorias"),
    path("criar/", views.categoria_criar, name="categoria_criar"),
    path("<int:pk>/", views.categoria_detalhes, name="categoria_detalhes"),
    path("<int:pk>/editar/", views.categoria_editar, name="categoria_editar"),
    path("<int:pk>/eliminar/", views.categoria_eliminar, name="categoria_eliminar"),
]
