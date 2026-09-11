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
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from produtos.models import ProdutoAgricola

from .models import Diagnostico


# ============================================================
# CONFIGURAÇÃO DA API DE IA
# ============================================================

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


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def normalizar_texto(valor):
    """
    Normaliza texto para facilitar comparações entre português,
    inglês, maiúsculas, acentos etc.
    """

    if valor is None:
        return ""

    texto = str(valor).strip().lower()

    texto = unicodedata.normalize(
        "NFKD",
        texto,
    )

    texto = "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(caractere)
    )

    return texto


def obter_produto(produto_id):
    """
    Obtém um produto agrícola ativo.
    """

    return get_object_or_404(
        ProdutoAgricola,
        pk=produto_id,
        ativo=True,
    )


def obter_nome_imagem(produto):
    """
    Obtém um nome seguro para a imagem do diagnóstico.
    """

    try:
        nome = Path(produto.imagem.name).name

        if nome:
            return nome

    except Exception:
        pass

    return f"produto_{produto.pk}.jpg"


def obter_content_type(nome_imagem):
    """
    Descobre o MIME type da imagem.
    """

    content_type, _ = mimetypes.guess_type(nome_imagem)

    if content_type:
        return content_type

    return "image/jpeg"


def validar_imagem(imagem_bytes):
    """
    Valida se existem dados na imagem e limita o tamanho.
    """

    if not imagem_bytes:
        raise ValueError(
            "A imagem do produto está vazia."
        )

    tamanho_maximo = 10 * 1024 * 1024

    if len(imagem_bytes) > tamanho_maximo:
        raise ValueError(
            "A imagem não pode ultrapassar 10 MB."
        )

    return True


# ============================================================
# IMAGENS DOS PRODUTOS
# ============================================================

def baixar_imagem_da_url(url):
    """
    Faz download da imagem através de uma URL pública.

    Necessário principalmente quando a imagem do produto
    está armazenada em um storage externo, incluindo Vercel Blob.
    """

    if not url:
        raise ValueError(
            "URL da imagem não encontrada."
        )

    try:
        resposta = requests.get(
            url,
            timeout=30,
            allow_redirects=True,
        )

    except requests.Timeout as erro:
        raise ValueError(
            "O servidor demorou demasiado tempo para fornecer "
            "a imagem do produto."
        ) from erro

    except requests.RequestException as erro:
        raise ValueError(
            f"Não foi possível obter a imagem do produto: {erro}"
        ) from erro

    if resposta.status_code != 200:
        raise ValueError(
            "Não foi possível obter a imagem do produto. "
            f"Servidor respondeu com HTTP {resposta.status_code}."
        )

    conteudo = resposta.content

    if not conteudo:
        raise ValueError(
            "A imagem obtida está vazia."
        )

    validar_imagem(conteudo)

    return conteudo


def obter_url_imagem_produto(produto):
    """
    Obtém a URL absoluta da imagem do produto.

    Funciona com storages que disponibilizam uma URL pública,
    incluindo Vercel Blob.
    """

    try:
        if not produto.imagem:
            return None

        url = produto.imagem.url

        if not url:
            return None

        url = str(url).strip()

        if url.startswith("http://") or url.startswith("https://"):
            return url

    except Exception:
        pass

    return None


def obter_imagem_produto(produto):
    """
    Obtém os bytes da imagem do produto.

    Ordem:

    1. URL pública do storage;
    2. abertura direta pelo storage;
    3. erro.
    """

    if not produto.imagem:
        raise ValueError(
            "Este produto não possui uma imagem registada."
        )

    nome = produto.imagem.name
    storage = produto.imagem.storage

    # --------------------------------------------------------
    # 1. Tentar URL pública
    # --------------------------------------------------------

    try:
        url = obter_url_imagem_produto(produto)

        if url:
            return baixar_imagem_da_url(url)

    except Exception:
        pass

    # --------------------------------------------------------
    # 2. Tentar diretamente pelo storage
    # --------------------------------------------------------

    try:
        with storage.open(nome, "rb") as arquivo:
            imagem_bytes = arquivo.read()

        validar_imagem(imagem_bytes)

        return imagem_bytes

    except Exception as erro_storage:
        raise ValueError(
            "Não foi possível obter a imagem do produto "
            "através do armazenamento configurado. "
            f"Detalhes: {erro_storage}"
        ) from erro_storage


# ============================================================
# COMUNICAÇÃO COM A API DA IA
# ============================================================

