import mimetypes
import os
from pathlib import Path

import requests
from PIL import Image, UnidentifiedImageError


# ============================================================
# CONFIGURAÇÕES
# ============================================================

MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB

# Em produção, a Vercel deverá usar a variável:
# AGROIA_API_URL=https://agroia-api.onrender.com/analisar
#
# O endereço local continua como fallback para desenvolvimento.
API_URL = os.getenv(
    "AGROIA_API_URL",
    "http://127.0.0.1:8001/analisar",
).strip().rstrip("/")

API_TIMEOUT = int(
    os.getenv(
        "AGROIA_API_TIMEOUT",
        "120",
    )
)


# ============================================================
# NORMALIZAR TEXTO
# ============================================================

def normalizar_texto(valor):
    """
    Converte um valor para texto normalizado.
    """
    if valor is None:
        return ""

    return str(valor).strip().lower()


# ============================================================
# OBTER NOME DO PRODUTO
# ============================================================

def obter_nome_produto(produto):
    """
    Obtém o nome do produto Django.
    """
    if produto is None:
        return ""

    nome = getattr(
        produto,
        "nome",
        "",
    )

    return normalizar_texto(nome)


# ============================================================
# NORMALIZAR CULTURA
# ============================================================

def normalizar_cultura(valor):
    """
    Converte diferentes formas de identificação de uma
    cultura para um nome padrão utilizado pelo sistema.
    """

    texto = normalizar_texto(valor)

    if not texto:
        return ""

    # Remover caracteres utilizados nas classes da IA
    texto = (
        texto
        .replace("_", " ")
        .replace("(", "")
        .replace(")", "")
        .replace(",", "")
        .strip()
    )

    # Remover espaços duplicados
    texto = " ".join(texto.split())

    equivalencias = {

        # ----------------------------------------------------
        # MILHO
        # ----------------------------------------------------
        "milho": "milho",
        "corn": "milho",
        "maize": "milho",
        "corn maize": "milho",
        "corn maize healthy": "milho",
        "corn maize common rust": "milho",

        # ----------------------------------------------------
        # TOMATE
        # ----------------------------------------------------
        "tomate": "tomate",
        "tomato": "tomate",

        # ----------------------------------------------------
        # BATATA
        # ----------------------------------------------------
        "batata": "batata",
        "potato": "batata",

        # ----------------------------------------------------
        # MAÇÃ
        # ----------------------------------------------------
        "maca": "maçã",
        "maçã": "maçã",
        "apple": "maçã",

        # ----------------------------------------------------
        # UVA
        # ----------------------------------------------------
        "uva": "uva",
        "grape": "uva",

        # ----------------------------------------------------
        # PÊSSEGO
        # ----------------------------------------------------
        "pessego": "pêssego",
        "pêssego": "pêssego",
        "peach": "pêssego",

        # ----------------------------------------------------
        # CEREJA
        # ----------------------------------------------------
        "cereja": "cereja",
        "cherry": "cereja",

        # ----------------------------------------------------
        # LARANJA
        # ----------------------------------------------------
        "laranja": "laranja",
        "orange": "laranja",

        # ----------------------------------------------------
        # SOJA
        # ----------------------------------------------------
        "soja": "soja",
        "soybean": "soja",

        # ----------------------------------------------------
        # MORANGO
        # ----------------------------------------------------
        "morango": "morango",
        "strawberry": "morango",

        # ----------------------------------------------------
        # FRAMBOESA
        # ----------------------------------------------------
        "framboesa": "framboesa",
        "raspberry": "framboesa",

        # ----------------------------------------------------
        # MIRTILO
        # ----------------------------------------------------
        "mirtilo": "mirtilo",
        "blueberry": "mirtilo",

        # ----------------------------------------------------
        # PIMENTÃO
        # ----------------------------------------------------
        "pimentao": "pimentão",
        "pimentão": "pimentão",
        "pepper": "pimentão",
        "pepper bell": "pimentão",

        # ----------------------------------------------------
        # ABÓBORA
        # ----------------------------------------------------
        "abobora": "abóbora",
        "abóbora": "abóbora",
        "squash": "abóbora",
    }

    return equivalencias.get(
        texto,
        texto,
    )


# ============================================================
# IDENTIFICAR PRODUTO DA CLASSE
# ============================================================

