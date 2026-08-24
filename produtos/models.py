from django.conf import settings
from django.db import models


class ProdutoAgricola(models.Model):

    nome = models.CharField(
        max_length=150,
        verbose_name="Nome do produto",
    )

    descricao = models.TextField(
        blank=True,
        null=True,
        verbose_name="Descrição",
    )

    categorias = models.ManyToManyField(
        "categorias.Categoria",
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
        null=True,
        verbose_name="Problemas",
    )

    analise_por_imagem = models.BooleanField(
        default=False,
        verbose_name="Análise por imagem",
    )

    ativo = models.BooleanField(
        default=True,
        verbose_name="Produto ativo",
    )

    # ============================================================
    # UTILIZADOR QUE CADASTROU O PRODUTO
    # ============================================================

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="produtos_agricolas",
        verbose_name="Utilizador",
    )

    # ============================================================
    # DATAS
    # ============================================================

    criado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em",
    )

    atualizado_em = models.DateTimeField(
        auto_now=True,
        verbose_name="Atualizado em",
    )

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "Produto agrícola"
        verbose_name_plural = "Produtos agrícolas"

        indexes = [
            models.Index(fields=["nome"]),
            models.Index(fields=["ativo"]),
            models.Index(fields=["analise_por_imagem"]),
            models.Index(fields=["usuario"]),
            models.Index(fields=["-criado_em"]),
        ]

    def __str__(self):
        return self.nome

    @property
    def tem_imagem(self):
        return bool(self.imagem)

    @property
    def pode_ser_analisado(self):
        return self.ativo and self.analise_por_imagem

    @property
    def nome_categorias(self):
        return ", ".join(
            categoria.nome
            for categoria in self.categorias.all()
        )
