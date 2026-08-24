from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from culturas.models import ProdutoAgricola
from diagnostico.models import Diagnostico

from .forms import UserUpdateForm, PerfilUpdateForm
from .models import Perfil


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def obter_perfil_usuario(user):
    """
    Obtém ou cria o perfil pertencente ao utilizador autenticado.

    Cada utilizador possui o seu próprio Perfil.
    """
    perfil_usuario, created = Perfil.objects.get_or_create(
        user=user,
        defaults={
            "provincia": "Moxico",
            "tipo_utilizador": "outro",
        },
    )

    return perfil_usuario


def produtos_do_usuario(user):
    """
    Retorna somente os produtos pertencentes ao utilizador.

    IMPORTANTE:
    O modelo ProdutoAgricola deve possuir:

        usuario = models.ForeignKey(
            User,
            on_delete=models.CASCADE,
            related_name="produtos_agricolas",
        )

    Assim, os produtos ficam isolados por conta.
    """
    return (
        ProdutoAgricola.objects
        .filter(
            usuario=user,
            ativo=True,
        )
        .prefetch_related("categorias")
    )


# ============================================================
# PÁGINA INICIAL
# ============================================================

def home(request):
    """
    Página inicial do AgroIA Moxico.

    Se o utilizador estiver autenticado:
    - mostra os produtos dele;
    - mostra os diagnósticos dele.

    Para visitantes:
    - não expõe dados privados de outros utilizadores.
    """

    if request.user.is_authenticated:

        produtos = (
            ProdutoAgricola.objects
            .filter(
                usuario=request.user,
                ativo=True,
            )
            .prefetch_related("categorias")
        )

        total_produtos = produtos.count()

        produtos_analise = produtos.filter(
            analise_por_imagem=True
        )

        total_produtos_analise = produtos_analise.count()

        total_diagnosticos = (
            Diagnostico.objects
            .filter(usuario=request.user)
            .count()
        )

        meus_diagnosticos = total_diagnosticos

    else:
        # Visitantes não recebem dados privados de utilizadores.
        produtos = ProdutoAgricola.objects.none()

        total_produtos = 0

        produtos_analise = ProdutoAgricola.objects.none()

        total_produtos_analise = 0

        total_diagnosticos = 0

        meus_diagnosticos = 0

    contexto = {
        "produtos": produtos,
        "total_produtos": total_produtos,
        "produtos_analise": produtos_analise,
        "total_produtos_analise": total_produtos_analise,
        "total_diagnosticos": total_diagnosticos,
        "meus_diagnosticos": meus_diagnosticos,
    }

    return render(
        request,
        "inicio/home.html",
        contexto,
    )


# ============================================================
# LOGIN
# ============================================================

def login_view(request):
    """
    Login normal do Django.

    Não utiliza:
    - OTP
    - SMS
    - autenticação por dispositivo
    - autenticação de dois fatores
    """

    if request.user.is_authenticated:
        return redirect("inicio:perfil")

    next_url = (
        request.POST.get("next")
        or request.GET.get("next")
        or ""
    ).strip()

    # --------------------------------------------------------
    # PROTEÇÃO CONTRA REDIRECIONAMENTOS EXTERNOS
    # --------------------------------------------------------

    if next_url and not url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = ""

    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    if request.method == "POST":

        username = request.POST.get(
            "username",
            "",
        ).strip()

        password = request.POST.get(
            "password",
            "",
        )

        remember = request.POST.get("remember") == "on"

        # ----------------------------------------------------
        # VALIDAÇÃO DO UTILIZADOR
        # ----------------------------------------------------

        if not username:
            messages.error(
                request,
                "Digite o seu nome de utilizador.",
            )

            return render(
                request,
                "inicio/login.html",
                {
                    "next": next_url,
                    "username_value": username,
                },
            )

        # ----------------------------------------------------
        # VALIDAÇÃO DA PALAVRA-PASSE
        # ----------------------------------------------------

        if not password:
            messages.error(
                request,
                "Digite a sua palavra-passe.",
            )

            return render(
                request,
                "inicio/login.html",
                {
                    "next": next_url,
                    "username_value": username,
                },
            )

        # ----------------------------------------------------
        # AUTENTICAÇÃO
        # ----------------------------------------------------

        user = authenticate(
            request,
            username=username,
            password=password,
        )

        if user is not None:

            # Garante que o perfil existe.
            obter_perfil_usuario(user)

            login(
                request,
                user,
            )

            # ------------------------------------------------
            # DURAÇÃO DA SESSÃO
            # ------------------------------------------------

            if remember:
                request.session.set_expiry(
                    60 * 60 * 24 * 30
                )
            else:
                request.session.set_expiry(0)

            messages.success(
                request,
                f"Bem-vindo, "
                f"{user.first_name or user.username}!",
            )

            if next_url:
                return redirect(next_url)

            return redirect("inicio:home")

        # ----------------------------------------------------
        # LOGIN INVÁLIDO
        # ----------------------------------------------------

        messages.error(
            request,
            "Nome de utilizador ou palavra-passe incorretos.",
        )

        return render(
            request,
            "inicio/login.html",
            {
                "next": next_url,
                "username_value": username,
            },
        )

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    return render(
        request,
        "inicio/login.html",
        {
            "next": next_url,
        },
    )


