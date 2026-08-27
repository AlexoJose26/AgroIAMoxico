from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CategoriaForm
from .models import Categoria


@login_required
def categorias(request):
    """
    Lista todas as categorias cadastradas.

    Também calcula:
    - total de categorias;
    - categorias ativas;
    - produtos classificados;
    - produtos ativos por categoria.
    """

    categorias_qs = (
        Categoria.objects
        .annotate(
            produtos_count=Count(
                "produtos",
                distinct=True
            ),
            produtos_ativos_count=Count(
                "produtos",
                filter=Q(produtos__ativo=True),
                distinct=True
            ),
        )
        .order_by("nome")
    )

    total_categorias = categorias_qs.count()

    categorias_ativas = categorias_qs.filter(
        ativo=True
    ).count()

    total_produtos_classificados = (
        categorias_qs
        .aggregate(
            total=Count(
                "produtos",
                distinct=True
            )
        )
        .get("total", 0)
    )

    contexto = {
        "categorias": categorias_qs,
        "total_categorias": total_categorias,
        "categorias_ativas": categorias_ativas,
        "total_produtos_classificados": total_produtos_classificados,
    }

    return render(
        request,
        "categorias/categorias.html",
        contexto
    )


@login_required
def categoria_criar(request):
    """
    Cria uma nova categoria.
    """

    if request.method == "POST":
        form = CategoriaForm(request.POST)

        if form.is_valid():
            categoria = form.save()

            messages.success(
                request,
                f'A categoria "{categoria.nome}" foi cadastrada com sucesso.'
            )

            return redirect("categorias:categorias")

    else:
        form = CategoriaForm()

    return render(
        request,
        "categorias/categoria_form.html",
        {
            "form": form,
            "modo": "criar",
            "titulo": "Nova categoria",
            "subtitulo": (
                "Cadastre uma nova categoria agrícola "
                "para organizar os produtos."
            ),
        }
    )


@login_required
def categoria_detalhes(request, pk):
    """
    Exibe os detalhes de uma categoria.
    """

    categoria = get_object_or_404(
        Categoria,
        pk=pk
    )

    produtos = (
        categoria.produtos
        .all()
        .order_by("nome")
    )

    produtos_ativos = produtos.filter(
        ativo=True
    ).count()

    contexto = {
        "categoria": categoria,
        "produtos": produtos,
        "total_produtos": produtos.count(),
        "produtos_ativos": produtos_ativos,
    }

    return render(
        request,
        "categorias/categoria_detalhes.html",
        contexto
    )


@login_required
def categoria_editar(request, pk):
    """
    Edita uma categoria existente.
    """

    categoria = get_object_or_404(
        Categoria,
        pk=pk
    )

    if request.method == "POST":
        form = CategoriaForm(
            request.POST,
            instance=categoria
        )

        if form.is_valid():
            categoria = form.save()

            messages.success(
                request,
                f'A categoria "{categoria.nome}" foi atualizada com sucesso.'
            )

            return redirect(
                "categorias:categorias"
            )

    else:
        form = CategoriaForm(
            instance=categoria
        )

    return render(
        request,
        "categorias/categoria_form.html",
        {
            "form": form,
            "modo": "editar",
            "categoria": categoria,
            "titulo": "Editar categoria",
            "subtitulo": (
                "Atualize as informações desta "
                "categoria agrícola."
            ),
        }
    )


@login_required
def categoria_eliminar(request, pk):
    """
    Elimina uma categoria.
    """

    categoria = get_object_or_404(
        Categoria,
        pk=pk
    )

    if request.method == "POST":
        nome = categoria.nome

        categoria.delete()

        messages.success(
            request,
            f'A categoria "{nome}" foi eliminada com sucesso.'
        )

        return redirect(
            "categorias:categorias"
        )

    return render(
        request,
        "categorias/categoria_confirm_delete.html",
        {
            "categoria": categoria,
        }
    )
