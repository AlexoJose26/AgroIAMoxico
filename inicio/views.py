from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import FieldError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from produtos.models import ProdutoAgricola
from diagnostico.models import Diagnostico

from .forms import UserUpdateForm, PerfilUpdateForm
from .models import Perfil


def obter_perfil_usuario(user):
    perfil_usuario, created = Perfil.objects.get_or_create(
        user=user,
        defaults={
            "provincia": "Moxico",
            "tipo_utilizador": "outro",
        },
    )
    return perfil_usuario


def produtos_do_usuario(user):
    try:
        return (
            ProdutoAgricola.objects
            .filter(
                usuario=user,
                ativo=True,
            )
            .prefetch_related("categorias")
        )
    except FieldError:
        return ProdutoAgricola.objects.none()


def home(request):
    produtos = ProdutoAgricola.objects.none()
    produtos_analise = ProdutoAgricola.objects.none()
    ultimos_diagnosticos = Diagnostico.objects.none()

    total_produtos = 0
    total_produtos_analise = 0
    total_diagnosticos = 0
    meus_diagnosticos = 0

    if request.user.is_authenticated:
        usuario = request.user

        try:
            produtos = (
                ProdutoAgricola.objects
                .filter(
                    usuario=usuario,
                    ativo=True,
                )
                .prefetch_related("categorias")
            )

            total_produtos = produtos.count()

        except FieldError as e:
            print(
                "ERRO NOS PRODUTOS DA HOME:",
                repr(e),
            )

            produtos = ProdutoAgricola.objects.none()
            total_produtos = 0

        except Exception as e:
            print(
                "ERRO AO CARREGAR PRODUTOS DA HOME:",
                repr(e),
            )

            produtos = ProdutoAgricola.objects.none()
            total_produtos = 0

        try:
            produtos_analise = (
                produtos.filter(
                    analise_por_imagem=True,
                )
            )

            total_produtos_analise = (
                produtos_analise.count()
            )

        except FieldError as e:
            print(
                "CAMPO analise_por_imagem NÃO DISPONÍVEL:",
                repr(e),
            )

            produtos_analise = ProdutoAgricola.objects.none()
            total_produtos_analise = 0

        except Exception as e:
            print(
                "ERRO AO CARREGAR PRODUTOS PARA ANÁLISE:",
                repr(e),
            )

            produtos_analise = ProdutoAgricola.objects.none()
            total_produtos_analise = 0

        try:
            total_diagnosticos = (
                Diagnostico.objects
                .filter(
                    usuario=usuario,
                )
                .count()
            )

            meus_diagnosticos = total_diagnosticos

        except FieldError as e:
            print(
                "ERRO NO CAMPO usuario DE DIAGNOSTICO:",
                repr(e),
            )

            total_diagnosticos = 0
            meus_diagnosticos = 0

        except Exception as e:
            print(
                "ERRO AO CONTAR DIAGNOSTICOS:",
                repr(e),
            )

            total_diagnosticos = 0
            meus_diagnosticos = 0

        try:
            ultimos_diagnosticos = (
                Diagnostico.objects
                .filter(
                    usuario=usuario,
                )
                .select_related("produto")
                .order_by("-data_criacao")[:5]
            )

        except FieldError as e:
            print(
                "ERRO AO CARREGAR ULTIMOS DIAGNOSTICOS:",
                repr(e),
            )

            try:
                ultimos_diagnosticos = (
                    Diagnostico.objects
                    .filter(
                        usuario=usuario,
                    )
                    .select_related("produto")[:5]
                )
            except Exception as fallback_error:
                print(
                    "ERRO NO FALLBACK DOS DIAGNOSTICOS:",
                    repr(fallback_error),
                )

                ultimos_diagnosticos = (
                    Diagnostico.objects.none()
                )

        except Exception as e:
            print(
                "ERRO AO CARREGAR DIAGNOSTICOS DA HOME:",
                repr(e),
            )

            ultimos_diagnosticos = (
                Diagnostico.objects.none()
            )

    contexto = {
        "produtos": produtos,
        "produtos_analise": produtos_analise,
        "ultimos_diagnosticos": ultimos_diagnosticos,
        "total_produtos": total_produtos,
        "total_produtos_analise": total_produtos_analise,
        "total_diagnosticos": total_diagnosticos,
        "meus_diagnosticos": meus_diagnosticos,
    }

    return render(
        request,
        "inicio/home.html",
        contexto,
    )


