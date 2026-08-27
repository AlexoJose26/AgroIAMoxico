from django.contrib import admin

from .models import ProdutoAgricola


@admin.register(ProdutoAgricola)
class ProdutoAgricolaAdmin(admin.ModelAdmin):

    list_display = (
        "nome",
        "categorias_display",
        "ativo",
        "analise_por_imagem",
        "criado_em",
        "atualizado_em",
    )

    list_filter = (
        "ativo",
        "analise_por_imagem",
        "categorias",
        "criado_em",
        "atualizado_em",
    )


    search_fields = (
        "nome",
        "descricao",
        "problemas",
        "categorias__nome",
    )


    readonly_fields = (
        "criado_em",
        "atualizado_em",
    )

    ordering = (
        "-criado_em",
        "nome",
    )

    list_per_page = 25

    fieldsets = (
        (
            "Informações do produto",
            {
                "fields": (
                    "nome",
                    "descricao",
                    "categorias",
                    "imagem",
                )
            },
        ),

        (
            "Diagnóstico e análise",
            {
                "fields": (
                    "problemas",
                    "analise_por_imagem",
                )
            },
        ),

        (
            "Estado do produto",
            {
                "fields": (
                    "ativo",
                )
            },
        ),

        (
            "Informações do sistema",
            {
                "fields": (
                    "criado_em",
                    "atualizado_em",
                )
            },
        ),
    )


    @admin.display(
        description="Categorias"
    )
    def categorias_display(self, obj):

        categorias = obj.categorias.all()

        if not categorias.exists():
            return "Sem categoria"

        return ", ".join(
            categoria.nome
            for categoria in categorias
        )
