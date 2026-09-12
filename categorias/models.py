from django.db import models


class Categoria(models.Model):
    nome = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nome da categoria",
    )

    descricao = models.TextField(
        blank=True,
        null=True,
        verbose_name="Descrição",
    )

    ativo = models.BooleanField(
        default=True,
        verbose_name="Categoria ativa",
    )

    criado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em",
    )

    atualizado_em = models.DateTimeField(
        auto_now=True,
        verbose_name="Atualizado em",
    )

    class Meta:
        ordering = ["nome"]
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"
        indexes = [
            models.Index(
                fields=["nome"],
                name="categoria_nome_idx",
            ),
            models.Index(
                fields=["ativo"],
                name="categoria_ativo_idx",
            ),
            models.Index(
                fields=["-criado_em"],
                name="categoria_criado_idx",
            ),
        ]

    def __str__(self):
        return self.nome

    @property
    def total_produtos(self):
        return self.produtos.count()

    @property
    def total_produtos_ativos(self):
        return self.produtos.filter(
            ativo=True
        ).count()

    @property
    def total_produtos_inativos(self):
        return self.produtos.filter(
            ativo=False
        ).count()

    @property
    def tem_produtos(self):
        return self.produtos.exists()

    @property
    def tem_produtos_ativos(self):
        return self.produtos.filter(
            ativo=True
        ).exists()

    @property
    def quantidade_produtos(self):
        return self.total_produtos

    @property
    def quantidade_produtos_ativos(self):
        return self.total_produtos_ativos
