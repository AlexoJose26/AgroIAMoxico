from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from produtos.models import ProdutoAgricola

from .ai_service import analisar_imagem
from .models import Diagnostico


# ============================================================
# FUNÇÃO AUXILIAR — CONTADORES
# ============================================================

def obter_contadores():
    """
    Retorna os contadores utilizados nas páginas de diagnóstico.
    """

    return {
        "total_diagnosticos": Diagnostico.objects.count(),
        "total_produtos": ProdutoAgricola.objects.count(),

        # Este valor pode ser substituído futuramente
        # pela precisão real obtida durante a validação
        # do modelo treinado.
        "precisao_ia": 92,
    }


# ============================================================
# FUNÇÃO AUXILIAR — ÚLTIMOS DIAGNÓSTICOS
# ============================================================

def obter_ultimos_diagnosticos(request, produto):
    """
    Retorna os últimos 5 diagnósticos realizados pelo
    utilizador para determinado produto.
    """

    return (
        Diagnostico.objects
        .filter(
            usuario=request.user,
            produto=produto,
        )
        .order_by("-data_criacao")[:5]
    )


# ============================================================
# FUNÇÃO AUXILIAR — LER IMAGEM DO PRODUTO
# ============================================================

def obter_imagem_produto(produto):
    """
    Abre a imagem cadastrada no ProdutoAgricola e retorna
    os seus bytes.

    A função não altera a imagem original.
    """

    if not produto.imagem:
        raise ValueError(
            "Este produto não possui uma imagem cadastrada."
        )

    try:
        produto.imagem.open("rb")

        try:
            imagem_bytes = produto.imagem.read()
        finally:
            produto.imagem.close()

    except Exception as exc:
        raise ValueError(
            "Não foi possível abrir a imagem cadastrada "
            "para este produto."
        ) from exc

    if not imagem_bytes:
        raise ValueError(
            "A imagem cadastrada deste produto está vazia."
        )

    return imagem_bytes


# ============================================================
# PÁGINA DE DIAGNÓSTICO
# ============================================================

@login_required
def diagnostico(request, produto_id):
    """
    Abre a página de diagnóstico de um produto.

    IMPORTANTE:
    A imagem cadastrada no produto é mostrada automaticamente.
    O utilizador não precisa enviar outra imagem.
    """

    produto = get_object_or_404(
        ProdutoAgricola,
        id=produto_id,
    )

    ultimos_diagnosticos = obter_ultimos_diagnosticos(
        request,
        produto,
    )

    context = {
        "produto": produto,
        "ultimos_diagnosticos": ultimos_diagnosticos,

        # Informa à página que a imagem vem automaticamente
        # do produto cadastrado.
        "imagem_produto": produto.imagem if produto.imagem else None,

        # Ainda não existe resultado nesta primeira abertura.
        "resultado": None,
        "diagnostico": None,

        **obter_contadores(),
    }

    return render(
        request,
        "diagnostico/diagnostico.html",
        context,
    )


# ============================================================
# EXECUTAR DIAGNÓSTICO COM IA
# ============================================================

