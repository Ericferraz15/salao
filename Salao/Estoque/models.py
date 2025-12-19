from django.db import models

class Produtos(models.Model):
    nome = models.CharField(
        max_length = 100,
        verbose_name = "Nome do Produto"
    )
    
    descricao = models.TextField(
        verbose_name = "Descrição do Produto"
    )
    
    preco = models.DecimalField(
        max_digits = 10,
        decimal_places = 2,
        verbose_name = "Preço (R$)"
    )
    
    quantidade_estoque = models.PositiveIntegerField(
        verbose_name = "Quantidade em Estoque"
    )

    estoque_minimo = models.PositiveIntegerField(
        verbose_name = "Estoque Mínimo"
    )

    class Meta:
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"

    def __str__(self):
        return self.nome
    