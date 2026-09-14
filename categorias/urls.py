from django.urls import path
from . import views

app_name = "categorias"

urlpatterns = [
path("", views.lista_categorias, name="lista_categorias"),
path("<int:pk>/", views.detalhe_categoria, name="detalhe_categoria"),
]
