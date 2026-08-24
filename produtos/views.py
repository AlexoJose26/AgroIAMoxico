from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from categorias.models import Categoria

from .forms import ProdutoForm
from .models import ProdutoAgricola


# ============================================================
# LISTAGEM DE PRODUTOS
# ============================================================

def produtos(request):
    """
    Página principal dos produtos agrícolas.

    Mostra:
    - Produtos ativos;
    - Categorias cadastradas;
    - Total de produtos;
    - Total de categorias;
    - Total de produtos disponíveis;
    - Quantidade de produtos por categoria;
    - Filtro de produtos por categoria;
    - Quantidade de produtos do utilizador autenticado.

    A página é pública.
    """

    # ========================================================
    # CATEGORIAS
    # ========================================================

    categorias_queryset = (
        Categoria.objects
        .all()
        .order_by("nome")
    )

    # ========================================================
    # PRODUTOS ATIVOS
    # ========================================================

    produtos_queryset = (
        ProdutoAgricola.objects
        .filter(
            ativo=True
        )
        .select_related("usuario")
        .prefetch_related("categorias")
        .order_by("-criado_em")
    )

    # ========================================================
    # FILTRO POR CATEGORIA
    # ========================================================

    categoria_id = request.GET.get("categoria")

    categoria_selecionada = None

    if categoria_id:

        try:

            categoria_selecionada = get_object_or_404(
                Categoria,
                pk=int(categoria_id),
            )

            produtos_queryset = (
                produtos_queryset
                .filter(
                    categorias=categoria_selecionada
                )
                .distinct()
            )

        except (
            ValueError,
            TypeError,
        ):

            categoria_selecionada = None


    total_produtos = (
        ProdutoAgricola.objects
        .filter(
            ativo=True
        )
        .count()
    )

    total_categorias = (
        Categoria.objects
        .count()
    )

    total_disponiveis = (
        ProdutoAgricola.objects
        .filter(
            ativo=True
        )
        .count()
    )



    total_produtos_analise = (
        ProdutoAgricola.objects
        .filter(
            ativo=True,
            analise_por_imagem=True,
        )
        .count()
    )



    produtos_para_contagem = (
        ProdutoAgricola.objects
        .filter(
            ativo=True
        )
        .prefetch_related("categorias")
    )

    categoria_quantidades = {
        categoria.pk: 0
        for categoria in categorias_queryset
    }

    for produto in produtos_para_contagem:

        for categoria in produto.categorias.all():

            if categoria.pk in categoria_quantidades:

                categoria_quantidades[categoria.pk] += 1



    meus_produtos = 0

    if request.user.is_authenticated:

        meus_produtos = (
            ProdutoAgricola.objects
            .filter(
                usuario=request.user,
                ativo=True,
            )
            .count()
        )

    # ========================================================
    # CONTEXTO
    # ========================================================

    context = {
        "produtos": produtos_queryset,
        "categorias": categorias_queryset,
        "categoria_selecionada": categoria_selecionada,

        "total_produtos": total_produtos,
        "total_categorias": total_categorias,
        "total_disponiveis": total_disponiveis,
        "total_produtos_analise": total_produtos_analise,

        "categoria_quantidades": categoria_quantidades,
        "meus_produtos": meus_produtos,
    }



    return render(
        request,
        "produtos/produtos.html",
        context,
    )



@login_required
@transaction.atomic
def criar_produto(request):


    categorias = (
        Categoria.objects
        .all()
        .order_by("nome")
    )



    if request.method == "POST":

        form = ProdutoForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():


            produto = form.save(
                commit=False
            )


            produto.usuario = request.user

            produto.save()



            form.save_m2m()

            messages.success(
                request,
                f'O produto "{produto.nome}" '
                f'foi cadastrado com sucesso.',
            )

            return redirect(
                "produtos:detalhe_produto",
                pk=produto.pk,
            )


    else:

        form = ProdutoForm()


        categoria_id = request.GET.get(
            "categoria"
        )

        if categoria_id:

            try:

                categoria = Categoria.objects.get(
                    pk=int(categoria_id)
                )

                form.fields[
                    "categorias"
                ].initial = [
                    categoria.pk
                ]

            except (
                Categoria.DoesNotExist,
                ValueError,
                TypeError,
            ):

                pass



    context = {
        "form": form,
        "categorias": categorias,
        "titulo": "Cadastrar Produto Agrícola",
        "modo": "criar",
    }

    return render(
        request,
        "produtos/criar_produto.html",
        context,
    )


@login_required
@transaction.atomic
def editar_produto(request, pk):


    produto = get_object_or_404(
        ProdutoAgricola.objects.prefetch_related(
            "categorias"
        ),
        pk=pk,
    )

    if produto.usuario_id != request.user.id:

        messages.error(
            request,
            "Você não tem permissão para editar "
            "este produto.",
        )

        return redirect(
            "produtos:detalhe_produto",
            pk=produto.pk,
        )


    categorias = (
        Categoria.objects
        .all()
        .order_by("nome")
    )


    if request.method == "POST":

        form = ProdutoForm(
            request.POST,
            request.FILES,
            instance=produto,
        )

        if form.is_valid():

            produto_atualizado = form.save(
                commit=False
            )



            produto_atualizado.usuario = request.user

            produto_atualizado.save()

            form.save_m2m()

            messages.success(
                request,
                f'O produto "{produto_atualizado.nome}" '
                f'foi atualizado com sucesso.',
            )

            return redirect(
                "produtos:detalhe_produto",
                pk=produto_atualizado.pk,
            )

    else:

        form = ProdutoForm(
            instance=produto
        )

    context = {
        "form": form,
        "produto": produto,
        "categorias": categorias,
        "titulo": "Editar Produto Agrícola",
        "modo": "editar",
    }

    return render(
        request,
        "produtos/editar_produto.html",
        context,
    )


def detalhe_produto(request, pk):

    produto = get_object_or_404(
        ProdutoAgricola.objects
        .select_related("usuario")
        .prefetch_related("categorias"),
        pk=pk,
        ativo=True,
    )

    categorias = produto.categorias.all()

    sou_dono = False

    if request.user.is_authenticated:

        sou_dono = (
            produto.usuario_id == request.user.id
        )

    context = {
        "produto": produto,
        "categorias": categorias,
        "sou_dono": sou_dono,
    }

    return render(
        request,
        "produtos/detalhe_produto.html",
        context,
    )


@login_required
@transaction.atomic
def eliminar_produto(request, pk):

    produto = get_object_or_404(
        ProdutoAgricola,
        pk=pk,
    )

    if produto.usuario_id != request.user.id:

        messages.error(
            request,
            "Você não tem permissão para eliminar "
            "este produto.",
        )

        return redirect(
            "produtos:detalhe_produto",
            pk=produto.pk,
        )


    if request.method == "POST":

        nome = produto.nome


        if produto.imagem:

            produto.imagem.delete(
                save=False
            )


        produto.delete()

        messages.success(
            request,
            f'O produto "{nome}" '
            f'foi eliminado com sucesso.',
        )

        return redirect(
            "produtos:produtos"
        )

    context = {
        "produto": produto,
    }

    return render(
        request,
        "produtos/eliminar_produto.html",
        context,
    )

