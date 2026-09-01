from pathlib import Path

import mimetypes
import requests

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404, redirect, render

from produtos.models import ProdutoAgricola

from .models import Diagnostico



API_IA_URL = getattr(
    settings,
    "AGROIA_API_URL",
    "http://127.0.0.1:8001/analisar",
)

API_TIMEOUT = getattr(
    settings,
    "AGROIA_API_TIMEOUT",
    120,
)



def obter_contadores():
    return {
        "total_diagnosticos": Diagnostico.objects.count(),
        "total_produtos": (
            ProdutoAgricola.objects
            .filter(ativo=True)
            .count()
        ),
        "precisao_ia": 92,
    }


def obter_estatisticas_utilizador(request):
    queryset = (
        Diagnostico.objects
        .filter(usuario=request.user)
    )

    total = queryset.count()

    concluidos = (
        queryset
        .filter(status="concluido")
        .count()
    )

    erros = (
        queryset
        .filter(status="erro")
        .count()
    )

    processando = (
        queryset
        .filter(status="processando")
        .count()
    )

    pendentes = (
        queryset
        .filter(status="pendente")
        .count()
    )

    problemas = (
        queryset
        .filter(status="concluido")
        .exclude(resultado="saudavel")
        .count()
    )

    saudaveis = (
        queryset
        .filter(
            status="concluido",
            resultado="saudavel",
        )
        .count()
    )

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



def obter_estatisticas_produto(request, produto):
    queryset = (
        Diagnostico.objects
        .filter(
            usuario=request.user,
            produto=produto,
        )
    )

    total = queryset.count()

    concluidos = (
        queryset
        .filter(status="concluido")
        .count()
    )

    saudaveis = (
        queryset
        .filter(
            status="concluido",
            resultado="saudavel",
        )
        .count()
    )

    problemas = (
        queryset
        .filter(status="concluido")
        .exclude(resultado="saudavel")
        .count()
    )

    erros = (
        queryset
        .filter(status="erro")
        .count()
    )

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
        .select_related(
            "produto",
            "usuario",
        )
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



def obter_ultimos_diagnosticos(
    request,
    produto=None,
    limite=5,
):
    queryset = (
        Diagnostico.objects
        .filter(usuario=request.user)
        .select_related(
            "produto",
            "usuario",
        )
        .order_by("-data_criacao")
    )

    if produto is not None:
        queryset = queryset.filter(
            produto=produto
        )

    return queryset[:limite]



def obter_diagnosticos_produto(
    request,
    produto,
):
    return (
        Diagnostico.objects
        .filter(
            usuario=request.user,
            produto=produto,
        )
        .select_related(
            "produto",
            "usuario",
        )
        .order_by("-data_criacao")
    )



def obter_produtos_ativos():
    return (
        ProdutoAgricola.objects
        .filter(ativo=True)
        .prefetch_related("categorias")
        .order_by("nome")
    )



def obter_imagem_produto(produto):
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



def obter_content_type(nome_imagem):

    extensao = Path(nome_imagem).suffix.lower()

    tipos_permitidos = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }

    content_type = tipos_permitidos.get(extensao)

    if content_type is None:
        content_type, _ = mimetypes.guess_type(
            nome_imagem
        )

    if content_type not in {
        "image/jpeg",
        "image/png",
        "image/webp",
    }:
        raise ValueError(
            "Formato de imagem não suportado. "
            "Utilize JPG, PNG ou WEBP."
        )

    return content_type


