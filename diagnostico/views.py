from pathlib import Path
import mimetypes

import requests

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

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

MAX_IMAGE_SIZE = 10 * 1024 * 1024

FORMATOS_PERMITIDOS = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def obter_contadores():
    """
    Obtém contadores gerais utilizados na interface.
    """

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
    """
    Obtém estatísticas dos diagnósticos do utilizador autenticado.
    """

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

    if media_confianca is None:
        media_confianca = 0

    return {
        "total": total,
        "concluidos": concluidos,
        "erros": erros,
        "processando": processando,
        "pendentes": pendentes,
        "problemas": problemas,
        "saudaveis": saudaveis,
        "media_confianca": float(media_confianca),
    }


def obter_estatisticas_produto(request, produto):
    """
    Obtém estatísticas do produto para o utilizador atual.
    """

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

    ultimo_diagnostico = diagnosticos.order_by(
        "-data_criacao"
    ).first()

    primeiro_diagnostico = diagnosticos.order_by(
        "data_criacao"
    ).first()

    return {
        "total": total,
        "concluidos": concluidos,
        "erros": erros,
        "problemas": problemas,
        "saudaveis": saudaveis,
        "media_confianca": float(media_confianca or 0),
        "ultimo_diagnostico": ultimo_diagnostico,
        "primeiro_diagnostico": primeiro_diagnostico,
    }


def obter_ultimos_diagnosticos(
    request,
    produto=None,
    limite=5,
):
    """
    Obtém os últimos diagnósticos do utilizador.
    """

    queryset = (
        Diagnostico.objects
        .filter(usuario=request.user)
        .select_related("produto", "usuario")
        .order_by("-data_criacao")
    )

    if produto is not None:
        queryset = queryset.filter(
            produto=produto
        )

    return queryset[:limite]


def obter_diagnosticos_produto(request, produto):
    """
    Obtém todos os diagnósticos do utilizador para determinado produto.
    """

    return (
        Diagnostico.objects
        .filter(
            usuario=request.user,
            produto=produto,
        )
        .select_related("produto", "usuario")
        .order_by("-data_criacao")
    )


def obter_produtos_ativos(request=None):
    """
    Retorna os produtos ativos.
    """

    return (
        ProdutoAgricola.objects
        .filter(ativo=True)
        .prefetch_related("categorias")
        .order_by("nome")
    )


def obter_produto(produto_id):
    """
    Obtém um produto ativo ou lança 404.
    """

    return get_object_or_404(
        ProdutoAgricola.objects
        .filter(ativo=True)
        .prefetch_related("categorias"),
        pk=produto_id,
    )


def obter_imagem_produto(produto):
    """
    Lê a imagem cadastrada no produto.
    """

    if not produto.imagem:
        raise ValueError(
            "Este produto não possui uma imagem cadastrada."
        )

    try:
        produto.imagem.open("rb")

        try:
            return produto.imagem.read()
        finally:
            produto.imagem.close()

    except Exception as exc:
        raise ValueError(
            f"Não foi possível carregar a imagem do produto: {exc}"
        ) from exc


def obter_nome_imagem(produto):
    """
    Obtém o nome original da imagem.
    """

    if not produto.imagem:
        return "imagem.jpg"

    nome = Path(
        produto.imagem.name
    ).name

    if not nome:
        return "imagem.jpg"

    return nome


def obter_content_type(nome_imagem):
    """
    Determina o MIME type da imagem.
    """

    extensao = Path(
        nome_imagem
    ).suffix.lower().replace(".", "")

    if extensao in FORMATOS_PERMITIDOS:
        return FORMATOS_PERMITIDOS[extensao]

    content_type, _ = mimetypes.guess_type(
        nome_imagem
    )

    if content_type in FORMATOS_PERMITIDOS.values():
        return content_type

    return None


