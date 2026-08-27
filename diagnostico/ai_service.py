from pathlib import Path
import json
import re
import unicodedata

import numpy as np
import tensorflow as tf
from PIL import Image, UnidentifiedImageError
from django.conf import settings


# ============================================================
# AGROIA MOXICO
# SERVIÇO DE INTELIGÊNCIA ARTIFICIAL
# DIAGNÓSTICO BASEADO NO PRODUTO CADASTRADO
# ============================================================


# ============================================================
# CAMINHOS
# ============================================================

BASE_DIR = Path(settings.BASE_DIR)

MODEL_PATH = (
    BASE_DIR
    / "diagnostico"
    / "ai"
    / "model.keras"
)

CLASS_NAMES_PATH = (
    BASE_DIR
    / "diagnostico"
    / "ai"
    / "class_names.json"
)


# ============================================================
# CONFIGURAÇÕES DO MODELO
# ============================================================

# Deve corresponder ao tamanho utilizado durante o treinamento.
IMAGE_SIZE = (224, 224)

# Tamanho máximo permitido para a imagem cadastrada no produto.
MAX_IMAGE_SIZE = 10 * 1024 * 1024

# Confiança mínima considerada aceitável.
MIN_CONFIDENCE = 40.0

# Quantidade esperada de classes.
EXPECTED_CLASSES = 11


# ============================================================
# CACHE
# ============================================================

_model = None
_class_names = None


# ============================================================
# INFORMAÇÕES DAS CLASSES
# ============================================================

RESULTADOS = {

    # ========================================================
    # MILHO
    # ========================================================

    "milho_saudavel": {
        "produto": "milho",
        "resultado": "saudavel",
        "doenca": "Milho saudável",
        "descricao": (
            "A imagem apresenta características compatíveis "
            "com uma planta de milho saudável."
        ),
        "recomendacoes": (
            "Continue acompanhando regularmente a cultura, "
            "mantenha uma boa nutrição, controle de plantas "
            "daninhas e realize inspeções periódicas."
        ),
    },

    "milho_ferrugem": {
        "produto": "milho",
        "resultado": "fungo",
        "doenca": "Possível ferrugem do milho",
        "descricao": (
            "A imagem apresenta características visuais "
            "compatíveis com sintomas associados à ferrugem "
            "do milho."
        ),
        "recomendacoes": (
            "Observe a evolução dos sintomas e a presença "
            "de lesões em outras plantas. Procure orientação "
            "de um técnico agrícola para confirmação e "
            "tratamento adequado."
        ),
    },

    "milho_mancha_foliar": {
        "produto": "milho",
        "resultado": "fungo",
        "doenca": "Possível mancha foliar do milho",
        "descricao": (
            "Foram identificadas características visuais "
            "compatíveis com sintomas de mancha foliar."
        ),
        "recomendacoes": (
            "Observe outras plantas da parcela, retire "
            "materiais vegetais muito afetados quando "
            "apropriado e procure orientação técnica."
        ),
    },


    # ========================================================
    # FEIJÃO
    # ========================================================

    "feijao_saudavel": {
        "produto": "feijao",
        "resultado": "saudavel",
        "doenca": "Feijão saudável",
        "descricao": (
            "A imagem apresenta características compatíveis "
            "com uma planta de feijão saudável."
        ),
        "recomendacoes": (
            "Continue monitorando a cultura, mantenha boas "
            "práticas de manejo e faça inspeções regulares."
        ),
    },

    "feijao_antracnose": {
        "produto": "feijao",
        "resultado": "fungo",
        "doenca": "Possível antracnose do feijão",
        "descricao": (
            "A imagem apresenta características visuais "
            "compatíveis com sintomas associados à antracnose."
        ),
        "recomendacoes": (
            "Monitore a evolução dos sintomas e procure "
            "orientação de um técnico agrícola para confirmar "
            "o diagnóstico e definir as medidas de controle."
        ),
    },


    # ========================================================
    # MANDIOCA
    # ========================================================

    "mandioca_saudavel": {
        "produto": "mandioca",
        "resultado": "saudavel",
        "doenca": "Mandioca saudável",
        "descricao": (
            "A imagem apresenta características compatíveis "
            "com uma planta de mandioca saudável."
        ),
        "recomendacoes": (
            "Continue realizando inspeções regulares e "
            "mantenha boas práticas de manejo da cultura."
        ),
    },

    "mandioca_mosaico": {
        "produto": "mandioca",
        "resultado": "doenca",
        "doenca": "Possível mosaico da mandioca",
        "descricao": (
            "A imagem apresenta características visuais "
            "compatíveis com sintomas de mosaico da mandioca."
        ),
        "recomendacoes": (
            "Observe a presença de sintomas semelhantes em "
            "outras plantas e procure orientação técnica para "
            "confirmar o diagnóstico."
        ),
    },


    # ========================================================
    # ARROZ
    # ========================================================

    "arroz_saudavel": {
        "produto": "arroz",
        "resultado": "saudavel",
        "doenca": "Arroz saudável",
        "descricao": (
            "A imagem apresenta características compatíveis "
            "com uma planta de arroz saudável."
        ),
        "recomendacoes": (
            "Continue monitorando a cultura e mantenha boas "
            "práticas de manejo agrícola."
        ),
    },

    "arroz_mancha_foliar": {
        "produto": "arroz",
        "resultado": "fungo",
        "doenca": "Possível mancha foliar do arroz",
        "descricao": (
            "A imagem apresenta características visuais "
            "compatíveis com sintomas de mancha foliar."
        ),
        "recomendacoes": (
            "Monitore outras plantas da parcela e procure "
            "orientação técnica para confirmar a causa "
            "dos sintomas."
        ),
    },


    # ========================================================
    # TOMATE
    # ========================================================

    "tomate_saudavel": {
        "produto": "tomate",
        "resultado": "saudavel",
        "doenca": "Tomate saudável",
        "descricao": (
            "A imagem apresenta características compatíveis "
            "com uma planta de tomate saudável."
        ),
        "recomendacoes": (
            "Continue acompanhando a cultura e observe "
            "regularmente folhas, caules e frutos."
        ),
    },

    "tomate_requeima": {
        "produto": "tomate",
        "resultado": "fungo",
        "doenca": "Possível requeima do tomate",
        "descricao": (
            "A imagem apresenta características visuais "
            "compatíveis com sintomas associados à requeima."
        ),
        "recomendacoes": (
            "Observe a evolução dos sintomas e procure "
            "orientação técnica para confirmação e definição "
            "das medidas adequadas de manejo."
        ),
    },
}