def enviar_para_api_ia(
    imagem,
    nome_imagem,
    content_type=None,
):
    """
    Envia a imagem para a API FastAPI.

    A API espera:

        POST /analisar

        campo:
            imagem

    Resposta esperada:

        {
            "sucesso": true,
            "resultado": {
                "classe": "...",
                "produto": "...",
                "problema": "...",
                "tipo": "...",
                "confianca": 91.72
            }
        }
    """

    validar_imagem(imagem)

    if not API_IA_URL:
        raise ValueError(
            "A URL da API de inteligência artificial "
            "não está configurada."
        )

    if not content_type:
        content_type = obter_content_type(nome_imagem)

    arquivos = {
        "imagem": (
            nome_imagem,
            imagem,
            content_type,
        )
    }

    try:
        resposta = requests.post(
            API_IA_URL,
            files=arquivos,
            timeout=API_TIMEOUT,
        )

    except requests.Timeout as erro:
        raise RuntimeError(
            "A API de inteligência artificial demorou "
            "demasiado tempo para responder."
        ) from erro

    except requests.ConnectionError as erro:
        raise RuntimeError(
            "Não foi possível estabelecer ligação com a API "
            "de inteligência artificial."
        ) from erro

    except requests.RequestException as erro:
        raise RuntimeError(
            f"Erro de comunicação com a API de IA: {erro}"
        ) from erro

    # --------------------------------------------------------
    # Verificação HTTP
    # --------------------------------------------------------

    if resposta.status_code < 200 or resposta.status_code >= 300:

        detalhe = ""

        try:
            dados_erro = resposta.json()

            if isinstance(dados_erro, dict):
                detalhe = (
                    dados_erro.get("detail")
                    or dados_erro.get("erro")
                    or dados_erro.get("message")
                    or ""
                )

        except ValueError:
            detalhe = resposta.text[:500]

        mensagem = (
            "A API de inteligência artificial respondeu "
            f"com HTTP {resposta.status_code}."
        )

        if detalhe:
            mensagem += f" Detalhes: {detalhe}"

        raise RuntimeError(mensagem)

    # --------------------------------------------------------
    # JSON
    # --------------------------------------------------------

    try:
        dados = resposta.json()

    except ValueError as erro:
        raise RuntimeError(
            "A API de inteligência artificial devolveu "
            "uma resposta que não é um JSON válido."
        ) from erro

    if not isinstance(dados, dict):
        raise RuntimeError(
            "A API de inteligência artificial devolveu "
            "um formato de resposta inválido."
        )

    if dados.get("sucesso") is False:
        detalhe = (
            dados.get("detail")
            or dados.get("erro")
            or "A API recusou a análise."
        )

        raise RuntimeError(str(detalhe))

    return dados


# ============================================================
# TRADUÇÃO / CLASSIFICAÇÃO DO RESULTADO
# ============================================================