def normalizar_resultado_ia(resultado_ia):
    if not resultado_ia:
        raise ValueError(
            "A inteligência artificial não retornou "
            "nenhum resultado."
        )

    classe = str(
        resultado_ia.get("classe", "") or ""
    ).strip()

    produto_detectado = str(
        resultado_ia.get("produto", "") or ""
    ).strip()

    problema = str(
        resultado_ia.get("problema", "") or ""
    ).strip()

    tipo = str(
        resultado_ia.get("tipo", "") or ""
    ).strip()

    principais_previsoes = (
        resultado_ia.get(
            "principais_previsoes",
            [],
        )
    )

    if not isinstance(
        principais_previsoes,
        list,
    ):
        principais_previsoes = []

    try:
        confianca = float(
            resultado_ia.get(
                "confianca",
                0,
            )
        )
    except (
        TypeError,
        ValueError,
    ):
        confianca = 0.0

    confianca = max(
        0.0,
        min(
            100.0,
            confianca,
        ),
    )

    tipo_lower = tipo.lower()
    problema_lower = problema.lower()

    # ========================================================
    # RESULTADO
    # ========================================================

    if (
        "healthy" in problema_lower
        or "saudável" in problema_lower
        or "saudavel" in problema_lower
        or "healthy" in tipo_lower
        or "saudável" in tipo_lower
        or "saudavel" in tipo_lower
    ):
        resultado = "saudavel"

    elif "praga" in tipo_lower:
        resultado = "praga"

    elif (
        "fung" in tipo_lower
        or "fungo" in tipo_lower
        or "fúng" in tipo_lower
    ):
        resultado = "fungo"

    elif (
        "viral" in tipo_lower
        or "virus" in tipo_lower
        or "vírus" in tipo_lower
    ):
        resultado = "doenca"

    elif "bacter" in tipo_lower:
        resultado = "doenca"

    elif "defici" in tipo_lower:
        resultado = "deficiencia"

    elif problema:
        resultado = "doenca"

    else:
        resultado = "indeterminado"

    # ========================================================
    # DOENÇA
    # ========================================================

    if resultado == "saudavel":
        doenca = ""

    elif problema:
        doenca = problema

    else:
        doenca = ""

    # ========================================================
    # DESCRIÇÃO
    # ========================================================

    if resultado == "saudavel":

        descricao = (
            "A inteligência artificial identificou "
            f"{produto_detectado or 'o produto analisado'} "
            "como saudável."
        )

    elif doenca:

        descricao = (
            "A inteligência artificial identificou "
            f"{doenca} em "
            f"{produto_detectado or 'o produto analisado'}."
        )

    else:

        descricao = (
            "A inteligência artificial não conseguiu "
            "determinar com precisão o problema presente "
            "na imagem."
        )

    # ========================================================
    # RECOMENDAÇÕES
    # ========================================================

    if resultado == "saudavel":

        recomendacoes = (
            "Continue acompanhando regularmente a cultura "
            "e mantenha boas práticas agrícolas. "
            "Faça novas análises caso sejam observadas "
            "alterações nas folhas, frutos ou demais partes "
            "da planta."
        )

    elif doenca:

        recomendacoes = (
            "Recomenda-se acompanhar a evolução dos sintomas "
            "e procurar orientação de um técnico agrícola "
            "ou agrónomo para confirmar o diagnóstico e "
            "definir o tratamento adequado."
        )

    else:

        recomendacoes = (
            "Recomenda-se realizar uma nova análise com "
            "uma imagem nítida e bem iluminada e, se "
            "necessário, procurar orientação técnica."
        )

    baixa_confianca = confianca < 60

    return {
        "classe": classe,
        "produto": produto_detectado,
        "produtos": produto_detectado,
        "problema": problema,
        "tipo": tipo,
        "confianca": confianca,
        "resultado": resultado,
        "doenca": doenca,
        "descricao": descricao,
        "recomendacoes": recomendacoes,
        "principais_previsoes": principais_previsoes,
        "produto_compativel": True,
        "mensagem_compatibilidade": "",
        "baixa_confianca": baixa_confianca,
    }


# ============================================================
# VERIFICAR COMPATIBILIDADE DO PRODUTO
# ============================================================