# ============================================================
# LOGOUT
# ============================================================

@login_required
def logout_view(request):
    """
    Termina completamente a sessão do utilizador.

    O logout do Django limpa a sessão autenticada.
    Nenhum dado permanente do utilizador é apagado.
    """

    nome_usuario = (
        request.user.first_name
        or request.user.username
    )

    # --------------------------------------------------------
    # LIMPA A SESSÃO
    # --------------------------------------------------------

    logout(request)

    # --------------------------------------------------------
    # NOVA SESSÃO APENAS PARA A MENSAGEM
    # --------------------------------------------------------

    messages.success(
        request,
        f"Sessão de {nome_usuario} terminada com sucesso.",
    )

    return redirect("inicio:home")


# ============================================================
# CADASTRO
# ============================================================

def cadastro(request):
    """
    Cria uma nova conta de utilizador.

    A fotografia não é adicionada durante o cadastro.

    O perfil é criado automaticamente e fica associado
    exclusivamente ao novo utilizador.
    """

    if request.user.is_authenticated:
        return redirect("inicio:perfil")

    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    if request.method == "POST":

        username = request.POST.get(
            "username",
            "",
        ).strip()

        first_name = request.POST.get(
            "first_name",
            "",
        ).strip()

        last_name = request.POST.get(
            "last_name",
            "",
        ).strip()

        email = request.POST.get(
            "email",
            "",
        ).strip().lower()

        password = request.POST.get(
            "password",
            "",
        )

        password_confirm = request.POST.get(
            "password_confirm",
            request.POST.get(
                "password2",
                "",
            ),
        )

        telefone = request.POST.get(
            "telefone",
            "",
        ).strip()

        localizacao = request.POST.get(
            "localizacao",
            "",
        ).strip()

        municipio = request.POST.get(
            "municipio",
            "",
        ).strip()

        provincia = request.POST.get(
            "provincia",
            "Moxico",
        ).strip()

        tipo_utilizador = request.POST.get(
            "tipo_utilizador",
            "outro",
        ).strip()

        # ----------------------------------------------------
        # VALIDAÇÕES
        # ----------------------------------------------------

        if not username:
            messages.error(
                request,
                "Informe o nome de utilizador.",
            )

            return render(
                request,
                "inicio/cadastro.html",
            )

        if not password:
            messages.error(
                request,
                "Informe uma palavra-passe.",
            )

            return render(
                request,
                "inicio/cadastro.html",
            )

        if password != password_confirm:
            messages.error(
                request,
                "As palavras-passe não coincidem.",
            )

            return render(
                request,
                "inicio/cadastro.html",
            )

        if len(password) < 8:
            messages.error(
                request,
                "A palavra-passe deve ter pelo menos 8 caracteres.",
            )

            return render(
                request,
                "inicio/cadastro.html",
            )

        if User.objects.filter(
            username__iexact=username
        ).exists():

            messages.error(
                request,
                "Este nome de utilizador já está em uso.",
            )

            return render(
                request,
                "inicio/cadastro.html",
            )

        if email and User.objects.filter(
            email__iexact=email
        ).exists():

            messages.error(
                request,
                "Este endereço de e-mail já está registado.",
            )

            return render(
                request,
                "inicio/cadastro.html",
            )

        try:

            with transaction.atomic():

                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                )

                Perfil.objects.create(
                    user=user,
                    telefone=telefone,
                    localizacao=localizacao,
                    municipio=municipio,
                    provincia=provincia or "Moxico",
                    tipo_utilizador=(
                        tipo_utilizador
                        or "outro"
                    ),
                )

        except Exception:

            messages.error(
                request,
                "Não foi possível criar a conta. "
                "Verifique os dados e tente novamente.",
            )

            return render(
                request,
                "inicio/cadastro.html",
            )

        login(
            request,
            user,
        )

        messages.success(
            request,
            "Conta criada com sucesso! "
            "Bem-vindo ao AgroIA Moxico.",
        )

        return redirect(
            "inicio:perfil"
        )


    return render(
        request,
        "inicio/cadastro.html",
    )