def obter_nome_produto_detectado(
    classe,
    resultado_api,
):
    """
    Obtém o nome do produto identificado pela API.

    Prioridade:

    1. produto enviado pela própria API;
    2. classe;
    3. nome da classe.
    """

    produto = (
        resultado_api.get("produto")
        or resultado_api.get("produto_detectado")
        or resultado_api.get("produto_identificado")
        or ""
    )

    if produto:
        return str(produto).strip()

    classe_texto = str(classe or "").strip()

    if not classe_texto:
        return ""

    classe_normalizada = normalizar_texto(
        classe_texto
    )

    produtos = {
        "apple": "Maçã",
        "apple scab": "Maçã",
        "apple___apple_scab": "Maçã",
        "apple___healthy": "Maçã",

        "blueberry": "Mirtilo",
        "blueberry___healthy": "Mirtilo",

        "cherry": "Cereja",
        "cherry___healthy": "Cereja",
        "cherry___powdery_mildew": "Cereja",

        "corn": "Milho",
        "corn___healthy": "Milho",
        "corn___common_rust": "Milho",
        "corn___northern_leaf_blight": "Milho",
        "corn___cercospora_leaf_spot_gray_leaf_spot": "Milho",

        "grape": "Uva",
        "grape___healthy": "Uva",
        "grape___black_rot": "Uva",
        "grape___esca_black_measles": "Uva",
        "grape___leaf_blight_isariopsis_leaf_spot": "Uva",

        "peach": "Pêssego",
        "peach___healthy": "Pêssego",
        "peach___bacterial_spot": "Pêssego",

        "pepper": "Pimento",
        "pepper___bell___healthy": "Pimento",
        "pepper___bell___bacterial_spot": "Pimento",

        "potato": "Batata",
        "potato___healthy": "Batata",
        "potato___early_blight": "Batata",
        "potato___late_blight": "Batata",

        "raspberry": "Framboesa",
        "raspberry___healthy": "Framboesa",

        "soybean": "Soja",
        "soybean___healthy": "Soja",

        "squash": "Abóbora",
        "squash___powdery_mildew": "Abóbora",

        "strawberry": "Morango",
        "strawberry___healthy": "Morango",
        "strawberry___leaf_scorch": "Morango",

        "tomato": "Tomate",
        "tomato___healthy": "Tomate",
        "tomato___bacterial_spot": "Tomate",
        "tomato___early_blight": "Tomate",
        "tomato___late_blight": "Tomate",
        "tomato___leaf_mold": "Tomate",
        "tomato___septoria_leaf_spot": "Tomate",
        "tomato___spider_mites_two_spotted_spider_mite": "Tomate",
        "tomato___target_spot": "Tomate",
        "tomato___tomato_mosaic_virus": "Tomate",
        "tomato___tomato_yellow_leaf_curl_virus": "Tomate",

        "banana": "Banana",
        "banana___healthy": "Banana",

        "mango": "Manga",
        "mango___healthy": "Manga",

        "cassava": "Mandioca",
        "cassava___healthy": "Mandioca",

        "rice": "Arroz",
        "rice___healthy": "Arroz",

        "wheat": "Trigo",
        "wheat___healthy": "Trigo",
    }

    if classe_normalizada in produtos:
        return produtos[classe_normalizada]

    for chave, nome in produtos.items():
        if classe_normalizada.startswith(
            normalizar_texto(chave)
        ):
            return nome

    return classe_texto


def determinar_resultado_final(
    resultado_api,
    classe,
    problema,
    tipo,
):
    """
    Determina o resultado final salvo no Diagnostico.
    """

    resultado_explicitamente_informado = (
        resultado_api.get("resultado")
        or resultado_api.get("resultado_final")
        or resultado_api.get("classificacao")
        or ""
    )

    resultado_normalizado = normalizar_texto(
        resultado_explicitamente_informado
    )

    # --------------------------------------------------------
    # Resultado explícito
    # --------------------------------------------------------

    if resultado_normalizado in {
        "saudavel",
        "saude",
        "healthy",
    }:
        return "saudavel"

    if resultado_normalizado in {
        "praga",
        "pest",
        "inseto",
    }:
        return "praga"

    if resultado_normalizado in {
        "fungo",
        "fungal",
        "fungal_disease",
    }:
        return "fungo"

    if resultado_normalizado in {
        "doenca",
        "disease",
        "bacterial",
        "viral",
    }:
        return "doenca"

    if resultado_normalizado in {
        "deficiencia",
        "deficiency",
        "nutritional_deficiency",
    }:
        return "deficiencia"

    # --------------------------------------------------------
    # Tipo
    # --------------------------------------------------------

    tipo_normalizado = normalizar_texto(tipo)

    if any(
        palavra in tipo_normalizado
        for palavra in [
            "saudavel",
            "healthy",
            "normal",
        ]
    ):
        return "saudavel"

    if any(
        palavra in tipo_normalizado
        for palavra in [
            "praga",
            "pest",
            "inseto",
        ]
    ):
        return "praga"

    if any(
        palavra in tipo_normalizado
        for palavra in [
            "fung",
            "fungal",
            "fungo",
        ]
    ):
        return "fungo"

    if any(
        palavra in tipo_normalizado
        for palavra in [
            "deficien",
            "deficiency",
            "nutricional",
        ]
    ):
        return "deficiencia"

    if any(
        palavra in tipo_normalizado
        for palavra in [
            "bacter",
            "viral",
            "virus",
            "doenca",
            "disease",
        ]
    ):
        return "doenca"

    # --------------------------------------------------------
    # Problema
    # --------------------------------------------------------

    problema_normalizado = normalizar_texto(
        problema
    )

    if not problema_normalizado:
        classe_normalizada = normalizar_texto(
            classe
        )

        if any(
            palavra in classe_normalizada
            for palavra in [
                "healthy",
                "saudavel",
            ]
        ):
            return "saudavel"

    if problema_normalizado:

        if any(
            palavra in problema_normalizado
            for palavra in [
                "insect",
                "pest",
                "aphid",
                "mite",
                "caterpillar",
                "bug",
                "praga",
            ]
        ):
            return "praga"

        if any(
            palavra in problema_normalizado
            for palavra in [
                "fung",
                "mildew",
                "mold",
                "rot",
                "rust",
                "blight",
                "fungo",
            ]
        ):
            return "fungo"

        if any(
            palavra in problema_normalizado
            for palavra in [
                "deficien",
                "deficiency",
                "nutrient",
            ]
        ):
            return "deficiencia"

        return "doenca"

    # --------------------------------------------------------
    # Classe
    # --------------------------------------------------------

    classe_normalizada = normalizar_texto(
        classe
    )

    if any(
        palavra in classe_normalizada
        for palavra in [
            "healthy",
            "saudavel",
        ]
    ):
        return "saudavel"

    if any(
        palavra in classe_normalizada
        for palavra in [
            "rust",
            "mildew",
            "mold",
            "blight",
            "rot",
            "scab",
            "spot",
            "virus",
            "bacterial",
            "disease",
            "fung",
        ]
    ):
        if any(
            palavra in classe_normalizada
            for palavra in [
                "rust",
                "mildew",
                "mold",
                "fung",
                "rot",
                "scab",
                "blight",
            ]
        ):
            return "fungo"

        return "doenca"

    return "indeterminado"


