from pathlib import Path
import json
import re

import numpy as np
import tensorflow as tf
from PIL import Image, UnidentifiedImageError
from django.conf import settings


# ============================================================
# CAMINHOS
# ============================================================

MODEL_PATH = (
    Path(settings.BASE_DIR)
    / "diagnostico"
    / "ai"
    / "model.keras"
)

CLASS_NAMES_PATH = (
    Path(settings.BASE_DIR)
    / "diagnostico"
    / "ai"
    / "class_names.json"
)


# ============================================================
# CONFIGURAÇÕES DO MODELO
# ============================================================

# Deve ser igual ao tamanho usado durante o treinamento.
IMAGE_SIZE = (224, 224)

# Tamanho máximo da imagem cadastrada/enviada.
MAX_IMAGE_SIZE = 10 * 1024 * 1024

# Confiança mínima considerada aceitável.
MIN_CONFIDENCE = 40.0


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
        "cultura": "milho",
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
        "cultura": "milho",
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
        "cultura": "milho",
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
        "cultura": "feijao",
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
        "cultura": "feijao",
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
        "cultura": "mandioca",
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
        "cultura": "mandioca",
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
        "cultura": "arroz",
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
        "cultura": "arroz",
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
        "cultura": "tomate",
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
        "cultura": "tomate",
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

        Milho       -> milho
        Milho       -> milho
        Feijão      -> feijao
        Mancha Foliar -> mancha_foliar
    """

    if valor is None:
        return ""

    texto = str(valor).strip().lower()

    substituicoes = {
        "á": "a",
        "à": "a",
        "ã": "a",
        "â": "a",
        "ä": "a",

        "é": "e",
        "è": "e",
        "ê": "e",
        "ë": "e",

        "í": "i",
        "ì": "i",
        "î": "i",
        "ï": "i",

        "ó": "o",
        "ò": "o",
        "ô": "o",
        "õ": "o",
        "ö": "o",

        "ú": "u",
        "ù": "u",
        "û": "u",
        "ü": "u",

        "ç": "c",
    }

    for original, novo in substituicoes.items():
        texto = texto.replace(original, novo)

    texto = re.sub(r"[^a-z0-9]+", "_", texto)

    return texto.strip("_")


# ============================================================
# IDENTIFICAR CULTURA
# ============================================================

def identificar_cultura_da_classe(classe):
    """
    Obtém a cultura a partir do nome da classe.

    Exemplos:

        milho_ferrugem
        -> milho

        feijao_antracnose
        -> feijao
    """

    classe = normalizar_texto(classe)

    if classe in RESULTADOS:
        return RESULTADOS[classe]["cultura"]

    if "_" in classe:
        return classe.split("_")[0]

    return ""


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
    # VERIFICAR EXISTÊNCIA
    # --------------------------------------------------------

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            "Modelo de IA não encontrado.\n\n"
            f"Caminho esperado:\n{MODEL_PATH}\n\n"
            "Execute o train_model.py para gerar "
            "o model.keras."
        )

    # --------------------------------------------------------
    # VERIFICAR TAMANHO
    # --------------------------------------------------------

    if MODEL_PATH.stat().st_size == 0:
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

    if not isinstance(data, list):
        raise ValueError(
            "O class_names.json deve conter uma lista."
        )

    if not data:
        raise ValueError(
            "O class_names.json está vazio."
        )

    _class_names = [
        normalizar_texto(classe)
        for classe in data
        if str(classe).strip()
    ]

    if len(_class_names) != 11:
        raise ValueError(
            "O sistema AgroIA Moxico espera exatamente "
            "11 classes.\n\n"
            f"Classes encontradas: {len(_class_names)}"
        )

    return _class_names


# ============================================================
# PREPARAR IMAGEM
# ============================================================

def prepare_image(image_file):
    """
    Prepara a imagem cadastrada no produto para o modelo.

    A imagem pode ser:

    - arquivo enviado pelo formulário;
    - FieldFile do Django;
    - imagem cadastrada em ProdutoAgricola.

    Não é necessário copiar a imagem para o dataset.
    """

    if image_file is None:
        raise ValueError(
            "Nenhuma imagem foi fornecida para análise."
        )

    # ========================================================
    # OBTER TAMANHO
    # ========================================================

    try:
        file_size = getattr(
            image_file,
            "size",
            0,
        )

        if file_size and file_size > MAX_IMAGE_SIZE:
            raise ValueError(
                "A imagem não pode ultrapassar 10 MB."
            )

    except Exception:
        pass

    # ========================================================
    # ABRIR IMAGEM
    # ========================================================

    try:

        # FieldFile do Django
        if hasattr(image_file, "open"):

            image_file.open("rb")

            try:
                image = Image.open(image_file)
                image.load()
            finally:
                image_file.close()

        else:

            # UploadedFile ou arquivo normal
            if hasattr(image_file, "seek"):
                image_file.seek(0)

            image = Image.open(image_file)

            image.load()

    except UnidentifiedImageError as exc:

        raise ValueError(
            "O arquivo associado ao produto não é "
            "uma imagem válida."
        ) from exc

    except Exception as exc:

        raise ValueError(
            "Não foi possível abrir a imagem cadastrada "
            "no produto."
        ) from exc

    # ========================================================
    # CONVERTER PARA RGB
    # ========================================================

    try:
        image = image.convert("RGB")

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

    classe = normalizar_texto(classe)

    informacao = RESULTADOS.get(classe)

    if informacao:
        return informacao.copy()

    cultura = identificar_cultura_da_classe(classe)

    return {
        "cultura": cultura,

        "resultado": "indeterminado",

        "doenca": (
            classe.replace("_", " ").title()
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
# VALIDAR PRODUTO
# ============================================================

def validar_produto_com_classe(
    produto,
    classe,
):
    """
    Verifica se a cultura detectada pela IA é compatível
    com o produto cadastrado.

    IMPORTANTE:

    A imagem analisada continua sendo exatamente a imagem
    cadastrada no produto.

    Esta função apenas verifica a compatibilidade entre:

        Produto cadastrado
        +
        Classe identificada pela IA
    """

    if produto is None:
        return {
            "corresponde": True,
            "mensagem": "",
        }

    cultura_detectada = identificar_cultura_da_classe(
        classe
    )

    if not cultura_detectada:
        return {
            "corresponde": True,
            "mensagem": "",
        }

    nome_produto = normalizar_texto(
        getattr(
            produto,
            "nome",
            "",
        )
    )

    if not nome_produto:
        return {
            "corresponde": True,
            "mensagem": "",
        }

    # ========================================================
    # VERIFICAR COMPATIBILIDADE
    # ========================================================

    corresponde = (
        cultura_detectada in nome_produto
        or nome_produto in cultura_detectada
    )

    if corresponde:
        return {
            "corresponde": True,
            "mensagem": "",
        }

    return {
        "corresponde": False,

        "mensagem": (
            f"A inteligência artificial identificou "
            f"uma cultura compatível com "
            f"'{cultura_detectada}', enquanto o produto "
            f"cadastrado é '{produto.nome}'. "
            "Verifique se a imagem cadastrada pertence "
            "ao produto selecionado."
        ),
    }


# ============================================================
# ANALISAR IMAGEM
# ============================================================

def analisar_imagem(
    image_file,
    produto=None,
):
    """
    Analisa a imagem através do modelo de IA.

    A imagem deve ser a imagem cadastrada no produto.

    Exemplo de utilização:

        resultado = analisar_imagem(
            produto.imagem,
            produto=produto
        )

    Retorna:

        {
            "classe": "...",
            "cultura": "...",
            "confianca": 95.20,
            "resultado": "...",
            "doenca": "...",
            "descricao": "...",
            "recomendacoes": "...",
            "produto_compativel": True,
            "mensagem_compatibilidade": "...",
            "baixa_confianca": False
        }
    """

    # ========================================================
    # VALIDAR IMAGEM DO PRODUTO
    # ========================================================

    if produto is not None:

        if not getattr(
            produto,
            "imagem",
            None,
        ):

            raise ValueError(
                "O produto selecionado não possui "
                "uma imagem cadastrada."
            )

        # ----------------------------------------------------
        # USAR SEMPRE A IMAGEM CADASTRADA
        # ----------------------------------------------------

        image_file = produto.imagem

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
    # CONVERTER PARA NUMPY
    # ========================================================

    predictions = np.asarray(
        predictions,
        dtype=np.float32,
    )

    # ========================================================
    # NORMALIZAR SAÍDA
    # ========================================================

    if predictions.ndim == 1:

        probabilities = predictions

    elif predictions.ndim == 2:

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
    # VALIDAR QUANTIDADE DE CLASSES
    # ========================================================

    if len(probabilities) != len(class_names):

        raise ValueError(
            "A quantidade de classes do modelo não "
            "corresponde ao class_names.json.\n\n"
            f"Saída do modelo: {len(probabilities)}\n"
            f"Classes configuradas: {len(class_names)}"
        )

    # ========================================================
    # LIMPAR VALORES INVÁLIDOS
    # ========================================================

    if not np.all(
        np.isfinite(probabilities)
    ):

        raise RuntimeError(
            "O modelo retornou probabilidades inválidas."
        )

    # ========================================================
    # VERIFICAR SE JÁ SÃO PROBABILIDADES
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
    # MELHOR CLASSE
    # ========================================================

    index = int(
        np.argmax(probabilities)
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

    cultura = informacoes.get(
        "cultura",
        identificar_cultura_da_classe(
            classe
        ),
    )

    # ========================================================
    # COMPATIBILIDADE COM PRODUTO
    # ========================================================

    compatibilidade = (
        validar_produto_com_classe(
            produto,
            classe,
        )
    )

    # ========================================================
    # BAIXA CONFIANÇA
    # ========================================================

    baixa_confianca = (
        confidence < MIN_CONFIDENCE
    )

    mensagem = compatibilidade.get(
        "mensagem",
        "",
    )

    if baixa_confianca:

        mensagem_baixa_confianca = (
            "A confiança da análise é relativamente "
            "baixa. Recomenda-se verificar a qualidade "
            "da imagem e procurar confirmação técnica."
        )

        if mensagem:

            mensagem += (
                " "
                + mensagem_baixa_confianca
            )

        else:

            mensagem = (
                mensagem_baixa_confianca
            )

    # ========================================================
    # RESULTADO FINAL
    # ========================================================

    return {

        # Classe técnica da IA
        "classe": classe,

        # Cultura
        "cultura": cultura,

        # Confiança
        "confianca": round(
            confidence,
            2,
        ),

        # Resultado
        "resultado": informacoes.get(
            "resultado",
            "indeterminado",
        ),

        # Doença
        "doenca": informacoes.get(
            "doenca",
            "Resultado não identificado",
        ),

        # Descrição
        "descricao": informacoes.get(
            "descricao",
            "",
        ),

        # Recomendações
        "recomendacoes": informacoes.get(
            "recomendacoes",
            "",
        ),

        # Compatibilidade
        "produto_compativel": (
            compatibilidade.get(
                "corresponde",
                True,
            )
        ),

        # Mensagem
        "mensagem_compatibilidade": mensagem,

        # Baixa confiança
        "baixa_confianca": baixa_confianca,
    }


# ============================================================
# FUNÇÃO DE TESTE DO MODELO
# ============================================================

def testar_modelo():
    """
    Verifica se o model.keras e o class_names.json
    estão corretamente configurados.

    Pode ser chamada no shell do Django:

        from diagnostico.ai_service import testar_modelo
        testar_modelo()
    """

    model = load_model()
    class_names = load_class_names()

    try:
        input_shape = model.input_shape
    except Exception:
        input_shape = "Não disponível"

    try:
        output_shape = model.output_shape
    except Exception:
        output_shape = "Não disponível"

    resultado = {
        "modelo": str(MODEL_PATH),
        "modelo_existe": MODEL_PATH.exists(),
        "modelo_tamanho": (
            MODEL_PATH.stat().st_size
            if MODEL_PATH.exists()
            else 0
        ),
        "input_shape": input_shape,
        "output_shape": output_shape,
        "quantidade_classes": len(
            class_names
        ),
        "classes": class_names,
    }

    return resultado


# ============================================================
# RECARREGAR MODELO
# ============================================================

def recarregar_modelo():
    """
    Limpa o cache e força o carregamento do modelo
    novamente.

    Útil depois de substituir o model.keras durante
    o desenvolvimento.
    """

    global _model
    global _class_names

    _model = None
    _class_names = None

    return load_model()
