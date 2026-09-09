from pathlib import Path
import mimetypes
import os
import unicodedata

import requests

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from produtos.models import ProdutoAgricola
from .models import Diagnostico


MAX_IMAGE_SIZE = 10 * 1024 * 1024

FORMATOS_PERMITIDOS = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}

API_IA_URL = os.environ.get(
    "AGROIA_API_URL",
    getattr(
        settings,
        "AGROIA_API_URL",
        "http://127.0.0.1:8001/analisar",
    ),
).strip().rstrip("/")

try:
    API_TIMEOUT = int(
        os.environ.get(
            "AGROIA_API_TIMEOUT",
            getattr(settings, "AGROIA_API_TIMEOUT", 120),
        )
    )
except (TypeError, ValueError):
    API_TIMEOUT = 120


def normalizar_texto(valor):
    if valor is None:
        return ""

    texto = str(valor).strip().lower()

    texto = unicodedata.normalize(
        "NFKD",
        texto,
    ).encode(
        "ascii",
        "ignore",
    ).decode(
        "ascii"
    )

    return texto


def obter_contadores():
    total_diagnosticos = Diagnostico.objects.count()

    produtos_ativos = ProdutoAgricola.objects.filter(
        ativo=True
    ).count()

    return {
        "total_diagnosticos": total_diagnosticos,
        "produtos_ativos": produtos_ativos,
        "precisao_ia": 92,
    }


def obter_estatisticas_utilizador(request):
    diagnosticos = Diagnostico.objects.filter(
        usuario=request.user
    )

    total = diagnosticos.count()

    concluidos = diagnosticos.filter(
        status="concluido"
    ).count()

    erros = diagnosticos.filter(
        status="erro"
    ).count()

    processando = diagnosticos.filter(
        status="processando"
    ).count()

    pendentes = diagnosticos.filter(
        status="pendente"
    ).count()

    problemas = diagnosticos.filter(
        resultado__in=[
            "doenca",
            "praga",
            "fungo",
            "deficiencia",
        ],
        status="concluido",
    ).count()

    saudaveis = diagnosticos.filter(
        resultado="saudavel",
        status="concluido",
    ).count()

    media_confianca = diagnosticos.filter(
        status="concluido"
    ).aggregate(
        media=Avg("confianca")
    )["media"]

    return {
        "total": total,
        "concluidos": concluidos,
        "erros": erros,
        "processando": processando,
        "pendentes": pendentes,
        "problemas": problemas,
        "saudaveis": saudaveis,
        "media_confianca": float(
            media_confianca or 0
        ),
    }


def obter_estatisticas_produto(request, produto):
    diagnosticos = Diagnostico.objects.filter(
        usuario=request.user,
        produto=produto,
    )

    total = diagnosticos.count()

    concluidos = diagnosticos.filter(
        status="concluido"
    ).count()

    erros = diagnosticos.filter(
        status="erro"
    ).count()

    problemas = diagnosticos.filter(
        resultado__in=[
            "doenca",
            "praga",
            "fungo",
            "deficiencia",
        ],
        status="concluido",
    ).count()

    saudaveis = diagnosticos.filter(
        resultado="saudavel",
        status="concluido",
    ).count()

    media_confianca = diagnosticos.filter(
        status="concluido"
    ).aggregate(
        media=Avg("confianca")
    )["media"]

    ultimo_diagnostico = (
        diagnosticos
        .filter(status="concluido")
        .order_by("-data_criacao")
        .first()
    )

    primeiro_diagnostico = (
        diagnosticos
        .filter(status="concluido")
        .order_by("data_criacao")
        .first()
    )

    return {
        "total": total,
        "concluidos": concluidos,
        "erros": erros,
        "problemas": problemas,
        "saudaveis": saudaveis,
        "media_confianca": float(
            media_confianca or 0
        ),
        "ultimo_diagnostico": ultimo_diagnostico,
        "primeiro_diagnostico": primeiro_diagnostico,
    }


def obter_ultimos_diagnosticos(
    request,
    produto=None,
    limite=5,
):
    queryset = (
        Diagnostico.objects
        .filter(
            usuario=request.user,
            status="concluido",
        )
        .select_related(
            "produto",
            "usuario",
        )
        .order_by(
            "-data_criacao"
        )
    )

    if produto is not None:
        queryset = queryset.filter(
            produto=produto
        )

    return queryset[:limite]