def login_view(request):
    if request.user.is_authenticated:
        return redirect("inicio:home")

    next_url = (
        request.POST.get("next")
        or request.GET.get("next")
        or ""
    ).strip()

    if next_url and not url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = ""

    if request.method == "POST":
        username = request.POST.get(
            "username",
            "",
        ).strip()

        password = request.POST.get(
            "password",
            "",
        )

        remember = request.POST.get(
            "remember",
        ) == "on"

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

        user = authenticate(
            request,
            username=username,
            password=password,
        )

        if user is None:
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

        try:
            obter_perfil_usuario(user)
        except Exception as e:
            print(
                "ERRO AO OBTER PERFIL DURANTE LOGIN:",
                repr(e),
            )

        login(
            request,
            user,
        )

        if remember:
            request.session.set_expiry(
                60 * 60 * 24 * 30
            )
        else:
            request.session.set_expiry(0)

        messages.success(
            request,
            f"Bem-vindo, {user.first_name or user.username}!",
        )

        if next_url:
            return redirect(next_url)

        return redirect("inicio:home")

    return render(
        request,
        "inicio/login.html",
        {
            "next": next_url,
        },
    )


@login_required
def logout_view(request):
    nome_usuario = (
        request.user.first_name
        or request.user.username
    )

    logout(request)

    messages.success(
        request,
        f"Sessão de {nome_usuario} terminada com sucesso.",
    )

    return redirect("inicio:home")