@login_required
def analisar(request, produto_id):
    """
    Executa o diagnóstico utilizando AUTOMATICAMENTE a imagem
    cadastrada no produto.

    Não recebe uma nova imagem do utilizador.

    Fluxo:

        Produto
           ↓
        imagem cadastrada
           ↓
        analisar_imagem()
           ↓
        resultado da IA
           ↓
        Diagnostico
           ↓
        página de resultado
    """

    # ========================================================
    # ACEITAR SOMENTE POST
    # ========================================================

    if request.method != "POST":
        return redirect(
            "diagnostico:diagnostico",
            produto_id=produto_id,
        )

    # ========================================================
    # BUSCAR PRODUTO
    # ========================================================

    produto = get_object_or_404(
        ProdutoAgricola,
        id=produto_id,
    )

    # ========================================================
    # VERIFICAR IMAGEM DO PRODUTO
    # ========================================================

    if not produto.imagem:
        messages.error(
            request,
            (
                "Não é possível realizar o diagnóstico porque "
                "este produto ainda não possui uma imagem "
                "cadastrada."
            ),
        )

        return redirect(
            "diagnostico:diagnostico",
            produto_id=produto.id,
        )

    diagnostico_registo = None

    try:

        # ====================================================
        # LER IMAGEM CADASTRADA
        # ====================================================

        imagem_bytes = obter_imagem_produto(produto)

        # ====================================================
        # CRIAR ARQUIVO EM MEMÓRIA
        # ====================================================

        nome_imagem = Path(
            produto.imagem.name
        ).name

        imagem_para_ia = ContentFile(
            imagem_bytes,
            name=nome_imagem,
        )

        # ====================================================
        # EXECUTAR INTELIGÊNCIA ARTIFICIAL
        # ====================================================

        resultado_ia = analisar_imagem(
            imagem_para_ia,
            produto=produto,
        )

        # ====================================================
        # VALIDAR RETORNO
        # ====================================================

        if not resultado_ia:
            raise ValueError(
                "A inteligência artificial não retornou "
                "nenhum resultado."
            )

        # ====================================================
        # OBTER DADOS DO RESULTADO
        # ====================================================

        classe = resultado_ia.get(
            "classe",
            "",
        )

        produtos = resultado_ia.get(
            "produtos",
            "",
        )

        confianca = resultado_ia.get(
            "confianca",
            0,
        )

        resultado = resultado_ia.get(
            "resultado",
            "indeterminado",
        )

        doenca = resultado_ia.get(
            "doenca",
            "",
        )

        descricao = resultado_ia.get(
            "descricao",
            "",
        )

        recomendacoes = resultado_ia.get(
            "recomendacoes",
            "",
        )

        produto_compativel = resultado_ia.get(
            "produto_compativel",
            True,
        )

        mensagem_compatibilidade = (
            resultado_ia.get(
                "mensagem_compatibilidade",
                "",
            )
        )

        baixa_confianca = resultado_ia.get(
            "baixa_confianca",
            False,
        )

        # ====================================================
        # NORMALIZAR CONFIANÇA
        # ====================================================

        try:
            confianca = float(confianca)
        except (TypeError, ValueError):
            confianca = 0.0

        confianca = max(
            0.0,
            min(
                100.0,
                confianca,
            ),
        )

        # ====================================================
        # NORMALIZAR CLASSE
        # ====================================================

        classe = str(classe).strip()

        if not classe:
            classe = "resultado_nao_identificado"

        # ====================================================
        # VALIDAR TIPO DE RESULTADO
        # ====================================================

        resultados_validos = {
            "saudavel",
            "doenca",
            "praga",
            "fungo",
            "deficiencia",
            "outro",
            "indeterminado",
        }

        if resultado not in resultados_validos:
            resultado = "indeterminado"

        # ====================================================
        # CONSTRUIR OBSERVAÇÕES
        # ====================================================

        observacoes = []

        if cultura:
            observacoes.append(
                f"Cultura identificada pela IA: {cultura}."
            )

        if not produto_compativel:
            observacoes.append(
                (
                    "A cultura identificada pela IA pode não "
                    "corresponder ao produto cadastrado. "
                    "Verifique a imagem e o produto."
                )
            )

        if baixa_confianca:
            observacoes.append(
                (
                    "A análise apresentou confiança "
                    "relativamente baixa. Recomenda-se uma "
                    "imagem mais nítida e confirmação técnica."
                )
            )

        if mensagem_compatibilidade:
            observacoes.append(
                mensagem_compatibilidade
            )

        observacoes_texto = "\n\n".join(
            observacoes
        )

        # ====================================================
        # GUARDAR DIAGNÓSTICO
        # ====================================================

        with transaction.atomic():

            diagnostico_registo = Diagnostico(
                usuario=request.user,
                produto=produto,

                classe_identificada=classe,

                resultado=resultado,

                doenca_identificada=doenca,

                confianca=round(
                    confianca,
                    2,
                ),

                descricao_resultado=descricao,

                recomendacoes=recomendacoes,

                observacoes=observacoes_texto,

                status="concluido",

                erro="",
            )

            # =================================================
            # GUARDAR CÓPIA DA IMAGEM DO PRODUTO
            # =================================================

            diagnostico_registo.imagem.save(
                nome_imagem,
                ContentFile(imagem_bytes),
                save=False,
            )

            diagnostico_registo.save()

        # ====================================================
        # URL DA IMAGEM
        # ====================================================

        if diagnostico_registo.imagem:
            imagem_url = diagnostico_registo.imagem.url
        elif produto.imagem:
            imagem_url = produto.imagem.url
        else:
            imagem_url = ""

        # ====================================================
        # RESULTADO PARA A PÁGINA
        # ====================================================

        resultado_pagina = {
            "id": diagnostico_registo.id,

            # Produto
            "produto_id": produto.id,
            "produto_nome": produto.nome,

            # Imagem
            "imagem_url": imagem_url,

            # IA
            "classe": classe,
            "produtos": produtos,
            "confianca": round(
                confianca,
                2,
            ),
            "resultado": resultado,
            "doenca": doenca,
            "descricao": descricao,
            "recomendacoes": recomendacoes,

            # Compatibilidade
            "produto_compativel": produto_compativel,
            "mensagem_compatibilidade": (
                mensagem_compatibilidade
            ),

            # Confiança
            "baixa_confianca": baixa_confianca,
        }

        # ====================================================
        # ATUALIZAR HISTÓRICO
        # ====================================================

        ultimos_diagnosticos = (
            Diagnostico.objects
            .filter(
                usuario=request.user,
                produto=produto,
            )
            .order_by("-data_criacao")[:5]
        )

        # ====================================================
        # CONTEXTO
        # ====================================================

        context = {
            "produto": produto,

            "imagem_produto": (
                produto.imagem
                if produto.imagem
                else None
            ),

            "resultado": resultado_pagina,

            "diagnostico": diagnostico_registo,

            "ultimos_diagnosticos": (
                ultimos_diagnosticos
            ),

            **obter_contadores(),
        }

        # ====================================================
        # MENSAGEM DE SUCESSO
        # ====================================================

        messages.success(
            request,
            "Diagnóstico concluído com sucesso.",
        )

        # ====================================================
        # MOSTRAR RESULTADO NA MESMA PÁGINA
        # ====================================================

        return render(
            request,
            "diagnostico/diagnostico.html",
            context,
        )

    # ========================================================
    # ERRO DURANTE O DIAGNÓSTICO
    # ========================================================

    except Exception as exc:

        # ====================================================
        # TENTAR REGISTRAR O ERRO
        # ====================================================

        try:

            erro_registo = Diagnostico(
                usuario=request.user,
                produto=produto,

                classe_identificada="",

                resultado="indeterminado",

                doenca_identificada="",

                confianca=0,

                descricao_resultado="",

                recomendacoes="",

                observacoes="",

                status="erro",

                erro=str(exc),
            )

            # ================================================
            # GUARDAR CÓPIA DA IMAGEM
            # ================================================

            try:

                imagem_erro = obter_imagem_produto(
                    produto
                )

                nome_imagem_erro = Path(
                    produto.imagem.name
                ).name

                erro_registo.imagem.save(
                    nome_imagem_erro,
                    ContentFile(imagem_erro),
                    save=False,
                )

            except Exception:
                pass

            erro_registo.save()

        except Exception:
            pass

        # ====================================================
        # MENSAGEM AMIGÁVEL PARA O UTILIZADOR
        # ====================================================

        mensagem_erro = str(exc)

        # ----------------------------------------------------
        # TRATAMENTO ESPECÍFICO DO MODEL.KERAS
        # ----------------------------------------------------

        if (
            "model.keras está vazio"
            in mensagem_erro.lower()
        ):

            mensagem_usuario = (
                "O diagnóstico ainda não pode ser realizado "
                "porque o modelo de inteligência artificial "
                "ainda não foi treinado. A imagem cadastrada "
                "do produto foi encontrada corretamente, mas "
                "é necessário configurar o modelo de IA "
                "antes de realizar diagnósticos."
            )

        elif (
            "modelo de ia não encontrado"
            in mensagem_erro.lower()
        ):

            mensagem_usuario = (
                "O modelo de inteligência artificial ainda "
                "não está configurado. A imagem do produto "
                "foi encontrada, mas o sistema precisa do "
                "modelo treinado para realizar o diagnóstico."
            )

        elif (
            "class_names.json"
            in mensagem_erro.lower()
        ):

            mensagem_usuario = (
                "A configuração das classes da inteligência "
                "artificial ainda não está completa. "
                "Verifique o arquivo class_names.json."
            )

        else:

            mensagem_usuario = (
                "Não foi possível concluir o diagnóstico "
                "deste produto. Verifique se a imagem está "
                "válida e se o modelo de inteligência "
                "artificial está corretamente configurado."
            )

        messages.error(
            request,
            mensagem_usuario,
        )

        # ====================================================
        # VOLTAR PARA A PÁGINA DO PRODUTO
        # ====================================================

        return redirect(
            "diagnostico:diagnostico",
            produto_id=produto.id,
        )