# ============================================================
# DESCRIÇÃO E RECOMENDAÇÕES
# ============================================================

def construir_descricao(
    produto,
    produto_detectado,
    problema,
    tipo,
    resultado,
):
    """
    Gera uma descrição útil para o diagnóstico.

    A API FastAPI atual não devolve descricao_resultado,
    portanto o Django gera esse texto.
    """

    nome_produto = (
        produto_detectado
        or getattr(produto, "nome", "")
        or "o produto agrícola"
    )

    nome_problema = (
        problema
        or "uma condição que requer observação"
    )

    tipo_texto = str(tipo or "").strip()

    if resultado == "saudavel":
        return (
            f"A análise por inteligência artificial indica que "
            f"{nome_produto} apresenta características compatíveis "
            f"com uma condição saudável na imagem analisada. "
            f"Não foram identificados sinais relevantes de doença "
            f"ou praga na análise atual."
        )

    if resultado == "praga":
        return (
            f"A análise por inteligência artificial identificou "
            f"sinais compatíveis com a presença de {nome_problema} "
            f"em {nome_produto}. "
            f"A identificação é baseada nos padrões visuais "
            f"presentes na imagem enviada."
        )

    if resultado == "fungo":
        return (
            f"A análise por inteligência artificial identificou "
            f"sinais compatíveis com {nome_problema} em "
            f"{nome_produto}. "
            f"O resultado apresenta características associadas "
            f"a uma condição de origem fúngica."
        )

    if resultado == "deficiencia":
        return (
            f"A análise por inteligência artificial identificou "
            f"sinais compatíveis com {nome_problema} em "
            f"{nome_produto}. "
            f"Os sinais observados podem estar relacionados "
            f"a uma deficiência ou desequilíbrio nutricional."
        )

    if resultado == "doenca":

        descricao_tipo = ""

        if tipo_texto:
            descricao_tipo = (
                f' A classificação indicada pela IA é '
                f'“{tipo_texto}”.'
            )

        return (
            f"A análise por inteligência artificial identificou "
            f"sinais compatíveis com {nome_problema} em "
            f"{nome_produto}.{descricao_tipo} "
            f"O resultado foi obtido a partir dos padrões "
            f"visuais encontrados na imagem."
        )

    return (
        f"A análise de {nome_produto} não permitiu estabelecer "
        f"uma classificação conclusiva. "
        f"Recomenda-se observar novamente o produto com uma "
        f"imagem nítida e com boa iluminação."
    )


