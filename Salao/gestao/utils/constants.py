"""
constants.py — valores fixos usados em vários pontos do sistema.

Centralizar aqui evita "números mágicos" espalhados: quando a regra
mudar (ex.: nova meta), muda-se em um lugar só.
"""

from decimal import Decimal

# Ciclo de vida de um agendamento:
# PENDENTE -> CONFIRMADO -> CONCLUIDO (gera receita)
# e os desvios: CANCELADO, NO_SHOW (cliente faltou).
STATUS_CHOICES = (
    ('PENDENTE', 'Pendente (aguardando confirmação)'),
    ('CONFIRMADO', 'Confirmado'),
    ('CONCLUIDO', 'Concluído (serviço pago)'),
    ('CANCELADO', 'Cancelado'),
    ('NO_SHOW', 'Não compareceu'),
)

# 0-6 alinhado com datetime.weekday() (0=segunda ... 6=domingo).
# Cuidado: usar 1-7 aqui já causou o bug de "profissional nunca trabalha".
DIAS_SEMANA = (
    (0, 'Segunda-feira'),
    (1, 'Terça-feira'),
    (2, 'Quarta-feira'),
    (3, 'Quinta-feira'),
    (4, 'Sexta-feira'),
    (5, 'Sábado'),
    (6, 'Domingo'),
)

# Meta de receita mensal do salão (documento de requisitos: R$ 4.000-5.000).
# O painel admin mostra uma barra de progresso da receita do mês vs. esta meta.
META_RECEITA_MENSAL = Decimal('5000.00')