def obter_diagnosticos_produto(request, produto):
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
        .order_by(
            "-data_criacao"
        )
    )


def obter_produtos_ativos(request=None):
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


def obter_produto(produto_id):
    return get_object_or_404(
        ProdutoAgricola.objects
        .filter(
            ativo=True
        )
        .prefetch_related(
            "categorias"
        ),
        pk=produto_id,
    )


def obter_produtos_com_resumo(request):
    produtos = list(
        obter_produtos_ativos(request)
    )

    diagnosticos = list(
        Diagnostico.objects
        .filter(
            usuario=request.user,
            status="concluido",
        )
        .select_related(
            "produto"
        )
        .order_by(
            "-data_criacao"
        )
    )

    diagnosticos_por_produto = {}

    for diagnostico in diagnosticos:
        if diagnostico.produto_id not in diagnosticos_por_produto:
            diagnosticos_por_produto[
                diagnostico.produto_id
            ] = []

        diagnosticos_por_produto[
            diagnostico.produto_id
        ].append(diagnostico)

    historico_recente = []

    for produto in produtos:
        historico = diagnosticos_por_produto.get(
            produto.id,
            []
        )

        produto.diagnosticos_usuario = historico
        produto.numero_diagnosticos_usuario = len(
            historico
        )
        produto.total_diagnosticos = len(
            historico
        )

        produto.ultimo_diagnostico_usuario = (
            historico[0]
            if historico
            else None
        )

        produto.ultimo_diagnostico = (
            historico[0]
            if historico
            else None
        )

        if historico:
            historico_recente.append(
                {
                    "produto": produto,
                    "diagnostico": historico[0],
                }
            )

    historico_recente.sort(
        key=lambda item: item["diagnostico"].data_criacao,
        reverse=True,
    )

    return produtos, historico_recente


def obter_nome_imagem(produto):
    if not produto.imagem:
        return "imagem.jpg"

    nome = Path(
        produto.imagem.name
    ).name

    return nome or "imagem.jpg"


def obter_content_type(nome_imagem):
    extensao = (
        Path(nome_imagem)
        .suffix
        .lower()
        .replace(
            ".",
            "",
        )
    )

    if extensao in FORMATOS_PERMITIDOS:
        return FORMATOS_PERMITIDOS[
            extensao
        ]

    content_type, _ = mimetypes.guess_type(
        nome_imagem
    )

    if content_type in FORMATOS_PERMITIDOS.values():
        return content_type

    return "image/jpeg"


def obter_url_imagem_produto(produto):
    if not produto.imagem:
        raise ValueError(
            "Este produto não possui uma imagem cadastrada."
        )

    try:
        url = produto.imagem.url
    except Exception as exc:
        raise ValueError(
            "Não foi possível obter a URL da imagem do produto."
        ) from exc

    if not url:
        raise ValueError(
            "A imagem do produto não possui uma URL válida."
        )

    if (
        url.startswith("http://")
        or url.startswith("https://")
    ):
        return url

    return None


