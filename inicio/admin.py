from django.contrib import admin
from .models import Perfil


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "telefone",
        "municipio",
        "provincia",
        "tipo_utilizador",
        "data_atualizacao",
    )

    list_filter = (
        "tipo_utilizador",
        "provincia",
        "municipio",
    )

    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__email",
        "telefone",
        "municipio",
    )

    readonly_fields = (
        "data_atualizacao",
    )