def cadastro(request):
    if request.user.is_authenticated:
        return redirect("inicio:perfil")

    if request.method != "POST":
        return render(
            request,
            "inicio/cadastro.html",
        )

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
        "",
    )

    if not password_confirm:
        password_confirm = request.POST.get(
            "password2",
            "",
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

    dados_formulario = {
        "username": username,
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "telefone": telefone,
        "localizacao": localizacao,
        "municipio": municipio,
        "provincia": provincia or "Moxico",
        "tipo_utilizador": tipo_utilizador or "outro",
    }

    contexto = {
        "dados": dados_formulario,
    }

    if not username:
        messages.error(
            request,
            "Informe o nome de utilizador.",
        )

        return render(
            request,
            "inicio/cadastro.html",
            contexto,
        )

    if len(username) < 3:
        messages.error(
            request,
            "O nome de utilizador deve ter pelo menos 3 caracteres.",
        )

        return render(
            request,
            "inicio/cadastro.html",
            contexto,
        )

    if not password:
        messages.error(
            request,
            "Informe uma palavra-passe.",
        )

        return render(
            request,
            "inicio/cadastro.html",
            contexto,
        )

    if not password_confirm:
        messages.error(
            request,
            "Confirme a sua palavra-passe.",
        )

        return render(
            request,
            "inicio/cadastro.html",
            contexto,
        )

    if password != password_confirm:
        messages.error(
            request,
            "As palavras-passe não coincidem.",
        )

        return render(
            request,
            "inicio/cadastro.html",
            contexto,
        )

    if len(password) < 8:
        messages.error(
            request,
            "A palavra-passe deve ter pelo menos 8 caracteres.",
        )

        return render(
            request,
            "inicio/cadastro.html",
            contexto,
        )

    if User.objects.filter(
        username__iexact=username,
    ).exists():
        messages.error(
            request,
            f"O nome de utilizador '{username}' já está registado.",
        )

        return render(
            request,
            "inicio/cadastro.html",
            contexto,
        )

    if email and User.objects.filter(
        email__iexact=email,
    ).exists():
        messages.error(
            request,
            f"O e-mail '{email}' já está registado.",
        )

        return render(
            request,
            "inicio/cadastro.html",
            contexto,
        )

    tipos_utilizador = getattr(
        Perfil,
        "TIPOS_UTILIZADOR",
        [],
    )

    tipos_validos = {
        escolha[0]
        for escolha in tipos_utilizador
    }

    if (
        tipos_validos
        and tipo_utilizador not in tipos_validos
    ):
        messages.error(
            request,
            "Selecione um tipo de utilizador válido.",
        )

        return render(
            request,
            "inicio/cadastro.html",
            contexto,
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

            perfil_usuario, created = (
                Perfil.objects.get_or_create(
                    user=user,
                    defaults={
                        "provincia": provincia or "Moxico",
                        "tipo_utilizador": (
                            tipo_utilizador or "outro"
                        ),
                    },
                )
            )

            perfil_usuario.telefone = telefone
            perfil_usuario.localizacao = localizacao
            perfil_usuario.municipio = municipio
            perfil_usuario.provincia = (
                provincia or "Moxico"
            )
            perfil_usuario.tipo_utilizador = (
                tipo_utilizador or "outro"
            )

            perfil_usuario.save()

    except IntegrityError:
        username_existe = User.objects.filter(
            username__iexact=username,
        ).exists()

        email_existe = (
            bool(email)
            and User.objects.filter(
                email__iexact=email,
            ).exists()
        )

        if username_existe and email_existe:
            mensagem = (
                "O nome de utilizador e o e-mail "
                "já estão registados."
            )
        elif username_existe:
            mensagem = (
                f"O nome de utilizador '{username}' "
                "já está registado."
            )
        elif email_existe:
            mensagem = (
                f"O e-mail '{email}' "
                "já está registado."
            )
        else:
            mensagem = (
                "Não foi possível criar a conta devido "
                "a uma restrição da base de dados."
            )

        messages.error(
            request,
            mensagem,
        )

        return render(
            request,
            "inicio/cadastro.html",
            contexto,
        )

    except Exception as e:
        print(
            "ERRO REAL NO CADASTRO:",
            repr(e),
        )

        messages.error(
            request,
            "Ocorreu um erro ao criar a conta. Tente novamente.",
        )

        return render(
            request,
            "inicio/cadastro.html",
            contexto,
        )

    login(
        request,
        user,
    )

    messages.success(
        request,
        "Conta criada com sucesso! Bem-vindo ao AgroIA Moxico.",
    )

    return redirect("inicio:perfil")


@login_required
def perfil(request):
    perfil_usuario = obter_perfil_usuario(
        request.user,
    )

    diagnosticos_usuario = (
        Diagnostico.objects
        .filter(
            usuario=request.user,
        )
    )

    total_diagnosticos = (
        diagnosticos_usuario.count()
    )

    try:
        diagnosticos_concluidos = (
            diagnosticos_usuario
            .filter(
                status="concluido",
            )
            .count()
        )
    except FieldError:
        diagnosticos_concluidos = 0

    produtos_usuario = (
        ProdutoAgricola.objects
        .filter(
            usuario=request.user,
        )
    )

    total_produtos = (
        produtos_usuario.count()
    )

    total_produtos_ativos = (
        produtos_usuario
        .filter(
            ativo=True,
        )
        .count()
    )

    try:
        total_produtos_analise = (
            produtos_usuario
            .filter(
                ativo=True,
                analise_por_imagem=True,
            )
            .count()
        )
    except FieldError:
        total_produtos_analise = 0

    contexto = {
        "perfil": perfil_usuario,
        "perfil_usuario": perfil_usuario,
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
        request.user,
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
            try:
                with transaction.atomic():
                    user_form.save()
                    perfil_form.save()

                messages.success(
                    request,
                    "O seu perfil foi atualizado com sucesso.",
                )

                return redirect(
                    "inicio:perfil",
                )

            except Exception as e:
                print(
                    "ERRO AO ATUALIZAR PERFIL:",
                    repr(e),
                )

                messages.error(
                    request,
                    "Não foi possível atualizar o perfil. Tente novamente.",
                )

        else:
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
        "perfil_usuario": perfil_usuario,
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
            "inicio:perfil",
        )

    perfil_usuario = obter_perfil_usuario(
        request.user,
    )

    if perfil_usuario.foto:
        perfil_usuario.foto.delete(
            save=False,
        )

        perfil_usuario.foto = None

        try:
            perfil_usuario.save(
                update_fields=[
                    "foto",
                    "data_atualizacao",
                ],
            )
        except FieldError:
            perfil_usuario.save()

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
        "inicio:perfil",
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
        "produtos/produtos.html",
        contexto,
    )


@login_required
def detalhe_produto(request, pk):
    produto = get_object_or_404(
        ProdutoAgricola.objects.prefetch_related(
            "categorias",
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
        "produtos/detalhe_produto.html",
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
        try:
            produtos_lista = (
                produtos_lista
                .filter(
                    Q(nome__icontains=termo)
                    | Q(descricao__icontains=termo)
                    | Q(problemas__icontains=termo)
                    | Q(categorias__nome__icontains=termo)
                )
                .distinct()
            )

        except FieldError:
            produtos_lista = (
                produtos_lista
                .filter(
                    Q(nome__icontains=termo)
                    | Q(descricao__icontains=termo)
                    | Q(categorias__nome__icontains=termo)
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