@login_required
def perfil(request):

    perfil_usuario = obter_perfil_usuario(
        request.user
    )


    diagnosticos_usuario = (
        Diagnostico.objects
        .filter(
            usuario=request.user
        )
    )

    total_diagnosticos = (
        diagnosticos_usuario.count()
    )

    diagnosticos_concluidos = (
        diagnosticos_usuario
        .filter(
            status="concluido"
        )
        .count()
    )

    produtos_usuario = (
        ProdutoAgricola.objects
        .filter(
            usuario=request.user
        )
    )

    total_produtos = (
        produtos_usuario.count()
    )


    total_produtos_ativos = (
        produtos_usuario
        .filter(
            ativo=True
        )
        .count()
    )


    total_produtos_analise = (
        produtos_usuario
        .filter(
            ativo=True,
            analise_por_imagem=True,
        )
        .count()
    )

    contexto = {
        "perfil": perfil_usuario,
        "usuario": request.user,

        "total_diagnosticos": total_diagnosticos,
        "diagnosticos_concluidos": diagnosticos_concluidos,

        "total_produtos": total_produtos,
        "total_produtos_ativos": total_produtos_ativos,
        "total_produtos_analise": total_produtos_analise,
    }

    return render(
        request,
        "inicio/perfil.html",
        contexto,
    )



@login_required
def editar_perfil(request):

    perfil_usuario = obter_perfil_usuario(
        request.user
    )

    if request.method == "POST":

        user_form = UserUpdateForm(
            request.POST,
            instance=request.user,
        )

        perfil_form = PerfilUpdateForm(
            request.POST,
            request.FILES,
            instance=perfil_usuario,
        )

        if (
            user_form.is_valid()
            and perfil_form.is_valid()
        ):

            with transaction.atomic():

                user_form.save()

                perfil_form.save()

            messages.success(
                request,
                "O seu perfil foi atualizado com sucesso.",
            )

            return redirect(
                "inicio:perfil"
            )

        messages.error(
            request,
            "Não foi possível atualizar o perfil. "
            "Verifique os campos assinalados.",
        )


    else:

        user_form = UserUpdateForm(
            instance=request.user,
        )

        perfil_form = PerfilUpdateForm(
            instance=perfil_usuario,
        )

    contexto = {
        "perfil": perfil_usuario,
        "usuario": request.user,
        "user_form": user_form,
        "perfil_form": perfil_form,
    }

    return render(
        request,
        "inicio/editar_perfil.html",
        contexto,
    )



@login_required
def remover_foto_perfil(request):

    if request.method != "POST":
        return redirect(
            "inicio:perfil"
        )

    perfil_usuario = obter_perfil_usuario(
        request.user
    )

    if perfil_usuario.foto:

        perfil_usuario.foto.delete(
            save=False
        )

        perfil_usuario.foto = None

        perfil_usuario.save(
            update_fields=[
                "foto",
                "data_atualizacao",
            ]
        )

        messages.success(
            request,
            "A fotografia de perfil foi removida.",
        )

    else:

        messages.info(
            request,
            "Não existe nenhuma fotografia de perfil para remover.",
        )

    return redirect(
        "inicio:perfil"
    )

@login_required
def produtos(request):


    produtos_lista = (
        ProdutoAgricola.objects
        .filter(
            usuario=request.user,
            ativo=True,
        )
        .prefetch_related("categorias")
    )

    contexto = {
        "produtos": produtos_lista,
        "total_produtos": produtos_lista.count(),
    }

    return render(
        request,
        "inicio/produtos.html",
        contexto,
    )



@login_required
def detalhe_produto(request, pk):


    produto = get_object_or_404(
        ProdutoAgricola.objects.prefetch_related(
            "categorias"
        ),
        pk=pk,
        usuario=request.user,
        ativo=True,
    )

    contexto = {
        "produto": produto,
    }

    return render(
        request,
        "culturas/detalhe_produto.html",
        contexto,
    )



@login_required
def pesquisar_produtos(request):


    termo = request.GET.get(
        "q",
        "",
    ).strip()

    produtos_lista = (
        ProdutoAgricola.objects
        .filter(
            usuario=request.user,
            ativo=True,
        )
        .prefetch_related("categorias")
    )

    if termo:

        produtos_lista = (
            produtos_lista
            .filter(
                Q(nome__icontains=termo)
                | Q(descricao__icontains=termo)
                | Q(problemas__icontains=termo)
                | Q(
                    categorias__nome__icontains=termo
                )
            )
            .distinct()
        )

    contexto = {
        "produtos": produtos_lista,
        "termo": termo,
        "total_produtos": produtos_lista.count(),
    }

    return render(
        request,
        "inicio/produtos.html",
        contexto,
    )




def sobre(request):


    return render(
        request,
        "inicio/sobre.html",
    )
