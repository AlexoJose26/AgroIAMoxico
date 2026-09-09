import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from categorias.models import Categoria

from .forms import ProdutoForm
from .models import ProdutoAgricola


logger = logging.getLogger(__name__)

MAX_IMAGE_SIZE = 4 * 1024 * 1024

try:
    from diagnostico.models import Diagnostico
except (ImportError, ModuleNotFoundError):
    Diagnostico = None


def _categorias_ativas():
    return (
        Categoria.objects
        .filter(ativo=True)
        .order_by("nome")
    )


def _obter_diagnosticos_por_produto():
    if Diagnostico is None:
        return {}

    registros = (
        Diagnostico.objects
        .filter(produto__isnull=False)
        .values("produto_id")
        .annotate(quantidade=Count("id"))
    )

    return {
        item["produto_id"]: item["quantidade"]
        for item in registros
    }


def _validar_imagem_upload(request):
    imagem = request.FILES.get("imagem")

    if not imagem:
        return

    if imagem.size > MAX_IMAGE_SIZE:
        raise ValidationError(
            "A imagem deve ter no máximo 4 MB."
        )

    content_type = (
        getattr(imagem, "content_type", "") or ""
    ).lower()

    tipos_permitidos = {
        "image/jpeg",
        "image/png",
        "image/webp",
    }

    if content_type and content_type not in tipos_permitidos:
        raise ValidationError(
            "Formato de imagem não permitido. "
            "Utilize JPG, PNG ou WEBP."
        )


@login_required
def produtos(request):
    produtos_qs = (
        ProdutoAgricola.objects
        .prefetch_related("categorias")
        .order_by("nome")
    )

    total_produtos = (
        ProdutoAgricola.objects
        .count()
    )

    total_disponiveis = (
        ProdutoAgricola.objects
        .filter(ativo=True)
        .count()
    )

    total_categorias_associadas = (
        Categoria.objects
        .filter(produtos__isnull=False)
        .distinct()
        .count()
    )

    total_diagnosticos = 0

    if Diagnostico is not None:
        total_diagnosticos = (
            Diagnostico.objects
            .filter(produto__isnull=False)
            .count()
        )

    diagnosticos_por_produto = (
        _obter_diagnosticos_por_produto()
    )

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

    contexto = {
        "produtos": produtos_lista,
        "total_produtos": total_produtos,
        "total_disponiveis": total_disponiveis,
        "total_categorias_associadas": (
            total_categorias_associadas
        ),
        "total_diagnosticos": total_diagnosticos,
    }

    return render(
        request,
        "produtos/produtos.html",
        contexto
    )


@login_required
def criar_produto(request):
    if request.method == "POST":
        form = ProdutoForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():
            try:
                _validar_imagem_upload(request)

                with transaction.atomic():
                    produto = form.save(
                        commit=False
                    )

                    if hasattr(
                        produto,
                        "usuario_id"
                    ):
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

            except ValidationError as exc:
                mensagens = (
                    exc.messages
                    if hasattr(exc, "messages")
                    else [str(exc)]
                )

                for mensagem in mensagens:
                    messages.error(
                        request,
                        mensagem
                    )

            except Exception:
                logger.exception(
                    "Erro ao cadastrar produto."
                )

                messages.error(
                    request,
                    "Não foi possível cadastrar "
                    "o produto. Verifique os dados "
                    "e tente novamente."
                )
    else:
        form = ProdutoForm()

    contexto = {
        "form": form,
        "titulo": "Cadastrar Produto",
        "modo": "criar",
        "categorias": _categorias_ativas(),
        "categorias_disponiveis": (
            _categorias_ativas()
        ),
    }

    return render(
        request,
        "produtos/criar_produto.html",
        contexto
    )


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

    ultimos_diagnosticos = []

    if Diagnostico is not None:
        ultimos_diagnosticos = (
            Diagnostico.objects
            .filter(produto=produto)
            .order_by("-data_criacao")[:5]
        )

    ultimo_diagnostico = (
        ultimos_diagnosticos[0]
        if ultimos_diagnosticos
        else None
    )

    contexto = {
        "produto": produto,
        "categorias_produto": categorias_produto,
        "total_categorias": (
            categorias_produto.count()
        ),
        "total_diagnosticos": total_diagnosticos,
        "ultimos_diagnosticos": (
            ultimos_diagnosticos
        ),
        "ultimo_diagnostico": (
            ultimo_diagnostico
        ),
    }

    return render(
        request,
        "produtos/produto_detalhes.html",
        contexto
    )


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
                _validar_imagem_upload(request)

                with transaction.atomic():
                    produto = form.save(
                        commit=False
                    )

                    if (
                        hasattr(
                            produto,
                            "usuario_id"
                        )
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

            except ValidationError as exc:
                mensagens = (
                    exc.messages
                    if hasattr(exc, "messages")
                    else [str(exc)]
                )

                for mensagem in mensagens:
                    messages.error(
                        request,
                        mensagem
                    )

            except Exception:
                logger.exception(
                    "Erro ao atualizar produto %s.",
                    produto.pk
                )

                messages.error(
                    request,
                    "Não foi possível atualizar "
                    "o produto. Verifique os dados "
                    "e tente novamente."
                )
    else:
        form = ProdutoForm(
            instance=produto
        )

    categorias_produto = (
        produto.categorias
        .all()
        .order_by("nome")
    )

    categorias_disponiveis = (
        _categorias_ativas()
    )

    contexto = {
        "form": form,
        "produto": produto,
        "categorias": categorias_disponiveis,
        "categorias_produto": categorias_produto,
        "categorias_disponiveis": (
            categorias_disponiveis
        ),
        "titulo": "Editar Produto",
        "modo": "editar",
    }

    return render(
        request,
        "produtos/editar_produto.html",
        contexto
    )


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

        except Exception:
            logger.exception(
                "Erro ao eliminar produto %s.",
                produto.pk
            )

            messages.error(
                request,
                "Não foi possível eliminar "
                "o produto. Tente novamente."
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
