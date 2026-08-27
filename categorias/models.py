from django.db import models


class Categoria(models.Model):
    """
    Representa uma categoria agrícola do AgroIA Moxico.

    Uma categoria pode estar associada a vários produtos através
    do relacionamento ManyToMany definido em ProdutoAgricola.
    """

    # ============================================================
    # INFORMAÇÕES PRINCIPAIS
    # ============================================================

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

    # ============================================================
    # ESTADO DA CATEGORIA
    # ============================================================

    ativo = models.BooleanField(
        default=True,
        verbose_name="Categoria ativa",
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

    # ============================================================
    # CONFIGURAÇÕES DO MODELO
    # ============================================================

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

    # ============================================================
    # REPRESENTAÇÃO
    # ============================================================

    def __str__(self):
        return self.nome

    # ============================================================
    # PROPRIEDADES — PRODUTOS
    # ============================================================

    @property
    def total_produtos(self):
        """
        Retorna a quantidade total de produtos
        associados à categoria.
        """
        return self.produtos.count()

    @property
    def total_produtos_ativos(self):
        """
        Retorna a quantidade de produtos ativos
        associados à categoria.
        """
        return self.produtos.filter(
            ativo=True
        ).count()

    @property
    def total_produtos_inativos(self):
        """
        Retorna a quantidade de produtos inativos
        associados à categoria.
        """
        return self.produtos.filter(
            ativo=False
        ).count()

    @property
    def tem_produtos(self):
        """
        Indica se existe pelo menos um produto
        associado à categoria.
        """
        return self.produtos.exists()

    @property
    def tem_produtos_ativos(self):
        """
        Indica se existe pelo menos um produto ativo
        associado à categoria.
        """
        return self.produtos.filter(
            ativo=True
        ).exists()

    @property
    def quantidade_produtos(self):
        """
        Alias amigável para utilização nos templates.
        """
        return self.total_produtos

    @property
    def quantidade_produtos_ativos(self):
        """
        Alias para quantidade de produtos ativos.
        """
        return self.total_produtos_ativos
