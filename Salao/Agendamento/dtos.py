from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

@dataclass(frozen=True)
class AgendamentoRequestDTO:
    cliente_id: int
    profissional_id: int
    servico_id: int
    data_hora_inicio: datetime

@dataclass(frozen=True)
class AgendamentoResponseDTO:
    id: int
    cliente_nome: str
    profissional_nome: str
    servico_nome: str
    inicio: str  
    fim: str
    valor: Decimal
    status_display: str
    cor_status: str  