def verificar_compatibilidade(
    produto,
    produto_detectado,
):
    if not produto_detectado:
        return True, ""

    nome_cadastrado = (
        str(produto.nome)
        .strip()
        .lower()
    )

    nome_detectado = (
        str(produto_detectado)
        .strip()
        .lower()
    )

    equivalencias = {
        "milho": "milho",
        "corn maize": "milho",
        "corn": "milho",
        "maize": "milho",

        "tomate": "tomate",
        "tomato": "tomate",

        "batata": "batata",
        "potato": "batata",

        "maçã": "maca",
        "maca": "maca",
        "apple": "maca",

        "uva": "uva",
        "grape": "uva",

        "pêssego": "pessego",
        "pessego": "pessego",
        "peach": "pessego",

        "cereja": "cereja",
        "cherry": "cereja",

        "laranja": "laranja",
        "orange": "laranja",

        "soja": "soja",
        "soybean": "soja",

        "morango": "morango",
        "strawberry": "morango",

        "framboesa": "framboesa",
        "raspberry": "framboesa",

        "mirtilo": "mirtilo",
        "blueberry": "mirtilo",

        "pimentão": "pimentao",
        "pimentao": "pimentao",
        "pepper bell": "pimentao",

        "abóbora": "abobora",
        "abobora": "abobora",
        "squash": "abobora",
    }

    cadastrado_normalizado = equivalencias.get(
        nome_cadastrado,
        nome_cadastrado,
    )

    detectado_normalizado = equivalencias.get(
        nome_detectado,
        nome_detectado,
    )

    if (
        cadastrado_normalizado
        == detectado_normalizado
    ):
        return True, ""

    mensagem = (
        "A inteligência artificial identificou a imagem como "
        f"'{produto_detectado}', mas o produto cadastrado é "
        f"'{produto.nome}'. Verifique se a imagem corresponde "
        "ao produto selecionado."
    )

    return False, mensagem


# ============================================================
# CONSTRUIR OBSERVAÇÕES
# ============================================================

