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
    - Produtos ativos
    - Categorias cadastradas
    - Total de produtos
    - Total de categorias
    - Total de produtos disponíveis
    - Quantidade de produtos por categoria
    - Filtro de produtos por categoria

    A listagem continua pública.
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
        .filter(ativo=True)
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

        except (ValueError, TypeError):
            categoria_selecionada = None

    # ========================================================
    # CONTADORES GERAIS
    # ========================================================

    total_produtos = (
        ProdutoAgricola.objects
        .filter(ativo=True)
        .count()
    )

    total_categorias = (
        Categoria.objects
        .count()
    )

    total_disponiveis = (
        ProdutoAgricola.objects
        .filter(ativo=True)
        .count()
    )

    # ========================================================
    # PRODUTOS POR CATEGORIA
    # ========================================================

    produtos_para_contagem = (
        ProdutoAgricola.objects
        .filter(ativo=True)
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

    # ========================================================
    # PRODUTOS DO UTILIZADOR AUTENTICADO
    # ========================================================

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

        "categoria_quantidades": categoria_quantidades,

        # Quantidade de produtos do utilizador
        "meus_produtos": meus_produtos,
    }

    # ========================================================
    # TEMPLATE
    # ========================================================

    return render(
        request,
        "culturas/produtos.html",
        context,
    )


# ============================================================
# CRIAR PRODUTO
# ============================================================

@login_required
@transaction.atomic
def criar_produto(request):
    """
    Cadastra um novo produto agrícola.

    O produto é automaticamente associado
    ao utilizador autenticado.
    """

    categorias = (
        Categoria.objects
        .all()
        .order_by("nome")
    )

    # ========================================================
    # POST
    # ========================================================

    if request.method == "POST":

        form = ProdutoForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():

            # ==================================================
            # SALVAR PRODUTO
            # ==================================================

            produto = form.save(
                commit=False
            )

            # ==================================================
            # ASSOCIAR AO UTILIZADOR AUTENTICADO
            # ==================================================

            produto.usuario = request.user

            produto.save()

            # ==================================================
            # SALVAR CATEGORIAS
            # ==================================================

            form.save_m2m()

            messages.success(
                request,
                f'O produto "{produto.nome}" '
                f'foi cadastrado com sucesso.',
            )

            return redirect(
                "culturas:detalhe_produto",
                pk=produto.pk,
            )

    # ========================================================
    # GET
    # ========================================================

    else:

        form = ProdutoForm()

        # ====================================================
        # CATEGORIA ENVIADA PELA URL
        #
        # Exemplo:
        #
        # /culturas/criar/?categoria=3
        # ====================================================

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

    # ========================================================
    # CONTEXTO
    # ========================================================

    context = {
        "form": form,
        "categorias": categorias,
        "titulo": "Cadastrar Produto Agrícola",
        "modo": "criar",
    }

    return render(
        request,
        "culturas/criar_produto.html",
        context,
    )


# ============================================================
# EDITAR PRODUTO
# ============================================================

@login_required
@transaction.atomic
def editar_produto(request, pk):
    """
    Edita um produto agrícola.

    Apenas o utilizador que cadastrou o produto
    pode editá-lo.
    """

    produto = get_object_or_404(
        ProdutoAgricola.objects.prefetch_related(
            "categorias"
        ),
        pk=pk,
    )

    # ========================================================
    # SEGURANÇA
    # ========================================================

    if produto.usuario != request.user:

        messages.error(
            request,
            "Você não tem permissão para editar "
            "este produto.",
        )

        return redirect(
            "culturas:detalhe_produto",
            pk=produto.pk,
        )

    categorias = (
        Categoria.objects
        .all()
        .order_by("nome")
    )

    # ========================================================
    # POST
    # ========================================================

    if request.method == "POST":

        form = ProdutoForm(
            request.POST,
            request.FILES,
            instance=produto,
        )

        if form.is_valid():

            produto = form.save()

            messages.success(
                request,
                f'O produto "{produto.nome}" '
                f'foi atualizado com sucesso.',
            )

            return redirect(
                "culturas:detalhe_produto",
                pk=produto.pk,
            )

    # ========================================================
    # GET
    # ========================================================

    else:

        form = ProdutoForm(
            instance=produto
        )

    # ========================================================
    # CONTEXTO
    # ========================================================

    context = {
        "form": form,
        "produto": produto,
        "categorias": categorias,
        "titulo": "Editar Produto Agrícola",
        "modo": "editar",
    }

    return render(
        request,
        "culturas/editar_produto.html",
        context,
    )


# ============================================================
# DETALHES DO PRODUTO
# ============================================================

def detalhe_produto(request, pk):
    """
    Mostra os detalhes completos
    de um produto agrícola.

    A página continua pública.
    """

    produto = get_object_or_404(
        ProdutoAgricola.objects
        .select_related("usuario")
        .prefetch_related("categorias"),
        pk=pk,
    )

    categorias = produto.categorias.all()

    # ========================================================
    # VERIFICAÇÃO DO UTILIZADOR
    # ========================================================

    sou_dono = False

    if request.user.is_authenticated:
        sou_dono = (
            produto.usuario_id == request.user.id
        )

    # ========================================================
    # CONTEXTO
    # ========================================================

    context = {
        "produto": produto,
        "categorias": categorias,

        # Informa ao template se o produto
        # pertence ao utilizador atual
        "sou_dono": sou_dono,
    }

    return render(
        request,
        "culturas/detalhe_produto.html",
        context,
    )


# ============================================================
# ELIMINAR PRODUTO
# ============================================================

@login_required
@transaction.atomic
def eliminar_produto(request, pk):
    """
    Elimina um produto agrícola.

    GET:
        Mostra a confirmação.

    POST:
        Elimina definitivamente.

    Apenas o utilizador que cadastrou o produto
    pode eliminá-lo.
    """

    produto = get_object_or_404(
        ProdutoAgricola,
        pk=pk,
    )

    # ========================================================
    # SEGURANÇA
    # ========================================================

    if produto.usuario != request.user:

        messages.error(
            request,
            "Você não tem permissão para eliminar "
            "este produto.",
        )

        return redirect(
            "culturas:detalhe_produto",
            pk=produto.pk,
        )

    # ========================================================
    # POST
    # ========================================================

    if request.method == "POST":

        nome = produto.nome

        # ----------------------------------------------------
        # REMOVER IMAGEM ASSOCIADA
        # ----------------------------------------------------

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
            "culturas:produtos",
        )

    # ========================================================
    # CONTEXTO
    # ========================================================

    context = {
        "produto": produto,
    }

    return render(
        request,
        "culturas/eliminar_produto.html",
        context,
    )