# ============================================================
# HISTÓRICO DE DIAGNÓSTICOS
# ============================================================

@login_required
def historico(request):
    """
    Mostra o histórico de diagnósticos realizados
    pelo utilizador autenticado.
    """

    diagnosticos = (
        Diagnostico.objects
        .filter(
            usuario=request.user,
        )
        .select_related(
            "produto",
            "usuario",
        )
        .order_by(
            "-data_criacao"
        )
    )

    context = {
        "diagnosticos": diagnosticos,
        **obter_contadores(),
    }

    return render(
        request,
        "diagnostico/historico.html",
        context,
    )


# ============================================================
# HISTÓRICO DE UM PRODUTO
# ============================================================

@login_required
def historico_produto(request, produto_id):
    """
    Mostra somente os diagnósticos de determinado produto.
    """

    produto = get_object_or_404(
        ProdutoAgricola,
        id=produto_id,
    )

    diagnosticos = (
        Diagnostico.objects
        .filter(
            usuario=request.user,
            produto=produto,
        )
        .select_related(
            "produto",
            "usuario",
        )
        .order_by(
            "-data_criacao"
        )
    )

    context = {
        "produto": produto,
        "diagnosticos": diagnosticos,
        **obter_contadores(),
    }

    return render(
        request,
        "diagnostico/historico_produto.html",
        context,
    )


# ============================================================
# DETALHE DO DIAGNÓSTICO
# ============================================================

@login_required
def detalhe_diagnostico(
    request,
    diagnostico_id,
):
    """
    Mostra o resultado completo de um diagnóstico.

    O utilizador só pode visualizar os seus próprios
    diagnósticos.
    """

    diagnostico_obj = get_object_or_404(
        Diagnostico.objects.select_related(
            "produto",
            "usuario",
        ),
        id=diagnostico_id,
        usuario=request.user,
    )

    context = {
        "diagnostico": diagnostico_obj,
        "produto": diagnostico_obj.produto,
        **obter_contadores(),
    }

    return render(
        request,
        "diagnostico/detalhe.html",
        context,
    )