# ============================================================
# NORMALIZAÇÃO DE TEXTO
# ============================================================

def normalizar_texto(valor):
    """
    Normaliza texto para comparação.

    Exemplos:

        Feijão       -> feijao
        Milho        -> milho
        Mancha Foliar -> mancha_foliar
    """

    if valor is None:
        return ""

    texto = str(valor).strip().lower()

    # Remove acentos de forma segura.
    texto = unicodedata.normalize(
        "NFKD",
        texto,
    )

    texto = "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(caractere)
    )

    texto = re.sub(
        r"[^a-z0-9]+",
        "_",
        texto,
    )

    return texto.strip("_")


# ============================================================
# IDENTIFICAR PRODUTO DA CLASSE
# ============================================================

def identificar_produto_da_classe(classe):
    """
    Identifica o produto correspondente à classe retornada
    pelo modelo.

    Exemplos:

        milho_ferrugem
        -> milho

        feijao_antracnose
        -> feijao

        mandioca_mosaico
        -> mandioca
    """

    classe = normalizar_texto(classe)

    if not classe:
        return ""

    if classe in RESULTADOS:
        return RESULTADOS[classe].get(
            "produto",
            "",
        )

    if "_" in classe:
        return classe.split("_")[0]

    return ""


# ============================================================
# ALIAS PARA COMPATIBILIDADE
# ============================================================

def identificar_cultura_da_classe(classe):
    """
    Mantém compatibilidade com código antigo.

    O sistema atual trabalha com produtos, mas esta função
    continua disponível para evitar quebra de código legado.
    """

    return identificar_produto_da_classe(classe)


# ============================================================
# CARREGAR MODELO
# ============================================================