def construir_observacoes(
    produto,
    classe,
    produto_detectado="",
    tipo="",
    confianca=0,
    produto_compativel=True,
    baixa_confianca=False,
    mensagem_compatibilidade="",
):
    observacoes = []

    observacoes.append(
        f"Produto analisado: {produto.nome}."
    )

    if produto_detectado:
        observacoes.append(
            "Produto identificado pela IA: "
            f"{produto_detectado}."
        )

    if classe:
        observacoes.append(
            f"Classe identificada pela IA: {classe}."
        )

    if tipo:
        observacoes.append(
            f"Tipo de diagnóstico: {tipo}."
        )

    observacoes.append(
        f"Confiança da IA: {float(confianca):.2f}%."
    )

    if not produto_compativel:
        observacoes.append(
            "A imagem analisada pode não corresponder "
            "ao produto cadastrado. Verifique a imagem "
            "e o produto selecionado."
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

    return "\n\n".join(observacoes)


# ============================================================
# ENVIAR IMAGEM PARA A API FASTAPI
# ============================================================

def enviar_para_api_ia(
    imagem_bytes,
    nome_imagem,
):

    if not imagem_bytes:
        raise ValueError(
            "A imagem está vazia."
        )


    tamanho_maximo = 10 * 1024 * 1024

    if len(imagem_bytes) > tamanho_maximo:
        raise ValueError(
            "A imagem não pode ultrapassar 10 MB."
        )

    # ========================================================
    # CONTENT TYPE
    # ========================================================

    content_type = obter_content_type(
        nome_imagem
    )

    # ========================================================
    # REQUEST
    # ========================================================

    try:
        resposta = requests.post(
            API_IA_URL,
            files={
                "imagem": (
                    nome_imagem,
                    imagem_bytes,
                    content_type,
                )
            },
            timeout=API_TIMEOUT,
        )

    except requests.exceptions.ConnectionError as exc:

        raise ValueError(
            "Não foi possível conectar à API de "
            "inteligência artificial. Verifique se a "
            "AgroIA-API está em execução e se a URL "
            f"está correta: {API_IA_URL}"
        ) from exc

    except requests.exceptions.Timeout as exc:

        raise ValueError(
            "A inteligência artificial demorou demasiado "
            "tempo para responder. Tente novamente."
        ) from exc

    except requests.exceptions.RequestException as exc:

        raise ValueError(
            "Ocorreu um erro ao comunicar com a API "
            "de inteligência artificial."
        ) from exc

    # ========================================================
    # VERIFICAR STATUS HTTP
    # ========================================================

    if resposta.status_code != 200:

        try:
            erro_api = resposta.json()
        except ValueError:
            erro_api = {}

        mensagem_api = (
            erro_api.get("detail")
            or erro_api.get("erro")
            or "A API de inteligência artificial "
               "não conseguiu processar a imagem."
        )

        raise ValueError(
            str(mensagem_api)
        )

    # ========================================================
    # LER JSON
    # ========================================================

    try:
        dados = resposta.json()

    except ValueError as exc:

        raise ValueError(
            "A API de inteligência artificial devolveu "
            "uma resposta inválida."
        ) from exc

    # ========================================================
    # VERIFICAR SUCESSO
    # ========================================================

    if not dados.get("sucesso"):

        raise ValueError(
            "A API de inteligência artificial informou "
            "que a análise não foi concluída."
        )

    # ========================================================
    # OBTER RESULTADO
    # ========================================================

    resultado = dados.get(
        "resultado"
    )

    if not isinstance(
        resultado,
        dict,
    ):
        raise ValueError(
            "A API de inteligência artificial não "
            "devolveu um resultado válido."
        )

    return resultado



@login_required
def diagnostico(request, produto_id=None):
    """
    Página principal de diagnóstico.

    Sem produto_id:
        Mostra todos os produtos e o histórico resumido.

    Com produto_id:
        Mostra os detalhes do produto, último diagnóstico
        e histórico das análises desse produto.
    """

    # =========================================================
    # ESTATÍSTICAS DO UTILIZADOR
    # =========================================================

    diagnosticos_usuario = Diagnostico.objects.filter(
        usuario=request.user
    )

    total_diagnosticos_usuario = diagnosticos_usuario.count()

    diagnosticos_concluidos = diagnosticos_usuario.filter(
        status="concluido"
    ).count()

    confianca_media = (
        diagnosticos_usuario
        .filter(
            status="concluido",
            confianca__isnull=False,
        )
        .aggregate(media=Avg("confianca"))
        .get("media")
        or 0
    )

    # =========================================================
    # PRODUTOS ATIVOS
    # =========================================================

    produtos = (
        ProdutoAgricola.objects
        .filter(ativo=True)
        .prefetch_related("categorias")
    )

    # =========================================================
    # MODO PRODUTO
    # =========================================================

    produto = None
    diagnostico_atual = None
    historico_produto = []

    if produto_id is not None:

        produto = get_object_or_404(
            ProdutoAgricola,
            id=produto_id,
            ativo=True,
        )

        historico_produto = list(
            Diagnostico.objects
            .filter(
                usuario=request.user,
                produto=produto,
            )
            .order_by("-data_criacao")
        )

        if historico_produto:
            diagnostico_atual = historico_produto[0]

    # =========================================================
    # MODO GERAL
    # =========================================================
    #
    # Para cada produto, adicionamos:
    #
    # item.ultimo_diagnostico
    # item.total_diagnosticos
    #
    # =========================================================

    if produto is None:

        produtos = list(produtos)

        for item in produtos:

            item.total_diagnosticos = (
                Diagnostico.objects
                .filter(
                    usuario=request.user,
                    produto=item,
                )
                .count()
            )

            item.ultimo_diagnostico = (
                Diagnostico.objects
                .filter(
                    usuario=request.user,
                    produto=item,
                )
                .order_by("-data_criacao")
                .first()
            )

    # =========================================================
    # CONTEXTO
    # =========================================================

    context = {
        "produtos": produtos,

        "produto": produto,

        "diagnostico": diagnostico_atual,

        "historico_produto": historico_produto,

        "total_produtos": ProdutoAgricola.objects.filter(
            ativo=True
        ).count(),

        "total_diagnosticos_usuario":
            total_diagnosticos_usuario,

        "diagnosticos_concluidos":
            diagnosticos_concluidos,

        "confianca_media":
            confianca_media,
    }

    return render(
        request,
        "diagnostico/diagnostico.html",
        context,
    )



@login_required
def analisar(
    request,
    produto_id=None,
):
    # ========================================================
    # SOMENTE POST
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
            "Nenhum produto foi selecionado "
            "para o diagnóstico.",
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
            "Não é possível realizar o diagnóstico "
            "porque este produto ainda não possui "
            "uma imagem cadastrada.",
        )

        return redirect(
            "diagnostico:diagnostico_produto",
            produto_id=produto.id,
        )

    diagnostico_registo = None

    try:
        # ====================================================
        # LER IMAGEM DO PRODUTO
        # ====================================================

        imagem_bytes = obter_imagem_produto(
            produto
        )

        nome_imagem = Path(
            produto.imagem.name
        ).name

        # ====================================================
        # VALIDAR FORMATO
        # ====================================================

        obter_content_type(
            nome_imagem
        )

        # ====================================================
        # ENVIAR PARA FASTAPI
        # ====================================================

        resultado_api = enviar_para_api_ia(
            imagem_bytes,
            nome_imagem,
        )

        # ====================================================
        # NORMALIZAR RESULTADO
        # ====================================================

        dados = normalizar_resultado_ia(
            resultado_api
        )

        classe = dados["classe"]

        produto_detectado = dados[
            "produto"
        ]

        tipo = dados[
            "tipo"
        ]

        confianca = dados[
            "confianca"
        ]

        resultado = dados[
            "resultado"
        ]

        doenca = dados[
            "doenca"
        ]

        descricao = dados[
            "descricao"
        ]

        recomendacoes = dados[
            "recomendacoes"
        ]

        principais_previsoes = dados[
            "principais_previsoes"
        ]

        baixa_confianca = dados[
            "baixa_confianca"
        ]

        # ====================================================
        # VERIFICAR COMPATIBILIDADE
        # ====================================================

        (
            produto_compativel,
            mensagem_compatibilidade,
        ) = verificar_compatibilidade(
            produto,
            produto_detectado,
        )

        # ====================================================
        # CONSTRUIR OBSERVAÇÕES
        # ====================================================

        observacoes_texto = construir_observacoes(
            produto=produto,
            classe=classe,
            produto_detectado=produto_detectado,
            tipo=tipo,
            confianca=confianca,
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

            # Guardar uma cópia da imagem analisada.
            diagnostico_registo.imagem.save(
                nome_imagem,
                ContentFile(
                    imagem_bytes
                ),
                save=False,
            )

            diagnostico_registo.save()

        # ====================================================
        # URL DA IMAGEM DO DIAGNÓSTICO
        # ====================================================

        imagem_url = ""

        if diagnostico_registo.imagem:
            imagem_url = (
                diagnostico_registo
                .imagem
                .url
            )

        elif produto.imagem:
            imagem_url = (
                produto
                .imagem
                .url
            )

        # ====================================================
        # RESULTADO PARA A PÁGINA
        # ====================================================

        resultado_pagina = {
            "id": diagnostico_registo.id,

            "produto_id": produto.id,

            "produto_nome": produto.nome,

            "produto_detectado": (
                produto_detectado
            ),

            "imagem_url": imagem_url,

            "classe": classe,

            "produto": produto_detectado,

            "produtos": produto_detectado,

            "problema": dados[
                "problema"
            ],

            "tipo": tipo,

            "confianca": round(
                confianca,
                2,
            ),

            "resultado": resultado,

            "doenca": doenca,

            "descricao": descricao,

            "recomendacoes": recomendacoes,

            "principais_previsoes": (
                principais_previsoes
            ),

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
        # HISTÓRICO DO PRODUTO
        # ====================================================

        ultimos_diagnosticos = (
            obter_ultimos_diagnosticos(
                request,
                produto=produto,
                limite=5,
            )
        )

        # ====================================================
        # HISTÓRICO GERAL
        # ====================================================

        todos_ultimos_diagnosticos = (
            obter_ultimos_diagnosticos(
                request,
                limite=5,
            )
        )

        # ====================================================
        # ESTATÍSTICAS DO PRODUTO
        # ====================================================

        estatisticas_produto = (
            obter_estatisticas_produto(
                request,
                produto,
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

            "todos_ultimos_diagnosticos": (
                todos_ultimos_diagnosticos
            ),

            **estatisticas_produto,
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
    # ERRO DURANTE O DIAGNÓSTICO
    # ========================================================

    except Exception as exc:

        # ====================================================
        # REGISTRAR ERRO NO HISTÓRICO
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

            # Tentar guardar também a imagem.
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
                    ContentFile(
                        imagem_erro
                    ),
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

        if (
            "conectar" in mensagem_erro_lower
            or "connection" in mensagem_erro_lower
            or "connect" in mensagem_erro_lower
        ):

            mensagem_usuario = (
                "Não foi possível conectar ao serviço "
                "de inteligência artificial. Verifique "
                "se a AgroIA-API está em execução."
            )

        elif (
            "timeout" in mensagem_erro_lower
            or "demorou" in mensagem_erro_lower
        ):

            mensagem_usuario = (
                "A inteligência artificial demorou "
                "demasiado tempo para responder. "
                "Tente novamente."
            )

        elif (
            "formato de imagem" in mensagem_erro_lower
            or "imagem" in mensagem_erro_lower
            and (
                "suportado" in mensagem_erro_lower
                or "válida" in mensagem_erro_lower
                or "valida" in mensagem_erro_lower
            )
        ):

            mensagem_usuario = (
                "A imagem do produto não possui um "
                "formato suportado. Utilize JPG, PNG ou WEBP."
            )

        elif "10 mb" in mensagem_erro_lower:

            mensagem_usuario = (
                "A imagem é demasiado grande. "
                "O tamanho máximo permitido é 10 MB."
            )

        else:

            mensagem_usuario = (
                "Não foi possível concluir o diagnóstico. "
                "Verifique se a AgroIA-API está funcionando "
                "e tente novamente."
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
def historico_produto(
    request,
    produto_id,
):
    produto = get_object_or_404(
        ProdutoAgricola.objects.prefetch_related(
            "categorias"
        ),
        pk=produto_id,
        ativo=True,
    )

    diagnosticos = (
        obter_diagnosticos_produto(
            request,
            produto,
        )
    )

    estatisticas = (
        obter_estatisticas_produto(
            request,
            produto,
        )
    )

    ultimo_diagnostico = (
        estatisticas[
            "ultimo_diagnostico"
        ]
    )

    primeiro_diagnostico = (
        diagnosticos
        .order_by("data_criacao")
        .first()
    )

    resultados = (
        diagnosticos
        .filter(status="concluido")
        .values("resultado")
        .annotate(
            total=Count("id")
        )
        .order_by("-total")
    )

    # ========================================================
    # DADOS PARA GRÁFICO
    # ========================================================

    diagnosticos_grafico = list(
        diagnosticos
        .filter(status="concluido")
        .values(
            "id",
            "confianca",
            "resultado",
            "data_criacao",
            "doenca_identificada",
        )
        .order_by("data_criacao")
    )

    evolucao_confianca = []

    for item in diagnosticos_grafico:

        evolucao_confianca.append(
            {
                "id": item["id"],

                "confianca": float(
                    item["confianca"] or 0
                ),

                "resultado": (
                    item["resultado"]
                ),

                "doenca": (
                    item[
                        "doenca_identificada"
                    ]
                    or ""
                ),

                "data": (
                    item[
                        "data_criacao"
                    ].strftime(
                        "%d/%m/%Y"
                    )
                    if item[
                        "data_criacao"
                    ]
                    else ""
                ),
            }
        )

    # ========================================================
    # ÚLTIMOS DIAGNÓSTICOS
    # ========================================================

    ultimos_diagnosticos = (
        obter_ultimos_diagnosticos(
            request,
            produto=produto,
            limite=5,
        )
    )

    todos_ultimos_diagnosticos = (
        obter_ultimos_diagnosticos(
            request,
            limite=5,
        )
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

        "ultimos_diagnosticos": (
            ultimos_diagnosticos
        ),

        "todos_ultimos_diagnosticos": (
            todos_ultimos_diagnosticos
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
def detalhe_diagnostico(
    request,
    diagnostico_id,
):
    diagnostico_obj = get_object_or_404(
        Diagnostico.objects.select_related(
            "produto",
            "usuario",
        ),
        pk=diagnostico_id,
        usuario=request.user,
    )

    produto = diagnostico_obj.produto

    context = {
        "diagnostico": diagnostico_obj,
        "produto": produto,

        **obter_contadores(),

        **obter_estatisticas_utilizador(
            request
        ),
    }

    if produto is not None:

        context.update(
            obter_estatisticas_produto(
                request,
                produto,
            )
        )

        context[
            "ultimos_diagnosticos"
        ] = obter_ultimos_diagnosticos(
            request,
            produto=produto,
            limite=5,
        )

    else:

        context[
            "ultimos_diagnosticos"
        ] = []

    return render(
        request,
        "diagnostico/detalhe.html",
        context,
    )