def construir_recomendacoes(
    produto,
    produto_detectado,
    problema,
    tipo,
    resultado,
):
    """
    Gera recomendações práticas para o diagnóstico.
    """

    nome_produto = (
        produto_detectado
        or getattr(produto, "nome", "")
        or "o produto"
    )

    nome_problema = (
        problema
        or "a condição observada"
    )

    if resultado == "saudavel":
        return (
            f"Continue a acompanhar regularmente {nome_produto}, "
            f"mantendo boas práticas de cultivo, irrigação e "
            f"nutrição. Observe folhas, frutos e caules "
            f"periodicamente para identificar alterações precoces."
        )

    if resultado == "praga":
        return (
            f"Inspecione cuidadosamente {nome_produto} e as plantas "
            f"próximas para verificar a presença de outros sinais "
            f"de {nome_problema}. Remova partes muito afetadas "
            f"quando apropriado, mantenha a área limpa e utilize "
            f"medidas de controlo adequadas à cultura e à praga "
            f"identificada."
        )

    if resultado == "fungo":
        return (
            f"Evite excesso de humidade sobre as folhas de "
            f"{nome_produto}, melhore a circulação de ar e remova "
            f"partes muito afetadas quando isso for recomendado "
            f"para a cultura. Evite espalhar material vegetal "
            f"suspeito para plantas saudáveis."
        )

    if resultado == "deficiencia":
        return (
            f"Observe o estado geral de {nome_produto} e avalie "
            f"as condições do solo. Antes de aplicar fertilizantes, "
            f"procure confirmar a deficiência através de avaliação "
            f"agronómica ou análise do solo, evitando aplicações "
            f"desnecessárias."
        )

    if resultado == "doenca":
        return (
            f"Separe, quando possível, plantas com sinais de "
            f"{nome_problema}, evite manipulação desnecessária das "
            f"partes afetadas e mantenha boas condições de higiene "
            f"na área de cultivo. Para definir o tratamento adequado, "
            f"confirme a doença com um técnico agrícola antes de "
            f"aplicar qualquer produto."
        )

    return (
        f"Repita a análise de {nome_produto} com uma fotografia "
        f"nítida, bem iluminada e focada na parte afetada. "
        f"Compare a evolução dos sinais ao longo dos dias e, "
        f"caso persistam, procure orientação de um técnico agrícola."
    )


# ============================================================
# COMPATIBILIDADE
# ============================================================

def verificar_compatibilidade(
    produto,
    produto_detectado,
):
    """
    Verifica se o produto identificado pela IA corresponde
    ao produto selecionado pelo utilizador.
    """

    if not produto_detectado:
        return None

    nome_produto = getattr(
        produto,
        "nome",
        "",
    )

    if not nome_produto:
        return None

    a = normalizar_texto(nome_produto)
    b = normalizar_texto(produto_detectado)

    if not a or not b:
        return None

    if a == b:
        return True

    if a in b or b in a:
        return True

    aliases = {
        "maca": ["apple"],
        "apple": ["maca"],

        "banana": ["banana"],

        "milho": ["corn", "maize"],
        "corn": ["milho", "maize"],

        "tomate": ["tomato"],
        "tomato": ["tomate"],

        "batata": ["potato"],
        "potato": ["batata"],

        "uva": ["grape"],
        "grape": ["uva"],

        "pimento": ["pepper", "bell pepper"],
        "pepper": ["pimento"],

        "morango": ["strawberry"],
        "strawberry": ["morango"],

        "soja": ["soybean"],
        "soybean": ["soja"],

        "abobora": ["squash"],
        "squash": ["abobora"],

        "cereja": ["cherry"],
        "cherry": ["cereja"],

        "mirtilo": ["blueberry"],
        "blueberry": ["mirtilo"],

        "pessego": ["peach"],
        "peach": ["pessego"],

        "framboesa": ["raspberry"],
        "raspberry": ["framboesa"],
    }

    if b in aliases.get(a, []):
        return True

    if a in aliases.get(b, []):
        return True

    return False


# ============================================================
# OBSERVAÇÕES
# ============================================================

def construir_observacoes(
    produto,
    resultado,
    compativel,
):
    """
    Gera observações complementares para o diagnóstico.
    """

    nome_produto = (
        getattr(produto, "nome", "")
        or resultado.get("produto")
        or "produto analisado"
    )

    produto_detectado = (
        resultado.get("produto")
        or ""
    )

    observacoes = []

    # --------------------------------------------------------
    # Compatibilidade
    # --------------------------------------------------------

    if compativel is False:
        observacoes.append(
            "A IA identificou um produto diferente daquele "
            f"selecionado: {produto_detectado}."
        )

        observacoes.append(
            "Confirme se a imagem corresponde ao produto "
            f"selecionado ({nome_produto}) antes de utilizar "
            "o resultado como referência."
        )

    elif compativel is True:
        observacoes.append(
            "O produto identificado pela IA é compatível "
            "com o produto selecionado."
        )

    # --------------------------------------------------------
    # Confiança
    # --------------------------------------------------------

    confianca = resultado.get(
        "confianca",
        0,
    )

    try:
        confianca = float(confianca)

    except (TypeError, ValueError):
        confianca = 0

    if confianca >= 90:
        observacoes.append(
            "A análise apresentou um nível elevado de confiança."
        )

    elif confianca >= 70:
        observacoes.append(
            "A análise apresentou um nível moderado de confiança. "
            "Recomenda-se acompanhar a evolução dos sinais."
        )

    elif confianca > 0:
        observacoes.append(
            "A análise apresentou confiança reduzida. "
            "Considere realizar uma nova análise com uma imagem "
            "mais nítida."
        )

    # --------------------------------------------------------
    # Resultado indeterminado
    # --------------------------------------------------------

    if resultado.get("resultado") == "indeterminado":
        observacoes.append(
            "O resultado não foi conclusivo. "
            "Uma nova fotografia, com melhor iluminação e foco, "
            "pode melhorar a análise."
        )

    if not observacoes:
        observacoes.append(
            "O resultado deve ser acompanhado juntamente com "
            "a evolução visual da cultura."
        )

    return " ".join(observacoes)