def identificar_produto_da_classe(classe):
    """
    Identifica a cultura/produto a partir da classe retornada
    pela API de inteligência artificial.

    Exemplos:

        Corn_(maize)___healthy
        -> milho

        Tomato___Late_blight
        -> tomate
    """

    if not classe:
        return ""

    classe_original = str(classe).strip()

    if "___" in classe_original:
        produto = classe_original.split(
            "___",
            1,
        )[0]
    else:
        produto = classe_original

    return normalizar_cultura(produto)


# ============================================================
# IDENTIFICAR CULTURA
# ============================================================

def identificar_cultura_da_classe(classe):
    """
    Alias para identificação da cultura.
    """
    return identificar_produto_da_classe(classe)


# ============================================================
# VALIDAR PRODUTO COM CLASSE
# ============================================================

def validar_produto_com_classe(produto, classe):
    """
    Verifica se o produto selecionado no Django corresponde
    à cultura identificada pela IA.
    """

    if produto is None or not classe:
        return {
            "corresponde": True,
            "mensagem": "",
        }

    nome_produto = normalizar_cultura(
        getattr(
            produto,
            "nome",
            "",
        )
    )

    produto_detectado = identificar_produto_da_classe(
        classe
    )

    # Se não conseguirmos determinar algum dos dois,
    # não bloqueamos o diagnóstico.
    if not nome_produto or not produto_detectado:
        return {
            "corresponde": True,
            "mensagem": "",
        }

    if nome_produto == produto_detectado:
        return {
            "corresponde": True,
            "mensagem": "",
        }

    nome_original = getattr(
        produto,
        "nome",
        "",
    )

    return {
        "corresponde": False,
        "mensagem": (
            "A inteligência artificial identificou "
            f"'{produto_detectado}', mas o produto selecionado "
            f"é '{nome_original}'. "
            "Verifique se a imagem corresponde ao produto."
        ),
    }


# ============================================================
# VALIDAR IMAGEM
# ============================================================

def validar_imagem(image_file):
    """
    Valida a imagem antes de enviá-la para a API externa.
    """

    if image_file is None:
        raise ValueError(
            "Nenhuma imagem foi fornecida para análise."
        )

    # --------------------------------------------------------
    # TAMANHO
    # --------------------------------------------------------

    try:
        tamanho = getattr(
            image_file,
            "size",
            0,
        )

        if tamanho and tamanho > MAX_IMAGE_SIZE:
            raise ValueError(
                "A imagem não pode ultrapassar 10 MB."
            )

    except ValueError:
        raise

    except Exception:
        pass

    # --------------------------------------------------------
    # ABRIR E VALIDAR IMAGEM
    # --------------------------------------------------------

    imagem = None

    try:

        if hasattr(image_file, "open"):

            image_file.open("rb")

            try:
                imagem = Image.open(image_file)
                imagem.load()

            finally:

                try:
                    image_file.close()
                except Exception:
                    pass

        else:

            if hasattr(image_file, "seek"):
                image_file.seek(0)

            imagem = Image.open(image_file)
            imagem.load()

    except UnidentifiedImageError as exc:

        raise ValueError(
            "O arquivo associado ao produto não é "
            "uma imagem válida."
        ) from exc

    except ValueError:
        raise

    except Exception as exc:

        raise ValueError(
            "Não foi possível abrir a imagem cadastrada "
            "no produto."
        ) from exc

    # --------------------------------------------------------
    # CONVERTER PARA RGB
    # --------------------------------------------------------

    try:

        imagem = imagem.convert("RGB")

    except Exception as exc:

        raise ValueError(
            "Não foi possível processar a imagem "
            "cadastrada no produto."
        ) from exc

    return imagem


# ============================================================
# OBTER BYTES DA IMAGEM
# ============================================================

