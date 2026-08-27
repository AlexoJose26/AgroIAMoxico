from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404, redirect, render

from produtos.models import ProdutoAgricola

from .ai_service import analisar_imagem
from .models import Diagnostico


# ============================================================
# CONTADORES GERAIS
# ============================================================

def obter_contadores():
    """
    Obtém os principais contadores utilizados pelo módulo
    de diagnóstico.
    """

    return {
        "total_diagnosticos": Diagnostico.objects.count(),
        "total_produtos": ProdutoAgricola.objects.filter(
            ativo=True
        ).count(),
        "precisao_ia": 92,
    }


# ============================================================
# ESTATÍSTICAS DO UTILIZADOR
# ============================================================

def obter_estatisticas_utilizador(request):
    """
    Obtém estatísticas dos diagnósticos realizados pelo
    utilizador autenticado.
    """

    queryset = Diagnostico.objects.filter(
        usuario=request.user
    )

    total = queryset.count()

    concluidos = queryset.filter(
        status="concluido"
    ).count()

    erros = queryset.filter(
        status="erro"
    ).count()

    processando = queryset.filter(
        status="processando"
    ).count()

    pendentes = queryset.filter(
        status="pendente"
    ).count()

    problemas = (
        queryset
        .filter(status="concluido")
        .exclude(resultado="saudavel")
        .count()
    )

    saudaveis = queryset.filter(
        status="concluido",
        resultado="saudavel",
    ).count()

    media_confianca = (
        queryset
        .filter(status="concluido")
        .aggregate(
            media=Avg("confianca")
        )["media"]
    )

    if media_confianca is None:
        media_confianca = 0

    return {
        "total_diagnosticos_usuario": total,
        "diagnosticos_concluidos": concluidos,
        "diagnosticos_erros": erros,
        "diagnosticos_processando": processando,
        "diagnosticos_pendentes": pendentes,
        "diagnosticos_problemas": problemas,
        "diagnosticos_saudaveis": saudaveis,
        "confianca_media": round(
            float(media_confianca),
            2,
        ),
    }


# ============================================================
# ESTATÍSTICAS DE UM PRODUTO
# ============================================================

def obter_estatisticas_produto(request, produto):
    """
    Obtém estatísticas específicas dos diagnósticos de
    um determinado produto pertencente ao utilizador.
    """

    queryset = Diagnostico.objects.filter(
        usuario=request.user,
        produto=produto,
    )

    total = queryset.count()

    concluidos = queryset.filter(
        status="concluido"
    ).count()

    saudaveis = queryset.filter(
        status="concluido",
        resultado="saudavel",
    ).count()

    problemas = (
        queryset
        .filter(status="concluido")
        .exclude(resultado="saudavel")
        .count()
    )

    erros = queryset.filter(
        status="erro"
    ).count()

    media_confianca = (
        queryset
        .filter(status="concluido")
        .aggregate(
            media=Avg("confianca")
        )["media"]
    )

    if media_confianca is None:
        media_confianca = 0

    ultimo_diagnostico = (
        queryset
        .select_related("produto", "usuario")
        .order_by("-data_criacao")
        .first()
    )

    return {
        "total_diagnosticos_produto": total,
        "diagnosticos_concluidos_produto": concluidos,
        "diagnosticos_saudaveis_produto": saudaveis,
        "diagnosticos_problemas_produto": problemas,
        "diagnosticos_erros_produto": erros,
        "confianca_media_produto": round(
            float(media_confianca),
            2,
        ),
        "ultimo_diagnostico": ultimo_diagnostico,
    }


# ============================================================
# ÚLTIMOS DIAGNÓSTICOS DO UTILIZADOR
# ============================================================

def obter_ultimos_diagnosticos(request, limite=5):
    """
    Retorna os últimos diagnósticos realizados pelo
    utilizador autenticado.
    """

    return (
        Diagnostico.objects
        .filter(
            usuario=request.user
        )
        .select_related(
            "produto",
            "usuario",
        )
        .order_by(
            "-data_criacao"
        )[:limite]
    )


# ============================================================
# PRODUTOS ATIVOS
# ============================================================

def obter_produtos_ativos():
    """
    Retorna os produtos agrícolas ativos.
    """

    return (
        ProdutoAgricola.objects
        .filter(
            ativo=True
        )
        .prefetch_related(
            "categorias"
        )
        .order_by(
            "nome"
        )
    )


# ============================================================
# LER IMAGEM DO PRODUTO
# ============================================================