# ============================================================
# NORMALIZAÇÃO DO RESULTADO DA API
# ============================================================

def normalizar_resultado_ia(
    dados_api,
    produto=None,
):
    """
    Converte a resposta real da FastAPI para o formato
    utilizado pelo Django.
    """

    if not isinstance(dados_api, dict):
        raise ValueError(
            "A resposta da API de IA não possui um formato válido."
        )

    # --------------------------------------------------------
    # Resultado pode estar dentro de "resultado"
    # --------------------------------------------------------

    resultado_api = dados_api.get("resultado")

    if not isinstance(resultado_api, dict):
        resultado_api = dados_api

    # --------------------------------------------------------
    # Classe
    # --------------------------------------------------------

    classe = (
        resultado_api.get("classe")
        or resultado_api.get("class")
        or resultado_api.get("classe_identificada")
        or resultado_api.get("class_name")
        or ""
    )

    classe = str(classe).strip()

    # --------------------------------------------------------
    # Produto
    # --------------------------------------------------------

    produto_detectado = obter_nome_produto_detectado(
        classe,
        resultado_api,
    )

    # --------------------------------------------------------
    # Problema
    # --------------------------------------------------------

    problema = (
        resultado_api.get("problema")
        or resultado_api.get("doenca")
        or resultado_api.get("doenca_identificada")
        or resultado_api.get("problema_identificado")
        or ""
    )

    problema = str(problema).strip()

    # --------------------------------------------------------
    # Tipo
    # --------------------------------------------------------

    tipo = (
        resultado_api.get("tipo")
        or resultado_api.get("tipo_resultado")
        or resultado_api.get("categoria")
        or ""
    )

    tipo = str(tipo).strip()

    # --------------------------------------------------------
    # Confiança
    # --------------------------------------------------------

    confianca = (
        resultado_api.get("confianca")
        or resultado_api.get("confidence")
        or resultado_api.get("precisao")
        or 0
    )

    try:
        confianca = float(confianca)

        if 0 < confianca <= 1:
            confianca *= 100

    except (TypeError, ValueError):
        confianca = 0

    confianca = max(
        0,
        min(
            100,
            confianca,
        ),
    )

    confianca = round(
        confianca,
        2,
    )

    # --------------------------------------------------------
    # Resultado final
    # --------------------------------------------------------

    resultado_final = determinar_resultado_final(
        resultado_api=resultado_api,
        classe=classe,
        problema=problema,
        tipo=tipo,
    )

    # --------------------------------------------------------
    # Descrição
    # --------------------------------------------------------

    descricao = (
        resultado_api.get("descricao")
        or resultado_api.get("descricao_resultado")
        or resultado_api.get("description")
        or ""
    )

    descricao = str(descricao).strip()

    if not descricao:
        descricao = construir_descricao(
            produto=produto,
            produto_detectado=produto_detectado,
            problema=problema,
            tipo=tipo,
            resultado=resultado_final,
        )

    # --------------------------------------------------------
    # Recomendações
    # --------------------------------------------------------

    recomendacoes = (
        resultado_api.get("recomendacoes")
        or resultado_api.get("recomendacoes_resultado")
        or resultado_api.get("recommendations")
        or ""
    )

    recomendacoes = str(recomendacoes).strip()

    if not recomendacoes:
        recomendacoes = construir_recomendacoes(
            produto=produto,
            produto_detectado=produto_detectado,
            problema=problema,
            tipo=tipo,
            resultado=resultado_final,
        )

    # --------------------------------------------------------
    # Principais previsões
    # --------------------------------------------------------

    principais_previsoes = (
        resultado_api.get("principais_previsoes")
        or resultado_api.get("top_predictions")
        or []
    )

    if not isinstance(principais_previsoes, list):
        principais_previsoes = []

    # --------------------------------------------------------
    # Retorno normalizado
    # --------------------------------------------------------

    return {
        "classe": classe,

        "produto": produto_detectado,

        "produtos": (
            [produto_detectado]
            if produto_detectado
            else []
        ),

        "problema": problema,

        "tipo": tipo,

        "confianca": confianca,

        "resultado": resultado_final,

        "doenca": problema,

        "descricao": descricao,

        "recomendacoes": recomendacoes,

        "principais_previsoes": principais_previsoes,

        "tempo_api": dados_api.get("tempo_api"),

        "tempo_predicao": resultado_api.get(
            "tempo_predicao"
        ),

        "tempo_total": resultado_api.get(
            "tempo_total"
        ),
    }


