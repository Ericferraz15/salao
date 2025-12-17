from dataclasses import dataclass
from decimal import Decimal 
from typing import Optional

@dataclass(frozen=True)
class ProdutoRequestDTO:
    nome: str
    descricao: str
    preco: Decimal
    quantidade_estoque: int
    estoque_minimo: int

@dataclass(frozen=True)
class ProdutoResponseDTO:
    id: int
    nome: str
    descricao: str
    preco: Decimal
    quantidade_estoque: int
    estoque_baixo: bool
    alerta_cor: str