def obter_bytes_imagem(image_file):
    """
    Obtém os bytes reais da imagem.
    """

    if image_file is None:
        raise ValueError(
            "Nenhuma imagem foi fornecida para análise."
        )

    try:

        if hasattr(image_file, "open"):

            image_file.open("rb")

            try:
                dados = image_file.read()

            finally:

                try:
                    image_file.close()
                except Exception:
                    pass

        else:

            if hasattr(image_file, "seek"):
                image_file.seek(0)

            dados = image_file.read()

    except Exception as exc:

        raise ValueError(
            "Não foi possível ler a imagem "
            "cadastrada no produto."
        ) from exc

    if not dados:
        raise ValueError(
            "A imagem cadastrada no produto está vazia."
        )

    if len(dados) > MAX_IMAGE_SIZE:
        raise ValueError(
            "A imagem não pode ultrapassar 10 MB."
        )

    return dados


# ============================================================
# DETERMINAR MIME TYPE
# ============================================================

def obter_content_type(nome_arquivo):
    """
    Determina o tipo MIME da imagem.
    """

    extensao = Path(
        nome_arquivo or ""
    ).suffix.lower()

    tipos = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }

    if extensao in tipos:
        return tipos[extensao]

    content_type, _ = mimetypes.guess_type(
        nome_arquivo or ""
    )

    if content_type in {
        "image/jpeg",
        "image/png",
        "image/webp",
    }:
        return content_type

    return "image/jpeg"


# ============================================================
# ENVIAR IMAGEM PARA A API EXTERNA
# ============================================================

def enviar_para_api(
    imagem_bytes,
    nome_arquivo="imagem.jpg",
):
    """
    Envia a imagem para a API externa AgroIA.

    Produção:
        https://agroia-api.onrender.com/analisar

    Desenvolvimento:
        http://127.0.0.1:8001/analisar
    """

    if not imagem_bytes:
        raise ValueError(
            "Nenhuma imagem disponível para enviar à API."
        )

    if len(imagem_bytes) > MAX_IMAGE_SIZE:
        raise ValueError(
            "A imagem não pode ultrapassar 10 MB."
        )

    content_type = obter_content_type(
        nome_arquivo
    )

    arquivos = {
        "imagem": (
            nome_arquivo,
            imagem_bytes,
            content_type,
        )
    }

    try:

        resposta = requests.post(
            API_URL,
            files=arquivos,
            timeout=API_TIMEOUT,
        )

    except requests.exceptions.ConnectionError as exc:

        raise ValueError(
            "Não foi possível conectar à API de "
            "inteligência artificial. "
            f"Verifique se a API AgroIA está disponível em "
            f"{API_URL}."
        ) from exc

    except requests.exceptions.Timeout as exc:

        raise ValueError(
            "A API de inteligência artificial demorou "
            "demasiado tempo para responder. "
            "Tente novamente."
        ) from exc

    except requests.exceptions.RequestException as exc:

        raise ValueError(
            "Ocorreu um erro ao comunicar com a API "
            "de inteligência artificial."
        ) from exc

    # ========================================================
    # ERROS HTTP
    # ========================================================

    if resposta.status_code >= 400:

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

        except Exception:
            pass

        if resposta.status_code == 400:

            raise ValueError(
                detalhe
                or "A API rejeitou a imagem enviada."
            )

        if resposta.status_code == 413:

            raise ValueError(
                "A imagem não pode ultrapassar 10 MB."
            )

        if resposta.status_code == 422:

            raise ValueError(
                detalhe
                or (
                    "A API recebeu dados inválidos "
                    "para realizar a análise."
                )
            )

        if resposta.status_code >= 500:

            raise ValueError(
                "A API de inteligência artificial "
                "encontrou um erro interno. "
                "Verifique se o modelo está funcionando."
            )

        raise ValueError(
            detalhe
            or (
                "A API de inteligência artificial "
                "não conseguiu processar a imagem."
            )
        )

    # ========================================================
    # JSON
    # ========================================================

    try:

        dados = resposta.json()

    except ValueError as exc:

        raise ValueError(
            "A API de inteligência artificial "
            "retornou uma resposta inválida."
        ) from exc

    if not isinstance(dados, dict):

        raise ValueError(
            "A API de inteligência artificial "
            "retornou um formato inesperado."
        )

    return dados


# ============================================================
# EXTRAIR RESULTADO DA API
# ============================================================

