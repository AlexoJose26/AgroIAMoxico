from pathlib import Path
import mimetypes

import requests

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Avg, Count
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
        "media_confianca": float(media_confianca or 0),
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
    return (
        ProdutoAgricola.objects
        .filter(ativo=True)
        .prefetch_related("categorias")
        .order_by("nome")
    )


def obter_produto(produto_id):
    return get_object_or_404(
        ProdutoAgricola.objects
        .filter(ativo=True)
        .prefetch_related("categorias"),
        pk=produto_id,
    )


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
        .replace(".", "")
    )

    if extensao in FORMATOS_PERMITIDOS:
        return FORMATOS_PERMITIDOS[extensao]

    content_type, _ = mimetypes.guess_type(
        nome_imagem
    )

    if content_type in FORMATOS_PERMITIDOS.values():
        return content_type

    return None


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

    if not (
        url.startswith("http://")
        or url.startswith("https://")
    ):
        raise ValueError(
            "A imagem do produto não possui uma URL pública válida."
        )

    return url


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

    try:
        if (
            nome.startswith("http://")
            or nome.startswith("https://")
        ):
            return baixar_imagem_da_url(nome)
    except AttributeError:
        pass

    try:
        url = obter_url_imagem_produto(
            produto
        )

        return baixar_imagem_da_url(
            url
        )

    except Exception as erro_url:
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
                f"URL: {erro_url}. "
                f"Storage: {erro_storage}."
            ) from erro_storage


def normalizar_texto(valor):
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


def normalizar_resultado_ia(resultado_ia):
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
        if resultado_ia.get("confianca") is not None
        else resultado_ia.get("confidence")
    )

    if confianca is None:
        confianca = resultado_ia.get(
            "precisao",
            0,
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
        min(100, confianca),
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
            "fungico",
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

    elif any(
        palavra in tipo_normalizado
        for palavra in [
            "viral",
            "virus",
        ]
    ):
        resultado = "doenca"

    elif problema_normalizado:
        problema_lower = problema_normalizado

        if any(
            palavra in problema_lower
            for palavra in [
                "acaro",
                "inseto",
                "praga",
            ]
        ):
            resultado = "praga"

        elif any(
            palavra in problema_lower
            for palavra in [
                "fungo",
                "ferrugem",
                "oídio",
                "oidio",
                "podridao",
                "mancha",
                "requeima",
            ]
        ):
            resultado = "fungo"

        elif any(
            palavra in problema_lower
            for palavra in [
                "virus",
                "viral",
            ]
        ):
            resultado = "doenca"

        else:
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

    return {
        "classe": classe,
        "produto": produto_detectado,
        "problema": problema,
        "tipo": tipo,
        "resultado": resultado,
        "confianca": round(
            confianca,
            2,
        ),
        "descricao": descricao,
        "recomendacoes": recomendacoes,
        "principais_previsoes": principais_previsoes,
        "baixa_confianca": confianca < 40,
        "resultado_bruto": resultado_ia,
    }


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

    for cultura, nomes in equivalencias.items():
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

    if resultado.get("baixa_confianca"):
        observacoes.append(
            "A confiança da inteligência artificial está abaixo "
            "do nível mínimo recomendado para uma interpretação "
            "segura."
        )

    if resultado.get("produto"):
        observacoes.append(
            "Cultura identificada pela IA: "
            f"{resultado['produto']}."
        )

    if resultado.get("classe"):
        observacoes.append(
            "Classe identificada: "
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


def enviar_para_api_ia(
    imagem_bytes,
    nome_imagem,
):
    if not imagem_bytes:
        raise ValueError(
            "A imagem está vazia."
        )

    if len(imagem_bytes) > MAX_IMAGE_SIZE:
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

    if not API_IA_URL:
        raise RuntimeError(
            "A URL da API de inteligência artificial não está configurada."
        )

    if (
        API_IA_URL.startswith(
            "http://127.0.0.1"
        )
        or API_IA_URL.startswith(
            "http://localhost"
        )
    ) and not settings.DEBUG:
        raise RuntimeError(
            "A API de IA está configurada para localhost. "
            "Na Vercel, AGROIA_API_URL deve apontar para a URL "
            "pública da API FastAPI."
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
            "Não foi possível conectar ao serviço de inteligência "
            "artificial. Verifique se a API FastAPI está online "
            "e se AGROIA_API_URL aponta para a URL correta."
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
            "A API de IA retornou o estado "
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
                "processar a imagem.",
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


@login_required
def diagnostico(
    request,
    produto_id=None,
):
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

    else:
        produtos = list(
            produtos
        )

        for item in produtos:
            diagnosticos_usuario = list(
                Diagnostico.objects
                .filter(
                    usuario=request.user,
                    produto=item,
                )
                .select_related(
                    "produto"
                )
                .order_by(
                    "-data_criacao"
                )[:5]
            )

            item.diagnosticos_usuario = (
                diagnosticos_usuario
            )

            item.ultimo_diagnostico_usuario = (
                diagnosticos_usuario[0]
                if diagnosticos_usuario
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
        imagem_bytes = obter_imagem_produto(
            produto
        )

        nome_imagem = obter_nome_imagem(
            produto
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
        )

        resultado_ia = enviar_para_api_ia(
            imagem_bytes,
            nome_imagem,
        )

        resultado = normalizar_resultado_ia(
            resultado_ia
        )

        compativel = verificar_compatibilidade(
            produto,
            resultado.get("produto"),
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
        erro = str(exc)

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
        .values("resultado")
        .annotate(
            total=Count("id")
        )
        .order_by("-total")
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
        "ultimos_diagnosticos": obter_ultimos_diagnosticos(
            request,
            produto=produto,
            limite=10,
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
        "ultimos_diagnosticos": recentes,
        "estatisticas": estatisticas,
    }

    return render(
        request,
        "diagnostico/detalhe.html",
        contexto,
    )
