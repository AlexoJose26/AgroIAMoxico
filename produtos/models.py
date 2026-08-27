from django.conf import settings
from django.db import models

from categorias.models import Categoria


class ProdutoAgricola(models.Model):
    nome = models.CharField(
        max_length=150,
        unique=True,
        verbose_name="Nome do produto",
    )

    descricao = models.TextField(
        blank=True,
        default="",
        verbose_name="Descrição",
    )

    categorias = models.ManyToManyField(
        Categoria,
        related_name="produtos",
        blank=True,
        verbose_name="Categorias",
    )

    imagem = models.ImageField(
        upload_to="produtos/",
        blank=True,
        null=True,
        verbose_name="Imagem",
    )

    problemas = models.TextField(
        blank=True,
        default="",
        verbose_name="Problemas / doenças",
    )

    analise_por_imagem = models.BooleanField(
        default=True,
        verbose_name="Permitir análise por imagem",
    )

    ativo = models.BooleanField(
        default=True,
        verbose_name="Disponível no catálogo",
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="produtos_agricolas",
        verbose_name="Utilizador",
    )

    criado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data de criação",
    )

    atualizado_em = models.DateTimeField(
        auto_now=True,
        verbose_name="Última atualização",
    )

    class Meta:
        ordering = ["nome"]
        verbose_name = "Produto agrícola"
        verbose_name_plural = "Produtos agrícolas"

    def __str__(self):
        return self.nome
