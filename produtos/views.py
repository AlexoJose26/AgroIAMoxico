from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from categorias.models import Categoria
from .forms import ProdutoForm
from .models import ProdutoAgricola


# ============================================================
# IMPORTAÇÃO OPCIONAL DO DIAGNÓSTICO
# ============================================================

try:
    from diagnostico.models import Diagnostico
except (ImportError, ModuleNotFoundError):
    Diagnostico = None


# ============================================================
# LISTAGEM DE PRODUTOS
# ============================================================

@login_required
def produtos(request):
    """
    Página principal dos produtos agrícolas.

    Indicadores apresentados no Hero:

    - total_produtos:
        Todos os produtos cadastrados.

    - total_disponiveis:
        Produtos com ativo=True.

    - total_categorias_associadas:
        Categorias que possuem pelo menos um produto associado.

    - total_diagnosticos:
        Total de diagnósticos associados aos produtos.
    """

    # --------------------------------------------------------
    # PRODUTOS
    # --------------------------------------------------------

    produtos_qs = (
        ProdutoAgricola.objects
        .prefetch_related("categorias")
        .order_by("nome")
    )

    # --------------------------------------------------------
    # 1. TOTAL DE PRODUTOS CADASTRADOS
    # --------------------------------------------------------

    total_produtos = ProdutoAgricola.objects.count()

    # --------------------------------------------------------
    # 2. TOTAL DE PRODUTOS DISPONÍVEIS
    # --------------------------------------------------------

    total_disponiveis = (
        ProdutoAgricola.objects
        .filter(ativo=True)
        .count()
    )

    # --------------------------------------------------------
    # 3. TOTAL DE CATEGORIAS ASSOCIADAS
    # --------------------------------------------------------

    total_categorias_associadas = (
        Categoria.objects
        .filter(produtos__isnull=False)
        .distinct()
        .count()
    )

    # --------------------------------------------------------
    # 4. TOTAL DE DIAGNÓSTICOS
    # --------------------------------------------------------

    total_diagnosticos = 0

    if Diagnostico is not None:
        total_diagnosticos = (
            Diagnostico.objects
            .filter(produto__isnull=False)
            .count()
        )

    # --------------------------------------------------------
    # DIAGNÓSTICOS POR PRODUTO
    # --------------------------------------------------------

    diagnosticos_por_produto = {}

    if Diagnostico is not None:

        registros = (
            Diagnostico.objects
            .filter(produto__isnull=False)
            .values("produto_id")
            .annotate(quantidade=Count("id"))
        )

        diagnosticos_por_produto = {
            item["produto_id"]: item["quantidade"]
            for item in registros
        }

    # --------------------------------------------------------
    # CATEGORIAS E DIAGNÓSTICOS POR PRODUTO
    # --------------------------------------------------------

    produtos_lista = []

    for produto in produtos_qs:

        produto.total_categorias_produto = (
            produto.categorias.count()
        )

        produto.total_diagnosticos_produto = (
            diagnosticos_por_produto.get(
                produto.pk,
                0
            )
        )

        produtos_lista.append(produto)

    # --------------------------------------------------------
    # CONTEXTO
    # --------------------------------------------------------

    contexto = {
        "produtos": produtos_lista,

        # HERO
        "total_produtos": total_produtos,
        "total_disponiveis": total_disponiveis,
        "total_categorias_associadas": total_categorias_associadas,
        "total_diagnosticos": total_diagnosticos,
    }

    return render(
        request,
        "produtos/produtos.html",
        contexto
    )


# ============================================================
# CRIAR PRODUTO
# ============================================================

@login_required
def criar_produto(request):

    if request.method == "POST":

        form = ProdutoForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():

            try:

                with transaction.atomic():

                    produto = form.save(commit=False)

                    if hasattr(produto, "usuario_id"):
                        produto.usuario = request.user

                    produto.save()

                    form.save_m2m()

                messages.success(
                    request,
                    f'O produto "{produto.nome}" '
                    "foi cadastrado com sucesso."
                )

                return redirect(
                    "produtos:produtos"
                )

            except Exception as exc:

                messages.error(
                    request,
                    "Não foi possível cadastrar "
                    f"o produto. Erro: {exc}"
                )

    else:

        form = ProdutoForm()

    contexto = {
        "form": form,
        "titulo": "Cadastrar Produto",
        "modo": "criar",
        "categorias": (
            Categoria.objects
            .filter(ativo=True)
            .order_by("nome")
        ),
    }

    return render(
        request,
        "produtos/criar_produto.html",
        contexto
    )


# ============================================================
# DETALHES
# ============================================================

@login_required
def detalhe_produto(request, pk):

    produto = get_object_or_404(
        ProdutoAgricola.objects.prefetch_related(
            "categorias"
        ),
        pk=pk
    )

    categorias_produto = (
        produto.categorias
        .all()
        .order_by("nome")
    )

    total_diagnosticos = 0

    if Diagnostico is not None:

        total_diagnosticos = (
            Diagnostico.objects
            .filter(produto=produto)
            .count()
        )

    contexto = {
        "produto": produto,
        "categorias_produto": categorias_produto,
        "total_categorias": categorias_produto.count(),
        "total_diagnosticos": total_diagnosticos,
    }

    return render(
        request,
        "produtos/produto_detalhes.html",
        contexto
    )


# ============================================================
# EDITAR PRODUTO
# ============================================================

@login_required
def editar_produto(request, pk):

    produto = get_object_or_404(
        ProdutoAgricola,
        pk=pk
    )

    if request.method == "POST":

        form = ProdutoForm(
            request.POST,
            request.FILES,
            instance=produto
        )

        if form.is_valid():

            try:

                with transaction.atomic():

                    produto = form.save(commit=False)

                    if (
                        hasattr(produto, "usuario_id")
                        and not produto.usuario_id
                    ):
                        produto.usuario = request.user

                    produto.save()

                    form.save_m2m()

                messages.success(
                    request,
                    f'O produto "{produto.nome}" '
                    "foi atualizado com sucesso."
                )

                return redirect(
                    "produtos:produtos"
                )

            except Exception as exc:

                messages.error(
                    request,
                    "Não foi possível atualizar "
                    f"o produto. Erro: {exc}"
                )

    else:

        form = ProdutoForm(
            instance=produto
        )

    contexto = {
        "form": form,
        "produto": produto,
        "categorias_produto": (
            produto.categorias
            .all()
            .order_by("nome")
        ),
        "categorias_disponiveis": (
            Categoria.objects
            .filter(ativo=True)
            .order_by("nome")
        ),
        "titulo": "Editar Produto",
        "modo": "editar",
    }

    return render(
        request,
        "produtos/editar_produto.html",
        contexto
    )


# ============================================================
# ELIMINAR PRODUTO
# ============================================================

@login_required
def eliminar_produto(request, pk):

    produto = get_object_or_404(
        ProdutoAgricola,
        pk=pk
    )

    if request.method == "POST":

        nome = produto.nome

        try:

            with transaction.atomic():
                produto.delete()

            messages.success(
                request,
                f'O produto "{nome}" '
                "foi eliminado com sucesso."
            )

        except Exception as exc:

            messages.error(
                request,
                "Não foi possível eliminar "
                f"o produto. Erro: {exc}"
            )

        return redirect(
            "produtos:produtos"
        )

    return render(
        request,
        "produtos/eliminar_produto.html",
        {
            "produto": produto
        }
    )
