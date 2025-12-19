from django.db import models

class TransicaoFinanceira(models.Model):
    tipo = models.CharField(
        max_length = 10,
        choices = [('ENTRADA', 'Entrada'), ('SAIDA', 'Saída')],
        verbose_name = "Tipo de Transição"
    )
    
    valor = models.DecimalField(
        max_digits = 10,
        decimal_places = 2,
        verbose_name = "Valor (R$)"
    )
    
    data_hora = models.DateTimeField(
        auto_now_add = True,
        verbose_name = "Data e Hora"
    )
    
    descricao = models.TextField(
        verbose_name = "Descrição"
    )

    class Meta:
        verbose_name = "Transição Financeira"
        verbose_name_plural = "Transições Financeiras"
    
    def __str__(self):
        return f"{self.tipo} - R$ {self.valor} em {self.data_hora}"