# ============================================================
# ANÁLISE COMPLETA
# ============================================================

def analisar_imagem(
    imagem,
    produto=None,
    nome_imagem=None,
):
    """
    Executa uma análise completa através da API externa.
    """

    if not nome_imagem:

        if produto is not None:
            nome_imagem = obter_nome_imagem(
                produto
            )

        else:
            nome_imagem = "imagem.jpg"

    content_type = obter_content_type(
        nome_imagem
    )

    dados_api = enviar_para_api_ia(
        imagem=imagem,
        nome_imagem=nome_imagem,
        content_type=content_type,
    )

    return normalizar_resultado_ia(
        dados_api=dados_api,
        produto=produto,
    )


# ============================================================
# PÁGINA PRINCIPAL
# ============================================================

@login_required
def diagnostico(request):
    """
    Página principal do diagnóstico.
    """

    produtos = (
        ProdutoAgricola.objects
        .filter(
            ativo=True,
            analise_por_imagem=True,
        )
        .order_by("nome")
    )

    contexto = {
        "produtos": produtos,
    }

    return render(
        request,
        "diagnostico/diagnostico.html",
        contexto,
    )


# ============================================================
# DIAGNÓSTICO DE UM PRODUTO
# ============================================================

@login_required
def diagnostico_produto(
    request,
    produto_id,
):
    """
    Página de análise de um produto específico.
    """

    produto = obter_produto(
        produto_id
    )

    contexto = {
        "produto": produto,
    }

    return render(
        request,
        "diagnostico/diagnostico_produto.html",
        contexto,
    )


# ============================================================
# REALIZAR ANÁLISE
# ============================================================

@login_required
@require_POST
def analisar(
    request,
    produto_id=None,
):
    """
    Recebe o pedido de análise, obtém a imagem do produto,
    envia para a API e grava o resultado no banco de dados.
    """

    diagnostico_obj = None

    try:

        # ----------------------------------------------------
        # Produto
        # ----------------------------------------------------

        if produto_id is None:
            produto_id = request.POST.get(
                "produto_id"
            )

        if not produto_id:
            raise ValueError(
                "Nenhum produto foi selecionado."
            )

        produto = obter_produto(
            produto_id
        )

        # ----------------------------------------------------
        # Imagem
        # ----------------------------------------------------

        if not produto.imagem:
            raise ValueError(
                "O produto selecionado não possui uma imagem."
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

        # ----------------------------------------------------
        # Criar diagnóstico
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # API IA
        # ----------------------------------------------------

        resultado = analisar_imagem(
            imagem=imagem_bytes,
            produto=produto,
            nome_imagem=nome_imagem,
        )

        # ----------------------------------------------------
        # Produto detectado
        # ----------------------------------------------------

        produto_detectado = (
            resultado.get("produto")
            or ""
        )

        # ----------------------------------------------------
        # Compatibilidade
        # ----------------------------------------------------

        compativel = verificar_compatibilidade(
            produto,
            produto_detectado,
        )

        # ----------------------------------------------------
        # Observações
        # ----------------------------------------------------

        observacoes = construir_observacoes(
            produto,
            resultado,
            compativel,
        )

        # ----------------------------------------------------
        # Gravar resultado
        # ----------------------------------------------------

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
                or "indeterminado"
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
            "A análise do produto foi concluída com sucesso.",
        )

        return redirect(
            "diagnostico:detalhe",
            diagnostico_id=diagnostico_obj.pk,
        )

    except Exception as exc:

        erro = str(exc).strip()

        if not erro:
            erro = (
                "Ocorreu um erro desconhecido "
                "durante o diagnóstico."
            )

        # ----------------------------------------------------
        # Guardar erro
        # ----------------------------------------------------

        if diagnostico_obj is not None:

            try:

                diagnostico_obj.status = "erro"

                diagnostico_obj.resultado = (
                    "indeterminado"
                )

                diagnostico_obj.confianca = 0

                diagnostico_obj.erro = erro

                diagnostico_obj.observacoes = (
                    "O diagnóstico não pôde ser concluído "
                    "devido a um erro durante o processamento."
                )

                diagnostico_obj.save(
                    update_fields=[
                        "status",
                        "resultado",
                        "confianca",
                        "erro",
                        "observacoes",
                    ]
                )

            except Exception:
                pass

        messages.error(
            request,
            f"Não foi possível concluir o diagnóstico: {erro}",
        )

        if produto_id:
            return redirect(
                "diagnostico:diagnostico_produto",
                produto_id=produto_id,
            )

        return redirect(
            "diagnostico:diagnostico"
        )


