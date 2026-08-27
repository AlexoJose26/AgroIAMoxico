from django import forms

from categorias.models import Categoria
from .models import ProdutoAgricola


class ProdutoForm(forms.ModelForm):

    categorias = forms.ModelMultipleChoiceField(
        queryset=Categoria.objects.filter(
            ativo=True
        ).order_by("nome"),
        required=False,
        widget=forms.CheckboxSelectMultiple(
            attrs={
                "class": "categoria-checkbox"
            }
        ),
        label="Categorias",
    )

    class Meta:
        model = ProdutoAgricola

        fields = [
            "nome",
            "descricao",
            "categorias",
            "imagem",
            "problemas",
            "analise_por_imagem",
            "ativo",
        ]

        widgets = {
            "nome": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ex.: Milho",
                }
            ),

            "descricao": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "Descreva o produto agrícola..."
                    ),
                    "rows": 5,
                }
            ),

            "imagem": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/*",
                }
            ),

            "problemas": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "Indique doenças, pragas ou problemas "
                        "que podem afetar esta cultura..."
                    ),
                    "rows": 5,
                }
            ),

            "analise_por_imagem": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),

            "ativo": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

        labels = {
            "nome": "Nome do produto",
            "descricao": "Descrição",
            "imagem": "Imagem",
            "problemas": "Problemas / doenças",
            "analise_por_imagem": "Permitir análise por imagem",
            "ativo": "Disponível no catálogo",
        }

        help_texts = {
            "categorias": (
                "Selecione uma ou mais categorias para este produto."
            ),
            "analise_por_imagem": (
                "Permite utilizar este produto no diagnóstico por imagem."
            ),
            "ativo": (
                "Produtos ativos aparecem como disponíveis no catálogo."
            ),
        }
