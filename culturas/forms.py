from django import forms

from .models import ProdutoAgricola


class ProdutoForm(forms.ModelForm):

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
                    "placeholder": "Ex.: Milho"
                }
            ),

            "descricao": forms.Textarea(
                attrs={
                    "placeholder": (
                        "Descreva as principais características "
                        "e informações agrícolas do produto..."
                    ),
                    "rows": 6,
                    "maxlength": 1000,
                }
            ),

            "categorias": forms.CheckboxSelectMultiple(),

            "imagem": forms.ClearableFileInput(
                attrs={
                    "accept": "image/jpeg,image/png,image/webp"
                }
            ),

            "problemas": forms.Textarea(
                attrs={
                    "placeholder": (
                        "Ex.: doenças, pragas ou problemas "
                        "agrícolas relacionados..."
                    ),
                    "rows": 5,
                }
            ),

            "analise_por_imagem": forms.CheckboxInput(),

            "ativo": forms.CheckboxInput(),
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields["categorias"].queryset = (
            self.fields["categorias"]
            .queryset
            .order_by("nome")
        )

        self.fields["categorias"].required = True
        self.fields["descricao"].required = True
        self.fields["imagem"].required = False
        self.fields["problemas"].required = False
        self.fields["analise_por_imagem"].required = False
        self.fields["ativo"].required = False
