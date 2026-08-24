from django.db import models


class Categoria(models.Model):

    nome = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nome da categoria"
    )

    descricao = models.TextField(
        blank=True,
        null=True,
        verbose_name="Descrição"
    )

    ativo = models.BooleanField(
        default=True,
        verbose_name="Categoria ativa"
    )

    criado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em"
    )

    atualizado_em = models.DateTimeField(
        auto_now=True,
        verbose_name="Atualizado em"
    )

    class Meta:
        ordering = ["nome"]
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"

    def __str__(self):
        return self.nome