def obter_imagem_produto(produto):
    """
    Lê a imagem cadastrada no produto e devolve os bytes.
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
# NORMALIZAR RESULTADO DA IA
# ============================================================

def normalizar_resultado_ia(resultado_ia):
    """
    Normaliza a resposta devolvida pelo serviço de IA.
    """

    if not resultado_ia:
        raise ValueError(
            "A inteligência artificial não retornou "
            "nenhum resultado."
        )

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

    mensagem_compatibilidade = resultado_ia.get(
        "mensagem_compatibilidade",
        "",
    )

    baixa_confianca = resultado_ia.get(
        "baixa_confianca",
        False,
    )

    # --------------------------------------------------------
    # CONFIANÇA
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # CLASSE
    # --------------------------------------------------------

    classe = str(
        classe or ""
    ).strip()

    if not classe:
        classe = "resultado_nao_identificado"

    # --------------------------------------------------------
    # RESULTADO
    # --------------------------------------------------------

    resultados_validos = {
        "saudavel",
        "doenca",
        "praga",
        "fungo",
        "deficiencia",
        "outro",
        "indeterminado",
    }

    resultado = str(
        resultado or ""
    ).strip().lower()

    if resultado not in resultados_validos:
        resultado = "indeterminado"

    return {
        "classe": classe,
        "produtos": produtos,
        "confianca": confianca,
        "resultado": resultado,
        "doenca": doenca,
        "descricao": descricao,
        "recomendacoes": recomendacoes,
        "produto_compativel": produto_compativel,
        "mensagem_compatibilidade": (
            mensagem_compatibilidade
        ),
        "baixa_confianca": baixa_confianca,
    }


# ============================================================
# CONSTRUIR OBSERVAÇÕES
# ============================================================

def construir_observacoes(
    produto,
    classe,
    produto_compativel=True,
    baixa_confianca=False,
    mensagem_compatibilidade="",
):
    """
    Cria as observações que serão armazenadas no diagnóstico.
    """

    observacoes = []

    observacoes.append(
        f"Produto analisado: {produto.nome}."
    )

    observacoes.append(
        f"Classe identificada pela IA: {classe}."
    )

    if not produto_compativel:
        observacoes.append(
            "A imagem analisada pode não corresponder "
            "ao produto cadastrado. Verifique a imagem "
            "e o produto."
        )

    if baixa_confianca:
        observacoes.append(
            "A análise apresentou confiança relativamente "
            "baixa. Recomenda-se uma imagem mais nítida "
            "e confirmação técnica."
        )

    if mensagem_compatibilidade:
        observacoes.append(
            str(mensagem_compatibilidade)
        )

    return "\n\n".join(
        observacoes
    )


# ============================================================
# PÁGINA PRINCIPAL DO DIAGNÓSTICO
# ============================================================

@login_required
def diagnostico(request, produto_id=None):
    """
    Página principal do diagnóstico.

    URL:
        /diagnostico/

    ou:

        /diagnostico/produto/<produto_id>/
    """

    produtos = obter_produtos_ativos()

    produto = None

    if produto_id is not None:
        produto = get_object_or_404(
            ProdutoAgricola.objects.prefetch_related(
                "categorias"
            ),
            id=produto_id,
            ativo=True,
        )

    ultimos_diagnosticos = (
        obter_ultimos_diagnosticos(
            request
        )
    )

    context = {
        "produtos": produtos,
        "produto": produto,

        "imagem_produto": (
            produto.imagem
            if produto and produto.imagem
            else None
        ),

        "resultado": None,
        "diagnostico": None,

        "ultimos_diagnosticos": (
            ultimos_diagnosticos
        ),

        **obter_contadores(),

        **obter_estatisticas_utilizador(
            request
        ),
    }

    return render(
        request,
        "diagnostico/diagnostico.html",
        context,
    )


# ============================================================
# EXECUTAR DIAGNÓSTICO
# ============================================================

@login_required
def analisar(request, produto_id=None):
    """
    Executa o diagnóstico.

    Pode ser chamado por:

        /diagnostico/produto/<produto_id>/analisar/

    ou:

        /diagnostico/analisar/
    """

    # ========================================================
    # MÉTODO HTTP
    # ========================================================

    if request.method != "POST":

        if produto_id is not None:
            return redirect(
                "diagnostico:diagnostico_produto",
                produto_id=produto_id,
            )

        return redirect(
            "diagnostico:diagnostico"
        )

    # ========================================================
    # IDENTIFICAR PRODUTO
    # ========================================================

    produto_id_post = request.POST.get(
        "produto_id"
    )

    produto_id_final = (
        produto_id
        or produto_id_post
    )

    if not produto_id_final:

        messages.error(
            request,
            "Nenhum produto foi selecionado para o diagnóstico.",
        )

        return redirect(
            "diagnostico:diagnostico"
        )

    # ========================================================
    # BUSCAR PRODUTO
    # ========================================================

    produto = get_object_or_404(
        ProdutoAgricola.objects.prefetch_related(
            "categorias"
        ),
        pk=produto_id_final,
        ativo=True,
    )

    # ========================================================
    # VERIFICAR IMAGEM
    # ========================================================

    if not produto.imagem:

        messages.error(
            request,
            (
                "Não é possível realizar o diagnóstico "
                "porque este produto ainda não possui "
                "uma imagem cadastrada."
            ),
        )

        return redirect(
            "diagnostico:diagnostico_produto",
            produto_id=produto.id,
        )

    diagnostico_registo = None

    try:

        # ====================================================
        # LER IMAGEM
        # ====================================================

        imagem_bytes = obter_imagem_produto(
            produto
        )

        nome_imagem = Path(
            produto.imagem.name
        ).name

        imagem_para_ia = ContentFile(
            imagem_bytes,
            name=nome_imagem,
        )

        # ====================================================
        # EXECUTAR IA
        # ====================================================

        resultado_ia = analisar_imagem(
            imagem_para_ia,
            produto=produto,
        )

        # ====================================================
        # NORMALIZAR RESULTADO
        # ====================================================

        dados = normalizar_resultado_ia(
            resultado_ia
        )

        classe = dados["classe"]
        produtos = dados["produtos"]
        confianca = dados["confianca"]
        resultado = dados["resultado"]
        doenca = dados["doenca"]
        descricao = dados["descricao"]
        recomendacoes = dados["recomendacoes"]

        produto_compativel = (
            dados["produto_compativel"]
        )

        mensagem_compatibilidade = (
            dados["mensagem_compatibilidade"]
        )

        baixa_confianca = (
            dados["baixa_confianca"]
        )

        # ====================================================
        # CONSTRUIR OBSERVAÇÕES
        # ====================================================

        observacoes_texto = construir_observacoes(
            produto=produto,
            classe=classe,
            produto_compativel=produto_compativel,
            baixa_confianca=baixa_confianca,
            mensagem_compatibilidade=(
                mensagem_compatibilidade
            ),
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

            diagnostico_registo.imagem.save(
                nome_imagem,
                ContentFile(imagem_bytes),
                save=False,
            )

            diagnostico_registo.save()

        # ====================================================
        # URL DA IMAGEM
        # ====================================================

        imagem_url = ""

        if diagnostico_registo.imagem:
            imagem_url = (
                diagnostico_registo.imagem.url
            )

        elif produto.imagem:
            imagem_url = (
                produto.imagem.url
            )

        # ====================================================
        # RESULTADO PARA A PÁGINA
        # ====================================================

        resultado_pagina = {
            "id": diagnostico_registo.id,

            "produto_id": produto.id,

            "produto_nome": produto.nome,

            "imagem_url": imagem_url,

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

            "produto_compativel": (
                produto_compativel
            ),

            "mensagem_compatibilidade": (
                mensagem_compatibilidade
            ),

            "baixa_confianca": (
                baixa_confianca
            ),
        }

        # ====================================================
        # HISTÓRICO RECENTE
        # ====================================================

        ultimos_diagnosticos = (
            obter_ultimos_diagnosticos(
                request
            )
        )

        # ====================================================
        # CONTEXTO
        # ====================================================

        context = {
            "produtos": (
                obter_produtos_ativos()
            ),

            "produto": produto,

            "imagem_produto": (
                produto.imagem
                if produto.imagem
                else None
            ),

            "resultado": resultado_pagina,

            "diagnostico": (
                diagnostico_registo
            ),

            "ultimos_diagnosticos": (
                ultimos_diagnosticos
            ),

            **obter_contadores(),

            **obter_estatisticas_utilizador(
                request
            ),
        }

        messages.success(
            request,
            "Diagnóstico concluído com sucesso.",
        )

        return render(
            request,
            "diagnostico/diagnostico.html",
            context,
        )

    # ========================================================
    # ERRO
    # ========================================================

    except Exception as exc:

        # ====================================================
        # REGISTRAR ERRO
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

            try:

                imagem_erro = (
                    obter_imagem_produto(
                        produto
                    )
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
        # MENSAGEM AMIGÁVEL
        # ====================================================

        mensagem_erro = str(exc)

        mensagem_erro_lower = (
            mensagem_erro.lower()
        )

        if "model.keras está vazio" in mensagem_erro_lower:

            mensagem_usuario = (
                "O diagnóstico ainda não pode ser realizado "
                "porque o modelo de inteligência artificial "
                "ainda não foi treinado."
            )

        elif "modelo de ia não encontrado" in mensagem_erro_lower:

            mensagem_usuario = (
                "O modelo de inteligência artificial ainda "
                "não está configurado."
            )

        elif "class_names.json" in mensagem_erro_lower:

            mensagem_usuario = (
                "A configuração das classes da inteligência "
                "artificial ainda não está completa."
            )

        else:

            mensagem_usuario = (
                "Não foi possível concluir o diagnóstico. "
                "Verifique se o produto possui uma imagem "
                "válida e se o modelo de IA está configurado."
            )

        messages.error(
            request,
            mensagem_usuario,
        )

        # ====================================================
        # VOLTAR PARA O PRODUTO
        # ====================================================

        if produto is not None:

            return redirect(
                "diagnostico:diagnostico_produto",
                produto_id=produto.id,
            )

        return redirect(
            "diagnostico:diagnostico"
        )


# ============================================================
# HISTÓRICO DE UM PRODUTO
# ============================================================

@login_required
def historico_produto(request, produto_id):
    """
    Mostra exclusivamente o histórico de diagnósticos
    de um produto específico.

    URL:

        /diagnostico/historico/produto/<produto_id>/
    """

    # ========================================================
    # PRODUTO
    # ========================================================

    produto = get_object_or_404(
        ProdutoAgricola.objects.prefetch_related(
            "categorias"
        ),
        pk=produto_id,
        ativo=True,
    )

    # ========================================================
    # HISTÓRICO DO PRODUTO
    # ========================================================

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

    # ========================================================
    # ESTATÍSTICAS
    # ========================================================

    estatisticas = (
        obter_estatisticas_produto(
            request,
            produto,
        )
    )

    # ========================================================
    # ÚLTIMO DIAGNÓSTICO
    # ========================================================

    ultimo_diagnostico = (
        estatisticas[
            "ultimo_diagnostico"
        ]
    )

    # ========================================================
    # PRIMEIRO DIAGNÓSTICO
    # ========================================================

    primeiro_diagnostico = (
        diagnosticos
        .order_by(
            "data_criacao"
        )
        .first()
    )

    # ========================================================
    # RESULTADOS PARA GRÁFICOS
    # ========================================================

    resultados = (
        diagnosticos
        .filter(
            status="concluido"
        )
        .values(
            "resultado"
        )
        .annotate(
            total=Count("id")
        )
        .order_by(
            "-total"
        )
    )

    # ========================================================
    # DADOS PARA GRÁFICO
    # ========================================================

    diagnosticos_grafico = list(
        diagnosticos
        .filter(
            status="concluido"
        )
        .values(
            "id",
            "confianca",
            "resultado",
            "data_criacao",
            "doenca_identificada",
        )
        .order_by(
            "data_criacao"
        )
    )

    # ========================================================
    # EVOLUÇÃO DA CONFIANÇA
    # ========================================================

    evolucao_confianca = []

    for item in diagnosticos_grafico:

        evolucao_confianca.append(
            {
                "id": item["id"],

                "confianca": float(
                    item["confianca"] or 0
                ),

                "resultado": item["resultado"],

                "doenca": (
                    item["doenca_identificada"]
                    or ""
                ),

                "data": (
                    item["data_criacao"].strftime(
                        "%d/%m/%Y"
                    )
                    if item["data_criacao"]
                    else ""
                ),
            }
        )

    # ========================================================
    # CONTEXTO
    # ========================================================

    context = {
        "produto": produto,

        "diagnosticos": diagnosticos,

        "ultimo_diagnostico": (
            ultimo_diagnostico
        ),

        "primeiro_diagnostico": (
            primeiro_diagnostico
        ),

        "resultados": resultados,

        "evolucao_confianca": (
            evolucao_confianca
        ),

        **estatisticas,

        **obter_contadores(),

        **obter_estatisticas_utilizador(
            request
        ),
    }

    return render(
        request,
        "diagnostico/historico_produto.html",
        context,
    )


# ============================================================
# DETALHE COMPLETO DO DIAGNÓSTICO
# ============================================================

@login_required
def detalhe_diagnostico(request, diagnostico_id):
    """
    Mostra todas as informações de um diagnóstico específico.

    URL:

        /diagnostico/detalhe/<diagnostico_id>/

    Template:

        diagnostico/detalhe.html
    """

    diagnostico_obj = get_object_or_404(
        Diagnostico.objects.select_related(
            "produto",
            "usuario",
        ),
        pk=diagnostico_id,
        usuario=request.user,
    )

    # ========================================================
    # PRODUTO
    # ========================================================

    produto = diagnostico_obj.produto

    # ========================================================
    # CONTEXTO
    # ========================================================

    context = {
        "diagnostico": diagnostico_obj,

        "produto": produto,

        **obter_contadores(),

        **obter_estatisticas_utilizador(
            request
        ),
    }

    return render(
        request,
        "diagnostico/detalhe.html",
        context,
    )
