from django.contrib.auth.models import User
from django.db import models

from produtos.models import ProdutoAgricola


class Diagnostico(models.Model):
    """
    Regista um diagnóstico realizado através do sistema
    de Visão Computacional do AgroIA Moxico.
    """

    # ============================================================
    # ESTADOS
    # ============================================================

    STATUS_CHOICES = [
        ("pendente", "Pendente"),
        ("processando", "Processando"),
        ("concluido", "Concluído"),
        ("erro", "Erro"),
    ]

    # ============================================================
    # RESULTADOS
    # ============================================================

    RESULTADO_CHOICES = [
        ("saudavel", "Saudável"),
        ("doenca", "Doença"),
        ("praga", "Praga"),
        ("fungo", "Fungo"),
        ("deficiencia", "Deficiência nutricional"),
        ("outro", "Outro"),
        ("indeterminado", "Indeterminado"),
    ]

    # ============================================================
    # UTILIZADOR
    # ============================================================

    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="diagnosticos",
        verbose_name="Utilizador",
    )

    # ============================================================
    # PRODUTO AGRÍCOLA
    # ============================================================

    produto = models.ForeignKey(
        ProdutoAgricola,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="diagnosticos",
        verbose_name="Produto agrícola",
    )

    # ============================================================
    # IMAGEM
    # ============================================================

    imagem = models.ImageField(
        upload_to="diagnosticos/%Y/%m/%d/",
        verbose_name="Imagem analisada",
    )

    # ============================================================
    # CLASSE DETETADA PELA IA
    # ============================================================

    classe_identificada = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Classe identificada pela IA",
    )

    # ============================================================
    # RESULTADO
    # ============================================================

    resultado = models.CharField(
        max_length=30,
        choices=RESULTADO_CHOICES,
        default="indeterminado",
        verbose_name="Resultado",
    )

    # ============================================================
    # DOENÇA
    # ============================================================

    doenca_identificada = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Doença identificada",
    )

    # ============================================================
    # CONFIANÇA
    # ============================================================

    confianca = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name="Confiança da IA (%)",
    )

    # ============================================================
    # DESCRIÇÃO
    # ============================================================

    descricao_resultado = models.TextField(
        blank=True,
        verbose_name="Descrição do resultado",
    )

    # ============================================================
    # RECOMENDAÇÕES
    # ============================================================

    recomendacoes = models.TextField(
        blank=True,
        verbose_name="Recomendações",
    )

    # ============================================================
    # OBSERVAÇÕES
    # ============================================================

    observacoes = models.TextField(
        blank=True,
        verbose_name="Observações",
    )

    # ============================================================
    # STATUS
    # ============================================================

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pendente",
        verbose_name="Estado",
    )

    # ============================================================
    # ERRO
    # ============================================================

    erro = models.TextField(
        blank=True,
        verbose_name="Mensagem de erro",
    )

    # ============================================================
    # DATAS
    # ============================================================

    data_criacao = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data do diagnóstico",
    )

    data_atualizacao = models.DateTimeField(
        auto_now=True,
        verbose_name="Última atualização",
    )

    # ============================================================
    # META
    # ============================================================

    class Meta:
        verbose_name = "Diagnóstico"
        verbose_name_plural = "Diagnósticos"
        ordering = ["-data_criacao"]

    # ============================================================
    # STR
    # ============================================================

    def __str__(self):
        if self.produto:
            return (
                f"{self.usuario.username} - "
                f"{self.produto.nome} - "
                f"Diagnóstico #{self.pk}"
            )

        return (
            f"{self.usuario.username} - "
            f"Diagnóstico #{self.pk}"
        )

    # ============================================================
    # PROPRIEDADES
    # ============================================================

    @property
    def confianca_formatada(self):
        return f"{float(self.confianca):.2f}%"

    @property
    def resultado_legivel(self):
        return self.get_resultado_display()

    @property
    def esta_concluido(self):
        return self.status == "concluido"

    @property
    def tem_erro(self):
        return self.status == "erro"