# ============================================================
# ANÁLISE GERAL
# ============================================================

@login_required
@require_POST
def analisar_geral(request):
    """
    Recebe uma análise iniciada pela página geral.
    """

    produto_id = (
        request.POST.get("produto_id")
        or request.POST.get("produto")
        or request.POST.get("id_produto")
    )

    if not produto_id:

        messages.error(
            request,
            "Selecione um produto antes de iniciar a análise.",
        )

        return redirect(
            "diagnostico:diagnostico"
        )

    return analisar(
        request,
        produto_id=produto_id,
    )


# ============================================================
# HISTÓRICO DO PRODUTO
# ============================================================

@login_required
def historico_produto(
    request,
    produto_id,
):
    """
    Mostra o histórico de diagnósticos do produto
    pertencentes ao utilizador autenticado.
    """

    produto = obter_produto(
        produto_id
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
            "-criado_em",
            "-id",
        )
    )

    contexto = {
        "produto": produto,
        "diagnosticos": diagnosticos,
    }

    return render(
        request,
        "diagnostico/historico_produto.html",
        contexto,
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
    Exibe os detalhes de um diagnóstico.

    Esta é a função utilizada oficialmente por
    diagnostico/urls.py.
    """

    diagnostico_obj = get_object_or_404(
        Diagnostico.objects.select_related(
            "produto",
            "usuario",
        ),
        pk=diagnostico_id,
        usuario=request.user,
    )

    contexto = {
        "diagnostico": diagnostico_obj,

        "resultado": (
            diagnostico_obj.resultado
        ),

        "produto": (
            diagnostico_obj.produto
        ),

        "descricao": (
            diagnostico_obj.descricao_resultado
        ),

        "recomendacoes": (
            diagnostico_obj.recomendacoes
        ),

        "observacoes": (
            diagnostico_obj.observacoes
        ),
    }

    return render(
        request,
        "diagnostico/detalhe.html",
        contexto,
    )


# ============================================================
# COMPATIBILIDADE COM O NOME ANTIGO "detalhe"
# ============================================================

@login_required
def detalhe(
    request,
    diagnostico_id,
):
    """
    Alias de compatibilidade.

    Mantém qualquer código antigo que ainda utilize
    views.detalhe().
    """

    return detalhe_diagnostico(
        request,
        diagnostico_id=diagnostico_id,
    )


# ============================================================
# ALIAS PARA DIAGNÓSTICO IA
# ============================================================

@login_required
def diagnostico_ia(request):
    """
    Alias para a página principal de diagnóstico.
    """

    return diagnostico(
        request
    )


# ============================================================
# ALIAS PARA REALIZAR DIAGNÓSTICO
# ============================================================

@login_required
def realizar_diagnostico(request):
    """
    Compatibilidade com chamadas antigas.

    Aceita apenas POST para iniciar uma análise.
    """

    if request.method != "POST":

        return redirect(
            "diagnostico:diagnostico"
        )

    produto_id = (
        request.POST.get("produto_id")
        or request.POST.get("produto")
        or request.POST.get("id_produto")
    )

    if not produto_id:

        messages.error(
            request,
            "Selecione um produto antes de realizar a análise.",
        )

        return redirect(
            "diagnostico:diagnostico"
        )

    return analisar(
        request,
        produto_id=produto_id,
    )