def baixar_imagem_da_url(url):
    try:
        response = requests.get(
            url,
            timeout=API_TIMEOUT,
            allow_redirects=True,
        )
    except requests.exceptions.Timeout as exc:
        raise TimeoutError(
            "O carregamento da imagem do produto demorou demasiado tempo."
        ) from exc
    except requests.exceptions.ConnectionError as exc:
        raise ConnectionError(
            "Não foi possível conectar ao armazenamento da imagem."
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(
            f"Erro ao carregar a imagem do armazenamento: {exc}"
        ) from exc

    if response.status_code != 200:
        raise RuntimeError(
            "O armazenamento não conseguiu disponibilizar "
            f"a imagem do produto. Estado HTTP: {response.status_code}."
        )

    imagem_bytes = response.content

    if not imagem_bytes:
        raise ValueError(
            "O armazenamento devolveu uma imagem vazia."
        )

    if len(imagem_bytes) > MAX_IMAGE_SIZE:
        raise ValueError(
            "A imagem do produto excede o limite máximo de 10 MB."
        )

    return imagem_bytes


def obter_imagem_produto(produto):
    if not produto.imagem:
        raise ValueError(
            "Este produto não possui uma imagem cadastrada."
        )

    storage = produto.imagem.storage
    nome = produto.imagem.name

    if not nome:
        raise ValueError(
            "A imagem do produto não possui um nome válido."
        )

    if (
        nome.startswith("http://")
        or nome.startswith("https://")
    ):
        return baixar_imagem_da_url(nome)

    try:
        url = obter_url_imagem_produto(
            produto
        )

        if url:
            return baixar_imagem_da_url(
                url
            )

    except Exception:
        pass

    try:
        with storage.open(
            nome,
            "rb",
        ) as arquivo:
            imagem_bytes = arquivo.read()

        if not imagem_bytes:
            raise ValueError(
                "A imagem armazenada está vazia."
            )

        if len(imagem_bytes) > MAX_IMAGE_SIZE:
            raise ValueError(
                "A imagem do produto excede o limite máximo de 10 MB."
            )

        return imagem_bytes

    except Exception as erro_storage:
        raise ValueError(
            "Não foi possível carregar a imagem do produto. "
            f"Storage: {erro_storage}."
        ) from erro_storage


def validar_imagem(imagem_bytes):
    if not imagem_bytes:
        raise ValueError(
            "A imagem enviada está vazia."
        )

    if len(imagem_bytes) > MAX_IMAGE_SIZE:
        raise ValueError(
            "A imagem do produto excede o limite máximo de 10 MB."
        )

    return True


def enviar_para_api_ia(
    imagem_bytes,
    nome_imagem="imagem.jpg",
):
    validar_imagem(
        imagem_bytes
    )

    content_type = obter_content_type(
        nome_imagem
    )

    arquivos = {
        "imagem": (
            nome_imagem,
            imagem_bytes,
            content_type,
        )
    }

    try:
        response = requests.post(
            API_IA_URL,
            files=arquivos,
            timeout=API_TIMEOUT,
        )

    except requests.exceptions.Timeout as exc:
        raise TimeoutError(
            "A inteligência artificial demorou demasiado tempo "
            "para responder."
        ) from exc

    except requests.exceptions.ConnectionError as exc:
        raise ConnectionError(
            "Não foi possível conectar ao serviço de inteligência "
            "artificial."
        ) from exc

    except requests.exceptions.RequestException as exc:
        raise RuntimeError(
            f"Erro de comunicação com a inteligência artificial: {exc}"
        ) from exc

    if response.status_code >= 400:
        try:
            erro_api = response.json()
        except ValueError:
            erro_api = response.text

        raise RuntimeError(
            "A API de inteligência artificial retornou "
            f"HTTP {response.status_code}: {erro_api}"
        )

    try:
        dados = response.json()
    except ValueError as exc:
        raise ValueError(
            "A API de inteligência artificial retornou "
            "uma resposta que não é JSON válido."
        ) from exc

    if not isinstance(
        dados,
        dict,
    ):
        raise ValueError(
            "A API de inteligência artificial retornou "
            "um formato de dados inválido."
        )

    if dados.get("sucesso") is False:
        mensagem = (
            dados.get("mensagem")
            or dados.get("erro")
            or "A inteligência artificial não conseguiu analisar a imagem."
        )

        raise RuntimeError(
            str(mensagem)
        )

    return dados


def identificar_produto_da_classe(classe):
    texto = normalizar_texto(
        classe
    )

    culturas = {
        "milho": [
            "corn",
            "maize",
            "milho",
        ],
        "tomate": [
            "tomato",
            "tomate",
        ],
        "batata": [
            "potato",
            "batata",
        ],
        "maca": [
            "apple",
            "maca",
        ],
        "uva": [
            "grape",
            "uva",
        ],
        "pessego": [
            "peach",
            "pessego",
        ],
        "cereja": [
            "cherry",
            "cereja",
        ],
        "laranja": [
            "orange",
            "laranja",
        ],
        "soja": [
            "soybean",
            "soy",
            "soja",
        ],
        "morango": [
            "strawberry",
            "morango",
        ],
        "framboesa": [
            "raspberry",
            "framboesa",
        ],
        "mirtilo": [
            "blueberry",
            "mirtilo",
        ],
        "pimentao": [
            "pepper",
            "bell_pepper",
            "pimentao",
        ],
        "abobora": [
            "squash",
            "pumpkin",
            "abobora",
        ],
        "feijao": [
            "bean",
            "beans",
            "feijao",
        ],
        "mandioca": [
            "cassava",
            "yuca",
            "mandioca",
        ],
        "arroz": [
            "rice",
            "arroz",
        ],
    }

    for produto, nomes in culturas.items():
        if any(
            nome in texto
            for nome in nomes
        ):
            return produto

    return ""


def obter_nome_produto_detectado(
    classe,
    resultado=None,
):
    if isinstance(
        resultado,
        dict,
    ):
        produto = resultado.get(
            "produto"
        )

        if produto:
            return str(
                produto
            ).strip()

    produto = identificar_produto_da_classe(
        classe
    )

    nomes = {
        "milho": "Milho",
        "tomate": "Tomate",
        "batata": "Batata",
        "maca": "Maçã",
        "uva": "Uva",
        "pessego": "Pêssego",
        "cereja": "Cereja",
        "laranja": "Laranja",
        "soja": "Soja",
        "morango": "Morango",
        "framboesa": "Framboesa",
        "mirtilo": "Mirtilo",
        "pimentao": "Pimentão",
        "abobora": "Abóbora",
        "feijao": "Feijão",
        "mandioca": "Mandioca",
        "arroz": "Arroz",
    }

    return nomes.get(
        produto,
        "",
    )


def normalizar_resultado_ia(
    dados_api,
    produto=None,
):
    if not isinstance(
        dados_api,
        dict,
    ):
        raise ValueError(
            "Resposta da API inválida."
        )

    resultado_api = dados_api.get(
        "resultado"
    )

    if not isinstance(
        resultado_api,
        dict,
    ):
        resultado_api = dados_api

    classe = (
        resultado_api.get(
            "classe"
        )
        or resultado_api.get(
            "class"
        )
        or resultado_api.get(
            "classe_identificada"
        )
        or ""
    )

    classe = str(
        classe
    ).strip()

    produto_detectado = obter_nome_produto_detectado(
        classe,
        resultado_api,
    )

    problema = (
        resultado_api.get(
            "problema"
        )
        or resultado_api.get(
            "doenca"
        )
        or resultado_api.get(
            "doenca_identificada"
        )
        or ""
    )

    problema = str(
        problema
    ).strip()

    tipo = (
        resultado_api.get(
            "tipo"
        )
        or ""
    )

    tipo_normalizado = normalizar_texto(
        tipo
    )

    problema_normalizado = normalizar_texto(
        problema
    )

    resultado = (
        resultado_api.get(
            "resultado"
        )
        or ""
    )

    resultado_normalizado = normalizar_texto(
        resultado
    )

    if resultado_normalizado in {
        "saudavel",
        "saude",
        "healthy",
        "normal",
    }:
        resultado_final = "saudavel"

    elif resultado_normalizado in {
        "praga",
        "pest",
        "pests",
    }:
        resultado_final = "praga"

    elif resultado_normalizado in {
        "fungo",
        "fungica",
        "fungico",
        "fungal",
        "fungal_disease",
    }:
        resultado_final = "fungo"

    elif resultado_normalizado in {
        "doenca",
        "disease",
        "viral",
        "bacterial",
        "bacteriana",
        "bacteriano",
        "virica",
        "virico",
    }:
        resultado_final = "doenca"

    elif resultado_normalizado in {
        "deficiencia",
        "deficiency",
        "nutritional_deficiency",
    }:
        resultado_final = "deficiencia"

    elif (
        "fung" in tipo_normalizado
        or "fung" in problema_normalizado
    ):
        resultado_final = "fungo"

    elif (
        "praga" in tipo_normalizado
        or "pest" in tipo_normalizado
        or "praga" in problema_normalizado
        or "pest" in problema_normalizado
    ):
        resultado_final = "praga"

    elif (
        "viral" in tipo_normalizado
        or "bacter" in tipo_normalizado
        or "viral" in problema_normalizado
        or "bacter" in problema_normalizado
    ):
        resultado_final = "doenca"

    elif (
        "deficien" in tipo_normalizado
        or "deficien" in problema_normalizado
    ):
        resultado_final = "deficiencia"

    elif (
        "healthy" in normalizar_texto(classe)
        or "saudavel" in normalizar_texto(classe)
    ):
        resultado_final = "saudavel"

    elif problema:
        resultado_final = "doenca"

    else:
        resultado_final = "indeterminado"

    try:
        confianca = float(
            resultado_api.get(
                "confianca",
                0,
            )
            or 0
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

    principais_previsoes = (
        resultado_api.get(
            "principais_previsoes",
            [],
        )
        or []
    )

    if not isinstance(
        principais_previsoes,
        list,
    ):
        principais_previsoes = []

    previsoes_normalizadas = []

    for previsao in principais_previsoes:
        if not isinstance(
            previsao,
            dict,
        ):
            continue

        previsao_classe = str(
            previsao.get(
                "classe",
                "",
            )
            or ""
        ).strip()

        previsao_produto = (
            previsao.get(
                "produto"
            )
            or obter_nome_produto_detectado(
                previsao_classe,
                previsao,
            )
        )

        previsao_problema = str(
            previsao.get(
                "problema",
                "",
            )
            or ""
        ).strip()

        try:
            previsao_confianca = float(
                previsao.get(
                    "confianca",
                    0,
                )
                or 0
            )
        except (
            TypeError,
            ValueError,
        ):
            previsao_confianca = 0.0

        previsoes_normalizadas.append(
            {
                "classe": previsao_classe,
                "produto": str(
                    previsao_produto or ""
                ),
                "problema": previsao_problema,
                "tipo": str(
                    previsao.get(
                        "tipo",
                        "",
                    )
                    or ""
                ),
                "confianca": max(
                    0.0,
                    min(
                        100.0,
                        previsao_confianca,
                    ),
                ),
            }
        )

    descricao = (
        resultado_api.get(
            "descricao"
        )
        or resultado_api.get(
            "descricao_resultado"
        )
        or ""
    )

    recomendacoes = (
        resultado_api.get(
            "recomendacoes"
        )
        or ""
    )

    baixa_confianca = resultado_api.get(
        "baixa_confianca"
    )

    if baixa_confianca is None:
        baixa_confianca = confianca < 40.0

    produto_compativel = resultado_api.get(
        "produto_compativel"
    )

    mensagem_compatibilidade = (
        resultado_api.get(
            "mensagem_compatibilidade"
        )
        or ""
    )

    resultado = {
        "classe": classe,
        "produto": produto_detectado,
        "produtos": (
            [produto_detectado]
            if produto_detectado
            else []
        ),
        "problema": problema,
        "tipo": str(
            tipo
        ).strip(),
        "confianca": confianca,
        "resultado": resultado_final,
        "doenca": problema,
        "descricao": str(
            descricao
        ).strip(),
        "recomendacoes": str(
            recomendacoes
        ).strip(),
        "principais_previsoes": previsoes_normalizadas,
        "produto_compativel": produto_compativel,
        "mensagem_compatibilidade": str(
            mensagem_compatibilidade
        ).strip(),
        "baixa_confianca": bool(
            baixa_confianca
        ),
    }

    if produto is not None:
        if produto_compativel is None:
            produto_compativel = verificar_compatibilidade(
                produto,
                produto_detectado,
            )

            resultado[
                "produto_compativel"
            ] = produto_compativel

        if not produto_compativel:
            resultado[
                "mensagem_compatibilidade"
            ] = (
                "A cultura identificada pela inteligência artificial "
                "não corresponde claramente ao produto selecionado."
            )

    return resultado


def analisar_imagem(
    imagem=None,
    produto=None,
    nome_imagem="imagem.jpg",
):
    if imagem is None and produto is not None:
        imagem = obter_imagem_produto(
            produto
        )

    if imagem is None:
        raise ValueError(
            "Nenhuma imagem foi fornecida para análise."
        )

    if hasattr(
        imagem,
        "read",
    ):
        imagem_bytes = imagem.read()

        if hasattr(
            imagem,
            "name",
        ):
            nome_imagem = (
                Path(
                    imagem.name
                ).name
                or nome_imagem
            )
    else:
        imagem_bytes = bytes(
            imagem
        )

    validar_imagem(
        imagem_bytes
    )

    dados_api = enviar_para_api_ia(
        imagem_bytes,
        nome_imagem,
    )

    return normalizar_resultado_ia(
        dados_api,
        produto=produto,
    )


def verificar_compatibilidade(
    produto,
    produto_detectado,
):
    if not produto_detectado:
        return True

    produto_base = normalizar_texto(
        produto.nome
    )

    detectado = normalizar_texto(
        produto_detectado
    )

    equivalencias = {
        "milho": [
            "milho",
            "maize",
            "corn",
        ],
        "feijao": [
            "feijao",
            "bean",
            "beans",
        ],
        "mandioca": [
            "mandioca",
            "cassava",
            "yuca",
        ],
        "arroz": [
            "arroz",
            "rice",
        ],
        "tomate": [
            "tomate",
            "tomato",
        ],
        "maca": [
            "maca",
            "apple",
        ],
        "mirtilo": [
            "mirtilo",
            "blueberry",
        ],
        "cereja": [
            "cereja",
            "cherry",
        ],
        "uva": [
            "uva",
            "grape",
        ],
        "laranja": [
            "laranja",
            "orange",
        ],
        "pessego": [
            "pessego",
            "peach",
        ],
        "pimentao": [
            "pimentao",
            "pepper",
        ],
        "batata": [
            "batata",
            "potato",
        ],
        "framboesa": [
            "framboesa",
            "raspberry",
        ],
        "soja": [
            "soja",
            "soybean",
        ],
        "abobora": [
            "abobora",
            "squash",
        ],
        "morango": [
            "morango",
            "strawberry",
        ],
    }

    for nomes in equivalencias.values():
        produto_correspondente = any(
            nome in produto_base
            for nome in nomes
        )

        detectado_correspondente = any(
            nome in detectado
            for nome in nomes
        )

        if (
            produto_correspondente
            and detectado_correspondente
        ):
            return True

    if (
        produto_base
        and detectado
        and (
            produto_base in detectado
            or detectado in produto_base
        )
    ):
        return True

    return False


def construir_observacoes(
    produto,
    resultado,
    compativel=True,
):
    observacoes = []

    if not compativel:
        observacoes.append(
            "A cultura identificada pela inteligência artificial "
            "não corresponde claramente ao produto selecionado. "
            "O resultado deve ser interpretado com cautela."
        )

    if resultado.get(
        "baixa_confianca"
    ):
        observacoes.append(
            "A confiança da inteligência artificial está abaixo "
            "do nível mínimo recomendado para uma interpretação "
            "segura."
        )

    produto_detectado = resultado.get(
        "produto"
    )

    if produto_detectado:
        observacoes.append(
            "Cultura identificada pela IA: "
            f"{produto_detectado}."
        )

    tipo = resultado.get(
        "tipo"
    )

    if tipo:
        observacoes.append(
            "Tipo de resultado identificado: "
            f"{tipo}."
        )

    classe = resultado.get(
        "classe"
    )

    if classe:
        observacoes.append(
            "Classe identificada: "
            f"{classe}."
        )

    confianca = resultado.get(
        "confianca"
    )

    if confianca is not None:
        observacoes.append(
            f"Confiança da análise: {float(confianca):.2f}%."
        )

    previsoes = resultado.get(
        "principais_previsoes"
    )

    if isinstance(
        previsoes,
        list,
    ) and previsoes:
        observacoes.append(
            "A análise considerou múltiplas previsões "
            "do modelo de inteligência artificial."
        )

    if not observacoes:
        observacoes.append(
            "Diagnóstico processado com sucesso pela "
            "inteligência artificial."
        )

    return "\n".join(
        observacoes
    )


@login_required
def diagnostico(
    request,
    produto_id=None,
):
    contadores = obter_contadores()

    estatisticas = obter_estatisticas_utilizador(
        request
    )

    produtos, historico_recente = (
        obter_produtos_com_resumo(
            request
        )
    )

    produto = None
    diagnostico_atual = None
    historico = []
    estatisticas_produto = None

    if produto_id is not None:
        produto = obter_produto(
            produto_id
        )

        historico = list(
            obter_diagnosticos_produto(
                request,
                produto,
            )
        )

        diagnostico_atual = (
            historico[0]
            if historico
            else None
        )

        estatisticas_produto = (
            obter_estatisticas_produto(
                request,
                produto,
            )
        )

    confianca_media = estatisticas[
        "media_confianca"
    ]

    contexto = {
        "produtos": produtos,
        "produto": produto,
        "diagnostico": diagnostico_atual,
        "diagnostico_atual": diagnostico_atual,
        "historico": historico,

        "historico_produto": historico,

        "historico_recente": historico_recente,

        "total_produtos": contadores[
            "produtos_ativos"
        ],

        "total_diagnosticos": estatisticas[
            "total"
        ],

        "total_diagnosticos_usuario": estatisticas[
            "concluidos"
        ],

        "diagnosticos_realizados": estatisticas[
            "concluidos"
        ],

        "diagnosticos_concluidos": estatisticas[
            "concluidos"
        ],

        "diagnosticos_erros": estatisticas[
            "erros"
        ],

        "diagnosticos_processando": estatisticas[
            "processando"
        ],

        "diagnosticos_pendentes": estatisticas[
            "pendentes"
        ],

        "total_problemas": estatisticas[
            "problemas"
        ],

        "total_saudaveis": estatisticas[
            "saudaveis"
        ],

        "media_confianca": confianca_media,

        "confianca_media": confianca_media,

        "precisao_ia": contadores[
            "precisao_ia"
        ],

        "ultimos_diagnosticos": (
            obter_ultimos_diagnosticos(
                request,
                produto=produto,
                limite=5,
            )
        ),

        "estatisticas": estatisticas,

        "estatisticas_produto": (
            estatisticas_produto
        ),

        "api_ia_url": API_IA_URL,
    }

    return render(
        request,
        "diagnostico/diagnostico.html",
        contexto,
    )


@login_required
@require_POST
def analisar(
    request,
    produto_id=None,
):
    produto_id_post = request.POST.get(
        "produto_id"
    )

    if produto_id is None and produto_id_post:
        try:
            produto_id = int(
                produto_id_post
            )
        except (
            TypeError,
            ValueError,
        ):
            messages.error(
                request,
                "Produto inválido.",
            )

            return redirect(
                "diagnostico:diagnostico"
            )

    if produto_id is None:
        messages.error(
            request,
            "É necessário selecionar um produto.",
        )

        return redirect(
            "diagnostico:diagnostico"
        )

    produto = obter_produto(
        produto_id
    )

    diagnostico_obj = None

    try:
        if not produto.imagem:
            raise ValueError(
                "Este produto não possui uma imagem cadastrada."
            )

        imagem_bytes = obter_imagem_produto(
            produto
        )

        nome_imagem = obter_nome_imagem(
            produto
        )

        validar_imagem(
            imagem_bytes
        )

        diagnostico_obj = Diagnostico.objects.create(
            usuario=request.user,
            produto=produto,
            imagem=ContentFile(
                imagem_bytes,
                name=nome_imagem,
            ),
            status="processando",
            resultado="indeterminado",
            confianca=0,
        )

        resultado = analisar_imagem(
            imagem=imagem_bytes,
            produto=produto,
            nome_imagem=nome_imagem,
        )

        if not isinstance(
            resultado,
            dict,
        ):
            raise ValueError(
                "O serviço de inteligência artificial "
                "retornou um resultado inválido."
            )

        produto_detectado = resultado.get(
            "produto"
        )

        compativel = verificar_compatibilidade(
            produto,
            produto_detectado,
        )

        observacoes = construir_observacoes(
            produto,
            resultado,
            compativel,
        )

        with transaction.atomic():
            diagnostico_obj.classe_identificada = (
                resultado.get(
                    "classe",
                    "",
                )
            )

            diagnostico_obj.resultado = (
                resultado.get(
                    "resultado",
                    "indeterminado",
                )
            )

            diagnostico_obj.doenca_identificada = (
                resultado.get(
                    "problema",
                    "",
                )
            )

            diagnostico_obj.confianca = (
                resultado.get(
                    "confianca",
                    0,
                )
            )

            diagnostico_obj.descricao_resultado = (
                resultado.get(
                    "descricao",
                    "",
                )
            )

            diagnostico_obj.recomendacoes = (
                resultado.get(
                    "recomendacoes",
                    "",
                )
            )

            diagnostico_obj.observacoes = (
                observacoes
            )

            diagnostico_obj.status = (
                "concluido"
            )

            diagnostico_obj.erro = ""

            diagnostico_obj.save()

        messages.success(
            request,
            "Diagnóstico concluído com sucesso.",
        )

        return redirect(
            "diagnostico:detalhe",
            diagnostico_id=diagnostico_obj.pk,
        )

    except Exception as exc:
        erro = str(
            exc
        ).strip()

        if not erro:
            erro = (
                "Ocorreu um erro desconhecido durante "
                "o processamento do diagnóstico."
            )

        if diagnostico_obj is not None:
            try:
                diagnostico_obj.status = "erro"

                diagnostico_obj.resultado = (
                    "indeterminado"
                )

                diagnostico_obj.erro = erro

                diagnostico_obj.observacoes = (
                    "O diagnóstico não pôde ser concluído "
                    "devido a um erro durante o processamento."
                )

                diagnostico_obj.save(
                    update_fields=[
                        "status",
                        "resultado",
                        "erro",
                        "observacoes",
                        "data_atualizacao",
                    ]
                )

            except Exception:
                pass

        messages.error(
            request,
            "Não foi possível realizar o diagnóstico: "
            f"{erro}",
        )

        return redirect(
            "diagnostico:diagnostico_produto",
            produto_id=produto.pk,
        )


@login_required
def historico_produto(
    request,
    produto_id,
):
    produto = obter_produto(
        produto_id
    )

    diagnosticos = list(
        obter_diagnosticos_produto(
            request,
            produto,
        )
    )

    estatisticas = obter_estatisticas_produto(
        request,
        produto,
    )

    distribuicao = (
        Diagnostico.objects
        .filter(
            usuario=request.user,
            produto=produto,
            status="concluido",
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

    evolucao_confianca = []

    for item in diagnosticos:
        if item.status != "concluido":
            continue

        evolucao_confianca.append(
            {
                "data": item.data_criacao,
                "confianca": float(
                    item.confianca or 0
                ),
                "resultado": item.resultado,
            }
        )

    contexto = {
        "produto": produto,
        "diagnosticos": diagnosticos,

        "total_diagnosticos": estatisticas[
            "total"
        ],

        "diagnosticos_concluidos": estatisticas[
            "concluidos"
        ],

        "diagnosticos_erros": estatisticas[
            "erros"
        ],

        "total_problemas": estatisticas[
            "problemas"
        ],

        "total_saudaveis": estatisticas[
            "saudaveis"
        ],

        "media_confianca": estatisticas[
            "media_confianca"
        ],

        "primeiro_diagnostico": estatisticas[
            "primeiro_diagnostico"
        ],

        "ultimo_diagnostico": estatisticas[
            "ultimo_diagnostico"
        ],

        "distribuicao": distribuicao,

        "evolucao_confianca": evolucao_confianca,

        "ultimos_diagnosticos": (
            obter_ultimos_diagnosticos(
                request,
                produto=produto,
                limite=10,
            )
        ),
    }

    return render(
        request,
        "diagnostico/historico_produto.html",
        contexto,
    )


@login_required
def detalhe_diagnostico(
    request,
    diagnostico_id,
):
    diagnostico_obj = get_object_or_404(
        Diagnostico.objects
        .select_related(
            "produto",
            "usuario",
        )
        .filter(
            usuario=request.user
        ),
        pk=diagnostico_id,
    )

    produto = diagnostico_obj.produto

    estatisticas = obter_estatisticas_utilizador(
        request
    )

    recentes = obter_ultimos_diagnosticos(
        request,
        produto=produto,
        limite=5,
    )

    contexto = {
        "diagnostico": diagnostico_obj,
        "diagnostico_obj": diagnostico_obj,
        "produto": produto,

        "total_diagnosticos": estatisticas[
            "total"
        ],

        "diagnosticos_concluidos": estatisticas[
            "concluidos"
        ],

        "media_confianca": estatisticas[
            "media_confianca"
        ],

        "confianca_media": estatisticas[
            "media_confianca"
        ],

        "ultimos_diagnosticos": recentes,

        "estatisticas": estatisticas,
    }

    return render(
        request,
        "diagnostico/detalhe.html",
        contexto,
    )
