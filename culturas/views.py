from django.shortcuts import render


def lista_culturas(request):
    return render(request, 'culturas/lista.html')
