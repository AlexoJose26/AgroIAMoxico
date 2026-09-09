from django.contrib.auth.models import User
from django.db import models

from produtos.models import ProdutoAgricola


class Diagnostico(models.Model):
    STATUS_CHOICES = [
        ("pendente", "Pendente"),
        ("processando", "Processando"),
        ("concluido", "Concluído"),
        ("erro", "Erro"),
    ]

    RESULTADO_CHOICES = [
        ("saudavel", "Saudável"),
        ("doenca", "Doença"),
        ("praga", "Praga"),
        ("fungo", "Fungo"),
        ("deficiencia", "Deficiência nutricional"),
        ("outro", "Outro"),
        ("indeterminado", "Indeterminado"),
    ]

    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="diagnosticos",
        verbose_name="Utilizador",
    )

    produto = models.ForeignKey(
        ProdutoAgricola,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="diagnosticos",
        verbose_name="Produto agrícola",
    )

    imagem = models.ImageField(
        upload_to="diagnosticos/%Y/%m/%d/",
        max_length=255,
        verbose_name="Imagem analisada",
    )

    classe_identificada = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Classe identificada pela IA",
    )

    resultado = models.CharField(
        max_length=30,
        choices=RESULTADO_CHOICES,
        default="indeterminado",
        verbose_name="Resultado",
    )

    doenca_identificada = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Doença identificada",
    )

    confianca = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name="Confiança da IA (%)",
    )

    descricao_resultado = models.TextField(
        blank=True,
        verbose_name="Descrição do resultado",
    )

    recomendacoes = models.TextField(
        blank=True,
        verbose_name="Recomendações",
    )

    observacoes = models.TextField(
        blank=True,
        verbose_name="Observações",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pendente",
        verbose_name="Estado",
    )

    erro = models.TextField(
        blank=True,
        verbose_name="Mensagem de erro",
    )

    data_criacao = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data do diagnóstico",
    )

    data_atualizacao = models.DateTimeField(
        auto_now=True,
        verbose_name="Última atualização",
    )

    class Meta:
        verbose_name = "Diagnóstico"
        verbose_name_plural = "Diagnósticos"
        ordering = ["-data_criacao"]

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
