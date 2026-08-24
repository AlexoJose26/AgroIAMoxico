from django.contrib import admin

from .models import Diagnostico


@admin.register(Diagnostico)
class DiagnosticoAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "usuario",
        "produto",
        "resultado",
        "confianca",
        "status",
        "data_criacao",
    )

    list_filter = (
        "status",
        "resultado",
        "data_criacao",
    )

    search_fields = (
        "usuario__username",
        "usuario__first_name",
        "usuario__last_name",
        "produto__nome",
        "doenca_identificada",
    )

    readonly_fields = (
        "data_criacao",
        "data_atualizacao",
    )

    ordering = (
        "-data_criacao",
    )
