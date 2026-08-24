from django.contrib.auth.models import User
from django.db import models


class Perfil(models.Model):

    # =========================================================
    # TIPOS DE UTILIZADOR
    # =========================================================

    TIPOS_UTILIZADOR = [
        ("agricultor", "Agricultor"),
        ("tecnico", "Técnico Agrícola"),
        ("estudante", "Estudante"),
        ("investigador", "Investigador"),
        ("administrador", "Administrador"),
        ("outro", "Outro"),
    ]

    # =========================================================
    # UTILIZADOR
    # =========================================================

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="perfil",
    )

    # =========================================================
    # INFORMAÇÕES DE CONTACTO
    # =========================================================

    telefone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Telefone",
    )

    # =========================================================
    # LOCALIZAÇÃO
    # =========================================================

    localizacao = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name="Localização",
    )

    municipio = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Município",
    )

    provincia = models.CharField(
        max_length=100,
        default="Moxico",
        blank=True,
        verbose_name="Província",
    )

    # =========================================================
    # TIPO DE UTILIZADOR
    # =========================================================

    tipo_utilizador = models.CharField(
        max_length=30,
        choices=TIPOS_UTILIZADOR,
        default="outro",
        verbose_name="Tipo de utilizador",
    )

    # =========================================================
    # FOTO DE PERFIL
    # =========================================================

    foto = models.ImageField(
        upload_to="perfis/",
        blank=True,
        null=True,
        verbose_name="Foto do perfil",
    )

    # =========================================================
    # DATA DE ATUALIZAÇÃO
    # =========================================================

    data_atualizacao = models.DateTimeField(
        auto_now=True,
    )

    # =========================================================
    # REPRESENTAÇÃO DO OBJETO
    # =========================================================

    def __str__(self):
        return f"Perfil de {self.user.username}"

    # =========================================================
    # NOME COMPLETO
    # =========================================================

    @property
    def nome_completo(self):
        """
        Retorna o nome completo do utilizador.
        """

        nome = self.user.get_full_name().strip()

        if nome:
            return nome

        return self.user.username

    # =========================================================
    # INICIAL DO UTILIZADOR
    # =========================================================

    @property
    def inicial(self):
        """
        Retorna a primeira letra do nome do utilizador.
        """

        nome = self.user.first_name.strip()

        if nome:
            return nome[0].upper()

        return self.user.username[0].upper()
