from django import forms

from .models import Categoria


class CategoriaForm(forms.ModelForm):

    class Meta:

        model = Categoria

        fields = [
            "nome",
            "descricao",
            "ativo",
        ]

        widgets = {

            "nome": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ex.: Cereais",
                }
            ),

            "descricao": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": (
                        "Descreva esta categoria agrícola..."
                    ),
                }
            ),

            "ativo": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

        labels = {
            "nome": "Nome da categoria",
            "descricao": "Descrição",
            "ativo": "Categoria ativa",
        }

    def clean_nome(self):

        nome = self.cleaned_data.get("nome")

        if nome:
            nome = nome.strip()

        if not nome:
            raise forms.ValidationError(
                "Informe o nome da categoria."
            )

        return nome
