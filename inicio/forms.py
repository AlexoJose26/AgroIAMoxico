from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .models import Perfil


# ============================================================
# FORMULÁRIO DE ATUALIZAÇÃO DO UTILIZADOR
# ============================================================

class UserUpdateForm(forms.ModelForm):
    """
    Formulário responsável pela atualização
    dos dados básicos da conta do utilizador.
    """

    class Meta:
        model = User

        fields = [
            "first_name",
            "last_name",
            "email",
        ]

        labels = {
            "first_name": "Nome",
            "last_name": "Apelido",
            "email": "E-mail",
        }

        widgets = {
            "first_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Digite o seu nome",
                    "autocomplete": "given-name",
                }
            ),

            "last_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Digite o seu apelido",
                    "autocomplete": "family-name",
                }
            ),

            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Digite o seu e-mail",
                    "autocomplete": "email",
                }
            ),
        }

    # --------------------------------------------------------
    # VALIDAR E-MAIL
    # --------------------------------------------------------

    def clean_email(self):
        email = self.cleaned_data.get("email")

        if not email:
            return email

        email = email.strip().lower()

        # Verifica se já existe outro utilizador
        # com este mesmo e-mail.
        utilizador_existente = (
            User.objects
            .filter(email__iexact=email)
            .exclude(pk=self.instance.pk)
            .first()
        )

        if utilizador_existente:
            raise ValidationError(
                "Este e-mail já está associado a outra conta."
            )

        return email


# ============================================================
# FORMULÁRIO DE ATUALIZAÇÃO DO PERFIL
# ============================================================

class PerfilUpdateForm(forms.ModelForm):
    """
    Formulário responsável pela atualização
    das informações adicionais do perfil.
    """

    class Meta:
        model = Perfil

        fields = [
            "telefone",
            "localizacao",
            "municipio",
            "provincia",
            "tipo_utilizador",
            "foto",
        ]

        labels = {
            "telefone": "Telefone",
            "localizacao": "Localização",
            "municipio": "Município",
            "provincia": "Província",
            "tipo_utilizador": "Tipo de utilizador",
            "foto": "Foto do perfil",
        }

        widgets = {
            # ------------------------------------------------
            # TELEFONE
            # ------------------------------------------------

            "telefone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ex.: 923 000 000",
                    "autocomplete": "tel",
                    "inputmode": "tel",
                }
            ),

            # ------------------------------------------------
            # LOCALIZAÇÃO
            # ------------------------------------------------

            "localizacao": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "Ex.: Bairro, comuna ou localidade"
                    ),
                    "autocomplete": "address-line1",
                }
            ),

            # ------------------------------------------------
            # MUNICÍPIO
            # ------------------------------------------------

            "municipio": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Digite o município",
                }
            ),

            # ------------------------------------------------
            # PROVÍNCIA
            # ------------------------------------------------

            "provincia": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Digite a província",
                }
            ),

            # ------------------------------------------------
            # TIPO DE UTILIZADOR
            # ------------------------------------------------

            "tipo_utilizador": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            # ------------------------------------------------
            # FOTO
            # ------------------------------------------------

            "foto": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/jpeg,image/png,image/webp",
                }
            ),
        }

    # ========================================================
    # VALIDAÇÃO DA FOTO
    # ========================================================

    def clean_foto(self):

        foto = self.cleaned_data.get("foto")

        # Se o utilizador não escolheu uma nova foto,
        # mantém a foto atual.
        if not foto:
            return foto

        # ----------------------------------------------------
        # TAMANHO MÁXIMO
        # ----------------------------------------------------

        tamanho_maximo = 5 * 1024 * 1024  # 5 MB

        if foto.size > tamanho_maximo:
            raise ValidationError(
                "A imagem não pode ultrapassar 5 MB."
            )

        # ----------------------------------------------------
        # TIPO DE IMAGEM
        # ----------------------------------------------------

        tipos_permitidos = [
            "image/jpeg",
            "image/png",
            "image/webp",
        ]

        if foto.content_type not in tipos_permitidos:
            raise ValidationError(
                "Formato de imagem não permitido. "
                "Utilize JPG, PNG ou WEBP."
            )

        return foto
