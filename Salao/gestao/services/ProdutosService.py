from decimal import Decimal
from typing import List
from django.db import transaction
from django.core.exceptions import ValidationError
from ..models import Produtos
from ..Mapper.ProdutoMapper import ProdutoMapper
from ..DTOs.ProdutosDTO import ProdutoRequestDTO, ProdutoResponseDTO

def __init__(self):
    self.mapper = ProdutoMapper()

def listar_produtos(self) -> List[ProdutoResponseDTO]:
    produtos = Produtos.objects.all()
    return [self.mapper.to_dto(produto) for produto in produtos]