def load_model():
    """
    Carrega o modelo TensorFlow/Keras apenas uma vez.
    """

    global _model

    if _model is not None:
        return _model

    # --------------------------------------------------------
    # EXISTÊNCIA
    # --------------------------------------------------------

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            "Modelo de IA não encontrado.\n\n"
            f"Caminho esperado:\n{MODEL_PATH}\n\n"
            "Execute o train_model.py para gerar o "
            "arquivo model.keras."
        )

    # --------------------------------------------------------
    # TAMANHO
    # --------------------------------------------------------

    model_size = MODEL_PATH.stat().st_size

    if model_size <= 0:
        raise RuntimeError(
            "O arquivo model.keras está vazio.\n\n"
            "Execute o train_model.py para treinar "
            "o modelo antes de realizar diagnósticos."
        )

    # --------------------------------------------------------
    # CARREGAR
    # --------------------------------------------------------

    try:
        _model = tf.keras.models.load_model(
            MODEL_PATH,
            compile=False,
        )

    except Exception as exc:

        raise RuntimeError(
            "Não foi possível carregar o modelo "
            "TensorFlow/Keras.\n\n"
            "Verifique se o arquivo model.keras foi "
            "gerado corretamente pelo train_model.py."
        ) from exc

    return _model


# ============================================================
# CARREGAR CLASSES
# ============================================================

