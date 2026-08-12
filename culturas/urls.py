from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_culturas, name='lista_culturas'),
]
