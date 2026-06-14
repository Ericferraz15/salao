"""
constants.py

CORREÇÃO CRÍTICA:
DIAS_SEMANA agora usa 0-6 em vez de 1-7.
datetime.weekday() retorna 0 para segunda-feira e 6 para domingo.
O código original usava 1-7, então a query de JornadaTrabalho
nunca encontrava o dia correto — o profissional "nunca trabalhava".

Após gerar uma nova migration, reinsira os dados de JornadaTrabalho
no banco com os novos valores (0-6).
"""

STATUS_CHOICES = (
    ('PENDENTE', 'Pendente (aguardando confirmação)'),
    ('CONFIRMADO', 'Confirmado'),
    ('CONCLUIDO', 'Concluído (serviço pago)'),
    ('CANCELADO', 'Cancelado'),
    ('NO_SHOW', 'Não compareceu'),
)

# CORRIGIDO: 0-6 alinhado com datetime.weekday()
DIAS_SEMANA = (
    (0, 'Segunda-feira'),
    (1, 'Terça-feira'),
    (2, 'Quarta-feira'),
    (3, 'Quinta-feira'),
    (4, 'Sexta-feira'),
    (5, 'Sábado'),
    (6, 'Domingo'),
)