def extrair_resultado_api(dados_api):
  

    if not dados_api:

        raise ValueError(
            "A API de inteligência artificial "
            "não retornou nenhum resultado."
        )

    sucesso = dados_api.get(
        "sucesso",
        False,
    )

    if sucesso is False:

        detalhe = (
            dados_api.get("detail")
            or dados_api.get("erro")
            or dados_api.get("message")
            or ""
        )

        raise ValueError(
            detalhe
            or (
                "A API de inteligência artificial "
                "não conseguiu concluir a análise."
            )
        )

    resultado = dados_api.get(
        "resultado"
    )

    if not isinstance(resultado, dict):

        raise ValueError(
            "A API de inteligência artificial "
            "não retornou os dados do diagnóstico."
        )

    return resultado


# ============================================================
# NORMALIZAR RESULTADO DA API
# ============================================================

def normalizar_resultado_api(
    resultado,
    produto=None,
):
    """
    Converte o resultado da API externa para o formato
    utilizado pelo sistema Django.
    """

    if not resultado:

        raise ValueError(
            "A inteligência artificial não retornou "
            "nenhum resultado."
        )

    # --------------------------------------------------------
    # CAMPOS PRINCIPAIS
    # --------------------------------------------------------

    classe = str(
        resultado.get(
            "classe",
            "",
        )
        or ""
    ).strip()

    produto_detectado = str(
        resultado.get(
            "produto",
            "",
        )
        or ""
    ).strip()

    problema = str(
        resultado.get(
            "problema",
            "",
        )
        or ""
    ).strip()

    tipo = str(
        resultado.get(
            "tipo",
            "",
        )
        or ""
    ).strip()

    # --------------------------------------------------------
    # CONFIANÇA
    # --------------------------------------------------------

    try:

        confianca = float(
            resultado.get(
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

    # --------------------------------------------------------
    # PRINCIPAIS PREVISÕES
    # --------------------------------------------------------

    principais_previsoes = resultado.get(
        "principais_previsoes",
        [],
    )

    if not isinstance(
        principais_previsoes,
        list,
    ):
        principais_previsoes = []

    # --------------------------------------------------------
    # NORMALIZAÇÃO
    # --------------------------------------------------------

    tipo_lower = normalizar_texto(
        tipo
    )

    problema_lower = normalizar_texto(
        problema
    )

    # --------------------------------------------------------
    # DETERMINAR RESULTADO
    # --------------------------------------------------------

    if (
        "healthy" in problema_lower
        or "saudavel" in problema_lower
        or "saudável" in problema_lower
        or "healthy" in tipo_lower
        or "saudavel" in tipo_lower
        or "saudável" in tipo_lower
    ):

        resultado_final = "saudavel"

    elif "praga" in tipo_lower:

        resultado_final = "praga"

    elif (
        "fung" in tipo_lower
        or "fungo" in tipo_lower
        or "fungica" in tipo_lower
        or "fúngica" in tipo_lower
    ):

        resultado_final = "fungo"

    elif "viral" in tipo_lower:

        resultado_final = "doenca"

    elif "bacteriana" in tipo_lower:

        resultado_final = "doenca"

    elif (
        "deficiência" in tipo_lower
        or "deficiencia" in tipo_lower
    ):

        resultado_final = "deficiencia"

    elif (
        problema
        and problema_lower not in {
            "healthy",
            "saudavel",
            "saudável",
        }
    ):

        resultado_final = "doenca"

    else:

        resultado_final = "indeterminado"

    # --------------------------------------------------------
    # DOENÇA
    # --------------------------------------------------------

    if resultado_final == "saudavel":

        doenca = ""

    elif problema:

        doenca = problema

    else:

        doenca = ""

    # --------------------------------------------------------
    # NOME DO PRODUTO
    # --------------------------------------------------------

    produto_nome = (
        produto_detectado
        or obter_nome_produto(produto)
        or "o produto analisado"
    )

    # --------------------------------------------------------
    # DESCRIÇÃO
    # --------------------------------------------------------

    if resultado_final == "saudavel":

        descricao = (
            "A inteligência artificial identificou "
            f"{produto_nome} como saudável."
        )

    elif doenca:

        descricao = (
            "A inteligência artificial identificou "
            f"{doenca} em {produto_nome}."
        )

    else:

        descricao = (
            "A inteligência artificial não conseguiu "
            "determinar com precisão o problema presente "
            "na imagem."
        )

    # --------------------------------------------------------
    # RECOMENDAÇÕES
    # --------------------------------------------------------

    if resultado_final == "saudavel":

        recomendacoes = (
            "A cultura foi identificada como saudável. "
            "Continue acompanhando regularmente a plantação "
            "e mantenha boas práticas agrícolas. "
            "Faça novas análises caso sejam observadas "
            "alterações nas folhas, frutos ou demais partes "
            "da planta."
        )

    elif doenca:

        recomendacoes = (
            "A imagem apresenta características associadas "
            f"a {doenca}. Recomenda-se acompanhar a evolução "
            "dos sintomas e procurar orientação de um técnico "
            "agrícola ou agrónomo para confirmar o diagnóstico "
            "e definir o tratamento adequado."
        )

    else:

        recomendacoes = (
            "A inteligência artificial não conseguiu "
            "determinar o problema com segurança. "
            "Recomenda-se realizar uma nova análise com "
            "uma imagem nítida e bem iluminada e procurar "
            "orientação técnica quando necessário."
        )

    # --------------------------------------------------------
    # CONFIANÇA BAIXA
    # --------------------------------------------------------

    baixa_confianca = confianca < 60.0

    # --------------------------------------------------------
    # COMPATIBILIDADE
    # --------------------------------------------------------

    compatibilidade = validar_produto_com_classe(
        produto,
        classe,
    )

    # --------------------------------------------------------
    # RESULTADO FINAL
    # --------------------------------------------------------

    return {
        "classe": classe,

        "produto": produto_detectado,

        "produtos": produto_detectado,

        "problema": problema,

        "tipo": tipo,

        "confianca": confianca,

        "resultado": resultado_final,

        "doenca": doenca,

        "descricao": descricao,

        "recomendacoes": recomendacoes,

        "principais_previsoes": (
            principais_previsoes
        ),

        "produto_compativel": (
            compatibilidade["corresponde"]
        ),

        "mensagem_compatibilidade": (
            compatibilidade["mensagem"]
        ),

        "baixa_confianca": baixa_confianca,
    }


# ============================================================
# FUNÇÃO PRINCIPAL — ANALISAR IMAGEM
# ============================================================

def analisar_imagem(
    image_file=None,
    produto=None,
):
    """
    Função principal utilizada pela views.py.

    Fluxo:

        Produto Django
              ↓
        Imagem cadastrada
              ↓
        Validação
              ↓
        Bytes da imagem
              ↓
        API externa Render
              ↓
        Modelo IA
              ↓
        Resultado JSON
              ↓
        Normalização
              ↓
        Django
    """

    # ========================================================
    # OBTER IMAGEM DO PRODUTO
    # ========================================================

    if produto is not None:

        produto_imagem = getattr(
            produto,
            "imagem",
            None,
        )

        if not produto_imagem:

            raise ValueError(
                "O produto selecionado não possui "
                "uma imagem cadastrada."
            )

        image_file = produto_imagem

    # ========================================================
    # VERIFICAR IMAGEM
    # ========================================================

    if image_file is None:

        raise ValueError(
            "Nenhuma imagem disponível para realizar "
            "o diagnóstico."
        )

    # ========================================================
    # VALIDAR IMAGEM
    # ========================================================

    validar_imagem(
        image_file
    )

    # ========================================================
    # OBTER BYTES
    # ========================================================

    imagem_bytes = obter_bytes_imagem(
        image_file
    )

    # ========================================================
    # NOME DO ARQUIVO
    # ========================================================

    nome_arquivo = "imagem.jpg"

    try:

        nome_arquivo = Path(
            getattr(
                image_file,
                "name",
                "imagem.jpg",
            )
        ).name

    except Exception:

        nome_arquivo = "imagem.jpg"

    if not nome_arquivo:
        nome_arquivo = "imagem.jpg"

    # ========================================================
    # ENVIAR PARA API EXTERNA
    # ========================================================

    dados_api = enviar_para_api(
        imagem_bytes,
        nome_arquivo,
    )

    # ========================================================
    # EXTRAIR RESULTADO
    # ========================================================

    resultado_api = extrair_resultado_api(
        dados_api
    )

    # ========================================================
    # NORMALIZAR RESULTADO
    # ========================================================

    resultado_final = normalizar_resultado_api(
        resultado_api,
        produto=produto,
    )

    return resultado_final
