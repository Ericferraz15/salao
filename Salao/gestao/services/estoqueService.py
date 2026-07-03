"""
estoqueService.py — regras de negócio do ESTOQUE de produtos.

O cadastro em si é um ModelForm simples (ProdutoForm); aqui fica a
operação com regra de verdade: ajustar a quantidade sem deixar o
estoque negativo, de forma segura contra cliques simultâneos.
"""

from django.core.exceptions import ValidationError
from django.db import transaction

# pyrefly: ignore [missing-import]
from ..models import Produto


def ajustar_estoque(produto_id: int, delta: int) -> Produto:
    """Soma `delta` à quantidade (use delta negativo para dar baixa).

    select_for_update tranca a linha do produto durante o ajuste: dois
    cliques ao mesmo tempo não "perdem" um dos ajustes (read-modify-write
    sem lock poderia gravar por cima). No SQLite o lock é no-op, mas a
    escrita já é serializada; no PostgreSQL ele vale de verdade.
    """
    with transaction.atomic():
        try:
            produto = Produto.objects.select_for_update().get(id=produto_id)
        except Produto.DoesNotExist:
            raise ValidationError('Produto não encontrado.')

        nova_quantidade = produto.quantidade_estoque + delta
        if nova_quantidade < 0:
            raise ValidationError(
                f'Estoque insuficiente: "{produto.nome}" tem só '
                f'{produto.quantidade_estoque} unidade(s).'
            )

        produto.quantidade_estoque = nova_quantidade
        produto.save(update_fields=['quantidade_estoque'])
    return produto
