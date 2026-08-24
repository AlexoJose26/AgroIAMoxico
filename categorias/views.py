from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CategoriaForm
from .models import Categoria



@login_required
def categoria_criar(request):

    if request.method == "POST":

        form = CategoriaForm(request.POST)

        if form.is_valid():

            categoria = form.save()

            messages.success(
                request,
                f'A categoria "{categoria.nome}" foi criada com sucesso.'
            )

            return redirect("produtos:produtos")

    else:

        form = CategoriaForm()

    context = {
        "form": form,
        "titulo": "Cadastrar Categoria",
        "modo": "criar",
    }

    return render(
        request,
        "categorias/categoria_form.html",
        context,
    )



def categoria_detalhes(request, pk):

    categoria = get_object_or_404(
        Categoria.objects.prefetch_related("produtos"),
        pk=pk,
    )

    produtos = categoria.produtos.all()

    context = {
        "categoria": categoria,
        "produtos": produtos,
        "total_produtos": produtos.count(),
    }

    return render(
        request,
        "categorias/categoria_detalhes.html",
        context,
    )



@login_required
def categoria_editar(request, pk):


    categoria = get_object_or_404(
        Categoria,
        pk=pk,
    )

    if request.method == "POST":

        form = CategoriaForm(
            request.POST,
            instance=categoria,
        )

        if form.is_valid():

            categoria = form.save()

            messages.success(
                request,
                f'A categoria "{categoria.nome}" foi atualizada com sucesso.'
            )

            return redirect("produtos:produtos")

    else:

        form = CategoriaForm(
            instance=categoria,
        )

    context = {
        "form": form,
        "categoria": categoria,
        "titulo": "Editar Categoria",
        "modo": "editar",
    }

    return render(
        request,
        "categorias/categoria_form.html",
        context,
    )



@login_required
def categoria_eliminar(request, pk):


    categoria = get_object_or_404(
        Categoria,
        pk=pk,
    )

    produtos_associados = categoria.produtos.count()

    if request.method == "POST":

        nome = categoria.nome

        with transaction.atomic():

            categoria.delete()

        messages.success(
            request,
            f'A categoria "{nome}" foi eliminada com sucesso.'
        )

        return redirect("produtos:produtos")

    context = {
        "categoria": categoria,
        "produtos_associados": produtos_associados,
    }

    return render(
        request,
        "categorias/categoria_confirm_delete.html",
        context,
    )