def normalizar_texto(valor):
    """
    Normaliza texto para comparações.
    """

    if valor is None:
        return ""

    return (
        str(valor)
        .strip()
        .lower()
        .replace("á", "a")
        .replace("à", "a")
        .replace("ã", "a")
        .replace("â", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("õ", "o")
        .replace("ú", "u")
        .replace("ç", "c")
    )


# ============================================================
# NORMALIZAÇÃO DO RESULTADO DA IA
# ============================================================

def normalizar_resultado_ia(resultado_ia):
    """
    Normaliza o resultado recebido da API de IA para o formato
    utilizado pelo sistema.
    """

    if not isinstance(resultado_ia, dict):
        raise ValueError(
            "A API de IA retornou um resultado inválido."
        )

    classe = (
        resultado_ia.get("classe")
        or resultado_ia.get("class")
        or resultado_ia.get("classe_identificada")
        or ""
    )

    produto_detectado = (
        resultado_ia.get("produto")
        or resultado_ia.get("cultura")
        or ""
    )

    problema = (
        resultado_ia.get("problema")
        or resultado_ia.get("doenca")
        or resultado_ia.get("doenca_identificada")
        or ""
    )

    tipo = (
        resultado_ia.get("tipo")
        or resultado_ia.get("resultado")
        or ""
    )

    confianca = (
        resultado_ia.get("confianca")
        or resultado_ia.get("confidence")
        or resultado_ia.get("precisao")
        or 0
    )

    try:
        confianca = float(confianca)
    except (
        TypeError,
        ValueError,
    ):
        confianca = 0

    if confianca <= 1:
        confianca *= 100

    confianca = max(
        0,
        min(100, confianca)
    )

    tipo_normalizado = normalizar_texto(
        tipo
    )

    problema_normalizado = normalizar_texto(
        problema
    )

    if any(
        palavra in tipo_normalizado
        for palavra in [
            "saudavel",
            "healthy",
            "normal",
        ]
    ):
        resultado = "saudavel"

    elif any(
        palavra in tipo_normalizado
        for palavra in [
            "praga",
            "pest",
            "inseto",
        ]
    ):
        resultado = "praga"

    elif any(
        palavra in tipo_normalizado
        for palavra in [
            "fungo",
            "fungal",
            "fungica",
        ]
    ):
        resultado = "fungo"

    elif any(
        palavra in tipo_normalizado
        for palavra in [
            "deficiencia",
            "nutricional",
            "nutriente",
        ]
    ):
        resultado = "deficiencia"

    elif any(
        palavra in tipo_normalizado
        for palavra in [
            "doenca",
            "disease",
        ]
    ):
        resultado = "doenca"

    elif problema_normalizado:
        resultado = "doenca"

    else:
        resultado = "indeterminado"

    descricao = (
        resultado_ia.get("descricao")
        or resultado_ia.get("descricao_resultado")
        or ""
    )

    recomendacoes = (
        resultado_ia.get("recomendacoes")
        or resultado_ia.get("recomendacao")
        or ""
    )

    principais_previsoes = (
        resultado_ia.get("principais_previsoes")
        or resultado_ia.get("previsoes")
        or []
    )

    if not descricao:

        if resultado == "saudavel":
            descricao = (
                "A análise da inteligência artificial indica "
                "que a cultura apresenta características "
                "compatíveis com uma condição saudável."
            )

        elif resultado == "praga":
            descricao = (
                "A inteligência artificial identificou "
                "características compatíveis com a presença "
                "de uma possível praga."
            )

        elif resultado == "fungo":
            descricao = (
                "A análise identificou características "
                "compatíveis com uma possível doença fúngica."
            )

        elif resultado == "deficiencia":
            descricao = (
                "Foram identificadas características que podem "
                "estar relacionadas com uma deficiência nutricional."
            )

        elif resultado == "doenca":
            descricao = (
                "A inteligência artificial identificou "
                "características compatíveis com uma possível doença."
            )

        else:
            descricao = (
                "Não foi possível determinar com segurança "
                "a condição da cultura."
            )

    if not recomendacoes:

        if resultado == "saudavel":
            recomendacoes = (
                "Continue a acompanhar regularmente a cultura, "
                "mantenha boas práticas agrícolas e realize "
                "novas análises sempre que observar alterações."
            )

        elif resultado in [
            "doenca",
            "fungo",
            "praga",
            "deficiencia",
        ]:
            recomendacoes = (
                "Recomenda-se acompanhar a evolução dos sintomas, "
                "verificar as condições da cultura e procurar "
                "orientação de um técnico agrícola antes de aplicar "
                "qualquer tratamento."
            )

        else:
            recomendacoes = (
                "Realize uma nova análise utilizando uma imagem "
                "de boa qualidade e, se possível, procure "
                "avaliação técnica."
            )

    baixa_confianca = confianca < 40

    return {
        "classe": classe,
        "produto": produto_detectado,
        "problema": problema,
        "tipo": tipo,
        "resultado": resultado,
        "confianca": round(confianca, 2),
        "descricao": descricao,
        "recomendacoes": recomendacoes,
        "principais_previsoes": principais_previsoes,
        "baixa_confianca": baixa_confianca,
        "resultado_bruto": resultado_ia,
    }


# ============================================================
# COMPATIBILIDADE DO PRODUTO
# ============================================================

def verificar_compatibilidade(
    produto,
    produto_detectado,
):
    """
    Verifica se a cultura identificada pela IA corresponde
    ao produto selecionado.
    """

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
            "feijao comum",
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
    }

    for cultura, nomes in equivalencias.items():

        produto_correspondente = any(
            cultura in produto_base
            or nome in produto_base
            for nome in nomes
        )

        detectado_correspondente = any(
            cultura in detectado
            or nome in detectado
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


# ============================================================
# OBSERVAÇÕES
# ============================================================

def construir_observacoes(
    produto,
    resultado,
    compativel=True,
):
    """
    Constrói observações complementares para o diagnóstico.
    """

    observacoes = []

    if not compativel:
        observacoes.append(
            "A cultura identificada pela inteligência artificial "
            "não corresponde claramente ao produto selecionado. "
            "O resultado deve ser interpretado com cautela."
        )

    if resultado.get("baixa_confianca"):
        observacoes.append(
            "A confiança da inteligência artificial está abaixo "
            "do nível mínimo recomendado para uma interpretação "
            "segura."
        )

    if resultado.get("produto"):
        observacoes.append(
            f"Cultura identificada pela IA: "
            f"{resultado['produto']}."
        )

    if resultado.get("classe"):
        observacoes.append(
            f"Classe identificada: "
            f"{resultado['classe']}."
        )

    if not observacoes:
        observacoes.append(
            "Diagnóstico processado com sucesso pela "
            "inteligência artificial."
        )

    return "\n".join(
        observacoes
    )


# ============================================================
# API DE INTELIGÊNCIA ARTIFICIAL
# ============================================================

def enviar_para_api_ia(
    imagem_bytes,
    nome_imagem,
):
    """
    Envia a imagem para a API FastAPI.
    """

    if not imagem_bytes:
        raise ValueError(
            "A imagem está vazia."
        )

    tamanho = len(
        imagem_bytes
    )

    if tamanho > MAX_IMAGE_SIZE:
        raise ValueError(
            "A imagem excede o limite máximo de 10 MB."
        )

    content_type = obter_content_type(
        nome_imagem
    )

    if not content_type:
        raise ValueError(
            "Formato de imagem não suportado. "
            "Utilize JPG, JPEG, PNG ou WEBP."
        )

    try:
        response = requests.post(
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
        raise ConnectionError(
            "Não foi possível conectar ao serviço de "
            "inteligência artificial. Verifique se a API "
            "está em execução."
        ) from exc

    except requests.exceptions.Timeout as exc:
        raise TimeoutError(
            "A análise demorou demasiado tempo e ultrapassou "
            "o limite definido."
        ) from exc

    except requests.exceptions.RequestException as exc:
        raise RuntimeError(
            f"Erro de comunicação com a API de IA: {exc}"
        ) from exc

    if response.status_code != 200:
        try:
            detalhe = response.json()
        except ValueError:
            detalhe = response.text

        raise RuntimeError(
            f"A API de IA retornou o estado "
            f"{response.status_code}: {detalhe}"
        )

    try:
        dados = response.json()
    except ValueError as exc:
        raise ValueError(
            "A API de IA não retornou um JSON válido."
        ) from exc

    if not isinstance(dados, dict):
        raise ValueError(
            "A resposta da API possui um formato inválido."
        )

    if dados.get("sucesso") is False:
        raise RuntimeError(
            dados.get(
                "erro",
                "A inteligência artificial não conseguiu "
                "processar a imagem."
            )
        )

    resultado = dados.get(
        "resultado"
    )

    if resultado is None:
        resultado = dados

    if not isinstance(resultado, dict):
        raise ValueError(
            "O resultado recebido da IA possui formato inválido."
        )

    return resultado


# ============================================================
# PÁGINA PRINCIPAL DE DIAGNÓSTICO
# ============================================================

@login_required
def diagnostico(
    request,
    produto_id=None,
):
    """
    Página principal de diagnóstico.

    Pode funcionar de duas formas:

    /diagnostico/
        Mostra todos os produtos.

    /diagnostico/produto/1/
        Mostra o diagnóstico de um produto específico.
    """

    contadores = obter_contadores()

    estatisticas = obter_estatisticas_utilizador(
        request
    )

    produtos = obter_produtos_ativos(
        request
    )

    produto = None
    diagnostico_atual = None
    historico = []

    # --------------------------------------------------------
    # MODO PRODUTO
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # MODO GERAL
    # --------------------------------------------------------

    else:

        # Não adicionamos atributos diretamente ao objeto
        # ProdutoAgricola. Isso evita conflitos com propriedades
        # definidas no model.

        produtos = list(
            produtos
        )

        for item in produtos:

            item.diagnosticos_usuario = list(
                Diagnostico.objects
                .filter(
                    usuario=request.user,
                    produto=item,
                )
                .order_by("-data_criacao")[:5]
            )

            item.ultimo_diagnostico_usuario = (
                item.diagnosticos_usuario[0]
                if item.diagnosticos_usuario
                else None
            )

            item.numero_diagnosticos_usuario = (
                Diagnostico.objects
                .filter(
                    usuario=request.user,
                    produto=item,
                )
                .count()
            )

        estatisticas_produto = None

    # --------------------------------------------------------
    # CONTEXTO
    # --------------------------------------------------------

    contexto = {
        "produtos": produtos,
        "produto": produto,
        "diagnostico": diagnostico_atual,
        "diagnostico_atual": diagnostico_atual,
        "historico": historico,

        "total_produtos": contadores[
            "produtos_ativos"
        ],

        "total_diagnosticos": estatisticas[
            "total"
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

        "media_confianca": estatisticas[
            "media_confianca"
        ],

        "precisao_ia": contadores[
            "precisao_ia"
        ],

        "ultimos_diagnosticos": obter_ultimos_diagnosticos(
            request,
            produto=produto,
            limite=5,
        ),

        "estatisticas": estatisticas,

        "estatisticas_produto": estatisticas_produto,
    }

    return render(
        request,
        "diagnostico/diagnostico.html",
        contexto,
    )


# ============================================================
# ANALISAR IMAGEM
# ============================================================

@login_required
@require_POST
def analisar(
    request,
    produto_id=None,
):
    """
    Executa o diagnóstico de um produto.
    """

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
                "Produto inválido."
            )
            return redirect(
                "diagnostico:diagnostico"
            )

    if produto_id is None:
        messages.error(
            request,
            "É necessário selecionar um produto."
        )
        return redirect(
            "diagnostico:diagnostico"
        )

    produto = obter_produto(
        produto_id
    )

    diagnostico_obj = None

    try:

        # ----------------------------------------------------
        # CARREGAR IMAGEM
        # ----------------------------------------------------

        imagem_bytes = obter_imagem_produto(
            produto
        )

        nome_imagem = obter_nome_imagem(
            produto
        )

        # ----------------------------------------------------
        # CRIAR DIAGNÓSTICO PENDENTE
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
        )

        # ----------------------------------------------------
        # ENVIAR PARA IA
        # ----------------------------------------------------

        resultado_ia = enviar_para_api_ia(
            imagem_bytes,
            nome_imagem,
        )

        resultado = normalizar_resultado_ia(
            resultado_ia
        )

        # ----------------------------------------------------
        # VERIFICAR CULTURA
        # ----------------------------------------------------

        compativel = verificar_compatibilidade(
            produto,
            resultado.get("produto"),
        )

        observacoes = construir_observacoes(
            produto,
            resultado,
            compativel,
        )

        # ----------------------------------------------------
        # GUARDAR RESULTADO
        # ----------------------------------------------------

        with transaction.atomic():

            diagnostico_obj.classe_identificada = (
                resultado.get("classe", "")
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
            "Diagnóstico concluído com sucesso."
        )

        return redirect(
            "diagnostico:detalhe",
            diagnostico_id=diagnostico_obj.pk,
        )

    except Exception as exc:

        erro = str(exc)

        # ----------------------------------------------------
        # REGISTAR ERRO
        # ----------------------------------------------------

        if diagnostico_obj is not None:

            try:

                diagnostico_obj.status = "erro"
                diagnostico_obj.resultado = "indeterminado"
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
            f"Não foi possível realizar o diagnóstico: {erro}"
        )

        return redirect(
            "diagnostico:diagnostico_produto",
            produto_id=produto.pk,
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
    Mostra o histórico completo de diagnósticos de um produto.
    """

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
        .values("resultado")
        .annotate(total=Count("id"))
        .order_by("-total")
    )

    evolucao_confianca = []

    for item in diagnosticos:

        if item.status != "concluido":
            continue

        evolucao_confianca.append({
            "data": item.data_criacao,
            "confianca": float(
                item.confianca or 0
            ),
            "resultado": item.resultado,
        })

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

        "ultimos_diagnosticos": obter_ultimos_diagnosticos(
            request,
            produto,
            limite=10,
        ),
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
    Mostra os detalhes de um diagnóstico específico.
    """

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

        "ultimos_diagnosticos": recentes,

        "estatisticas": estatisticas,
    }

    return render(
        request,
        "diagnostico/detalhe.html",
        contexto,
    )
