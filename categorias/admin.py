from django.contrib import admin

from .models import Categoria


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):

    # ============================================================
    # LISTAGEM
    # ============================================================

    list_display = (
        "nome",
        "ativo",
        "quantidade_produtos",
        "criado_em",
        "atualizado_em",
    )

    # ============================================================
    # FILTROS
    # ============================================================

    list_filter = (
        "ativo",
        "criado_em",
        "atualizado_em",
    )

    # ============================================================
    # PESQUISA
    # ============================================================

    search_fields = (
        "nome",
        "descricao",
    )

    # ============================================================
    # CAMPOS SOMENTE LEITURA
    # ============================================================

    readonly_fields = (
        "criado_em",
        "atualizado_em",
        "quantidade_produtos",
    )

    # ============================================================
    # ORDENAÇÃO
    # ============================================================

    ordering = (
        "-criado_em",
        "nome",
    )

    # ============================================================
    # PAGINAÇÃO
    # ============================================================

    list_per_page = 25

    # ============================================================
    # CAMPOS DO FORMULÁRIO DO ADMIN
    # ============================================================

    fieldsets = (
        (
            "Informações da categoria",
            {
                "fields": (
                    "nome",
                    "descricao",
                    "ativo",
                )
            },
        ),

        (
            "Informações do sistema",
            {
                "fields": (
                    "quantidade_produtos",
                    "criado_em",
                    "atualizado_em",
                )
            },
        ),
    )

    # ============================================================
    # QUANTIDADE DE PRODUTOS
    # ============================================================

    @admin.display(
        description="Produtos"
    )
    def quantidade_produtos(self, obj):

        return obj.produtos.count()