def load_class_names():
    """
    Carrega e valida o class_names.json.
    """

    global _class_names

    if _class_names is not None:
        return _class_names

    if not CLASS_NAMES_PATH.exists():
        raise FileNotFoundError(
            "Arquivo class_names.json não encontrado.\n\n"
            f"Caminho esperado:\n{CLASS_NAMES_PATH}"
        )

    try:

        with open(
            CLASS_NAMES_PATH,
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

    except json.JSONDecodeError as exc:

        raise ValueError(
            "O arquivo class_names.json não contém "
            "um JSON válido."
        ) from exc

    except OSError as exc:

        raise RuntimeError(
            "Não foi possível ler o arquivo "
            "class_names.json."
        ) from exc

    if not isinstance(data, list):
        raise ValueError(
            "O class_names.json deve conter uma lista."
        )

    if not data:
        raise ValueError(
            "O class_names.json está vazio."
        )

    classes_normalizadas = []

    for classe in data:

        classe_normalizada = normalizar_texto(
            classe
        )

        if classe_normalizada:
            classes_normalizadas.append(
                classe_normalizada
            )

    if not classes_normalizadas:
        raise ValueError(
            "Nenhuma classe válida foi encontrada "
            "no class_names.json."
        )

    if len(classes_normalizadas) != EXPECTED_CLASSES:
        raise ValueError(
            "O sistema AgroIA Moxico espera exatamente "
            f"{EXPECTED_CLASSES} classes.\n\n"
            f"Classes encontradas: "
            f"{len(classes_normalizadas)}"
        )

    _class_names = classes_normalizadas

    return _class_names


# ============================================================
# PREPARAR IMAGEM
# ============================================================

def prepare_image(image_file):
    """
    Prepara a imagem cadastrada no ProdutoAgricola.

    Aceita:

    - FieldFile do Django;
    - UploadedFile;
    - arquivo aberto;
    - objeto compatível com PIL.

    A imagem não é alterada no armazenamento.
    """

    if image_file is None:
        raise ValueError(
            "Nenhuma imagem foi fornecida para análise."
        )

    # ========================================================
    # TAMANHO
    # ========================================================

    try:

        file_size = getattr(
            image_file,
            "size",
            0,
        )

        if (
            file_size
            and file_size > MAX_IMAGE_SIZE
        ):
            raise ValueError(
                "A imagem não pode ultrapassar 10 MB."
            )

    except ValueError:
        raise

    except Exception:
        pass

    # ========================================================
    # ABRIR IMAGEM
    # ========================================================

    image = None

    try:

        # ----------------------------------------------------
        # FieldFile do Django
        # ----------------------------------------------------

        if hasattr(
            image_file,
            "open",
        ):

            image_file.open("rb")

            try:

                image = Image.open(
                    image_file
                )

                image.load()

            finally:

                try:
                    image_file.close()
                except Exception:
                    pass

        # ----------------------------------------------------
        # UploadedFile / arquivo
        # ----------------------------------------------------

        else:

            if hasattr(
                image_file,
                "seek",
            ):
                image_file.seek(0)

            image = Image.open(
                image_file
            )

            image.load()

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

    # ========================================================
    # RGB
    # ========================================================

    try:

        image = image.convert(
            "RGB"
        )

    except Exception as exc:

        raise ValueError(
            "Não foi possível converter a imagem "
            "para o formato RGB."
        ) from exc

    # ========================================================
    # REDIMENSIONAR
    # ========================================================

    image = image.resize(
        IMAGE_SIZE,
        Image.Resampling.LANCZOS,
    )

    # ========================================================
    # NUMPY
    # ========================================================

    image_array = np.asarray(
        image,
        dtype=np.float32,
    )

    # ========================================================
    # NORMALIZAÇÃO
    # ========================================================

    image_array /= 255.0

    # ========================================================
    # BATCH
    # ========================================================

    image_array = np.expand_dims(
        image_array,
        axis=0,
    )

    return image_array


# ============================================================
# OBTER INFORMAÇÕES DA CLASSE
# ============================================================

def obter_informacoes_classe(classe):
    """
    Retorna informações agrícolas da classe detectada.
    """

    classe = normalizar_texto(
        classe
    )

    informacao = RESULTADOS.get(
        classe
    )

    if informacao:
        return informacao.copy()

    produto = identificar_produto_da_classe(
        classe
    )

    return {
        "produto": produto,
        "resultado": "indeterminado",
        "doenca": (
            classe.replace(
                "_",
                " ",
            ).title()
            if classe
            else "Resultado não identificado"
        ),
        "descricao": (
            "O modelo identificou uma classe para a qual "
            "ainda não existe uma descrição detalhada "
            "configurada no sistema."
        ),
        "recomendacoes": (
            "Procure orientação técnica para confirmar "
            "o resultado antes de tomar qualquer decisão."
        ),
    }


# ============================================================
# OBTER NOME NORMALIZADO DO PRODUTO
# ============================================================

def obter_nome_produto(produto):
    """
    Obtém o nome normalizado do ProdutoAgricola.

    Exemplo:

        ProdutoAgricola(nome="Milho")
        -> milho
    """

    if produto is None:
        return ""

    nome = getattr(
        produto,
        "nome",
        "",
    )

    return normalizar_texto(
        nome
    )


# ============================================================
# VALIDAR PRODUTO COM CLASSE
# ============================================================

def validar_produto_com_classe(
    produto,
    classe,
):
    """
    Verifica se o produto cadastrado corresponde ao produto
    identificado pela IA.

    Produto cadastrado:
        Milho

    Classe da IA:
        milho_ferrugem

    Resultado:
        corresponde = True
    """

    if produto is None:
        return {
            "corresponde": True,
            "mensagem": "",
        }

    produto_detectado = identificar_produto_da_classe(
        classe
    )

    if not produto_detectado:
        return {
            "corresponde": True,
            "mensagem": "",
        }

    produto_cadastrado = obter_nome_produto(
        produto
    )

    if not produto_cadastrado:
        return {
            "corresponde": True,
            "mensagem": "",
        }

    # ========================================================
    # COMPARAÇÃO
    # ========================================================

    corresponde = (
        produto_detectado in produto_cadastrado
        or produto_cadastrado in produto_detectado
    )

    if corresponde:
        return {
            "corresponde": True,
            "mensagem": "",
        }

    # ========================================================
    # INCOMPATIBILIDADE
    # ========================================================

    nome_original = getattr(
        produto,
        "nome",
        "produto",
    )

    return {
        "corresponde": False,
        "mensagem": (
            "A inteligência artificial identificou "
            f"uma classe compatível com '{produto_detectado}', "
            f"enquanto o produto cadastrado é "
            f"'{nome_original}'. "
            "Verifique se a imagem cadastrada pertence "
            "ao produto selecionado."
        ),
    }


# ============================================================
# ANALISAR IMAGEM
# ============================================================

def analisar_imagem(
    image_file=None,
    produto=None,
):
    """
    Analisa a imagem através do modelo de IA.

    O fluxo principal do AgroIA Moxico é:

        ProdutoAgricola
              ↓
        produto.imagem
              ↓
        prepare_image()
              ↓
        model.keras
              ↓
        classe
              ↓
        informações agrícolas
              ↓
        validação do produto
              ↓
        resultado final

    Se 'produto' for fornecido, a função ignora qualquer
    outra imagem e utiliza exclusivamente:

        produto.imagem
    """

    # ========================================================
    # VALIDAR PRODUTO
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

        # ----------------------------------------------------
        # IMPORTANTE:
        # sempre utilizar a imagem do produto
        # ----------------------------------------------------

        image_file = produto_imagem

    # ========================================================
    # VALIDAR IMAGEM
    # ========================================================

    if image_file is None:
        raise ValueError(
            "Nenhuma imagem disponível para realizar "
            "o diagnóstico."
        )

    # ========================================================
    # CARREGAR MODELO
    # ========================================================

    model = load_model()

    # ========================================================
    # CARREGAR CLASSES
    # ========================================================

    class_names = load_class_names()

    # ========================================================
    # PREPARAR IMAGEM
    # ========================================================

    image = prepare_image(
        image_file
    )

    # ========================================================
    # PREDIÇÃO
    # ========================================================

    try:

        predictions = model.predict(
            image,
            verbose=0,
        )

    except Exception as exc:

        raise RuntimeError(
            "Ocorreu um erro durante a análise da "
            "imagem pelo modelo de IA."
        ) from exc

    if predictions is None:
        raise RuntimeError(
            "O modelo de IA não retornou resultados."
        )

    # ========================================================
    # NUMPY
    # ========================================================

    try:

        predictions = np.asarray(
            predictions,
            dtype=np.float32,
        )

    except Exception as exc:

        raise RuntimeError(
            "Não foi possível interpretar a saída "
            "do modelo de IA."
        ) from exc

    # ========================================================
    # NORMALIZAR SAÍDA
    # ========================================================

    if predictions.ndim == 1:

        probabilities = predictions

    elif predictions.ndim == 2:

        if predictions.shape[0] < 1:
            raise RuntimeError(
                "O modelo não retornou nenhuma previsão."
            )

        probabilities = predictions[0]

    else:

        raise RuntimeError(
            "O modelo retornou uma saída inválida."
        )

    probabilities = np.asarray(
        probabilities,
        dtype=np.float32,
    ).reshape(-1)

    # ========================================================
    # QUANTIDADE DE CLASSES
    # ========================================================

    if len(probabilities) != len(class_names):

        raise ValueError(
            "A quantidade de classes do modelo não "
            "corresponde ao class_names.json.\n\n"
            f"Saída do modelo: "
            f"{len(probabilities)}\n"
            f"Classes configuradas: "
            f"{len(class_names)}"
        )

    # ========================================================
    # VALORES FINITOS
    # ========================================================

    if not np.all(
        np.isfinite(probabilities)
    ):

        raise RuntimeError(
            "O modelo retornou probabilidades inválidas."
        )

    # ========================================================
    # DETECTAR TIPO DA SAÍDA
    # ========================================================

    probability_sum = float(
        np.sum(probabilities)
    )

    probabilities_are_valid = (
        np.all(probabilities >= 0)
        and
        np.all(probabilities <= 1)
        and
        np.isclose(
            probability_sum,
            1.0,
            atol=0.01,
        )
    )

    # ========================================================
    # SOFTMAX
    # ========================================================

    if not probabilities_are_valid:

        probabilities = (
            tf.nn.softmax(
                probabilities
            ).numpy()
        )

    # ========================================================
    # SEGURANÇA
    # ========================================================

    if not np.all(
        np.isfinite(probabilities)
    ):

        raise RuntimeError(
            "Não foi possível obter probabilidades "
            "válidas do modelo."
        )

    # ========================================================
    # MELHOR CLASSE
    # ========================================================

    index = int(
        np.argmax(
            probabilities
        )
    )

    confidence = float(
        probabilities[index] * 100.0
    )

    confidence = max(
        0.0,
        min(
            100.0,
            confidence,
        ),
    )

    classe = normalizar_texto(
        class_names[index]
    )

    # ========================================================
    # INFORMAÇÕES AGRÍCOLAS
    # ========================================================

    informacoes = obter_informacoes_classe(
        classe
    )

    produto_detectado = informacoes.get(
        "produto",
        identificar_produto_da_classe(
            classe
        ),
    )

    # ========================================================
    # COMPATIBILIDADE COM PRODUTO
    # ========================================================

    compatibilidade = validar_produto_com_classe(
        produto,
        classe,
    )

    produto_compativel = compatibilidade.get(
        "corresponde",
        True,
    )

    mensagem = compatibilidade.get(
        "mensagem",
        "",
    )

    # ========================================================
    # BAIXA CONFIANÇA
    # ========================================================

    baixa_confianca = (
        confidence < MIN_CONFIDENCE
    )

    if baixa_confianca:

        mensagem_baixa_confianca = (
            "A confiança da análise é relativamente "
            "baixa. Recomenda-se verificar a qualidade "
            "da imagem e procurar confirmação técnica."
        )

        if mensagem:

            mensagem = (
                f"{mensagem} "
                f"{mensagem_baixa_confianca}"
            )

        else:

            mensagem = (
                mensagem_baixa_confianca
            )

    # ========================================================
    # RESULTADO FINAL
    # ========================================================

    return {

        # ----------------------------------------------------
        # IDENTIFICAÇÃO TÉCNICA
        # ----------------------------------------------------

        "classe": classe,

        # ----------------------------------------------------
        # PRODUTO IDENTIFICADO PELA IA
        # ----------------------------------------------------

        "produto": produto_detectado,

        # ----------------------------------------------------
        # COMPATIBILIDADE
        # ----------------------------------------------------

        "produto_compativel": (
            produto_compativel
        ),

        "mensagem_compatibilidade": (
            mensagem
        ),

        # ----------------------------------------------------
        # CONFIANÇA
        # ----------------------------------------------------

        "confianca": round(
            confidence,
            2,
        ),

        "baixa_confianca": (
            baixa_confianca
        ),

        # ----------------------------------------------------
        # RESULTADO
        # ----------------------------------------------------

        "resultado": informacoes.get(
            "resultado",
            "indeterminado",
        ),

        # ----------------------------------------------------
        # DOENÇA
        # ----------------------------------------------------

        "doenca": informacoes.get(
            "doenca",
            "Resultado não identificado",
        ),

        # ----------------------------------------------------
        # DESCRIÇÃO
        # ----------------------------------------------------

        "descricao": informacoes.get(
            "descricao",
            "",
        ),

        # ----------------------------------------------------
        # RECOMENDAÇÕES
        # ----------------------------------------------------

        "recomendacoes": informacoes.get(
            "recomendacoes",
            "",
        ),
    }


# ============================================================
# TESTAR MODELO
# ============================================================

def testar_modelo():
    """
    Verifica se o model.keras e o class_names.json estão
    corretamente configurados.

    No shell do Django:

        from diagnostico.ai_service import testar_modelo
        testar_modelo()
    """

    model = load_model()

    class_names = load_class_names()

    # --------------------------------------------------------
    # INPUT
    # --------------------------------------------------------

    try:

        input_shape = model.input_shape

    except Exception:

        input_shape = "Não disponível"

    # --------------------------------------------------------
    # OUTPUT
    # --------------------------------------------------------

    try:

        output_shape = model.output_shape

    except Exception:

        output_shape = "Não disponível"

    # --------------------------------------------------------
    # TAMANHO
    # --------------------------------------------------------

    model_size = (
        MODEL_PATH.stat().st_size
        if MODEL_PATH.exists()
        else 0
    )

    return {

        "modelo": str(
            MODEL_PATH
        ),

        "modelo_existe": (
            MODEL_PATH.exists()
        ),

        "modelo_tamanho": (
            model_size
        ),

        "input_shape": (
            input_shape
        ),

        "output_shape": (
            output_shape
        ),

        "quantidade_classes": (
            len(class_names)
        ),

        "classes": (
            class_names
        ),
    }


# ============================================================
# RECARREGAR MODELO
# ============================================================

def recarregar_modelo():
    """
    Limpa o cache do modelo e das classes e força novo
    carregamento.
    """

    global _model
    global _class_names

    _model = None
    _class_names = None

    return load_model()
