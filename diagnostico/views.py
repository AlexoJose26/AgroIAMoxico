from django.shortcuts import render


def diagnostico(request):
    return render(request, 'diagnostico/diagnostico.html')
