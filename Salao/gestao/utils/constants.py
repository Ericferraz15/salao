
# Status de Agendamento
STATUS_CHOICES = (
    ('PENDENTE', 'Pendente (Aguardando Confirmação)'),
    ('CONFIRMADO', 'Confirmado'),
    ('CONCLUIDO', 'Concluído (Serviço Pago)'),
    ('CANCELADO', 'Cancelado'),
    ('NO_SHOW', 'Não Compareceu'),
)

DIAS_SEMANA = (
    (1, 'Segunda-feira'),
    (2, 'Terça-feira'),
    (3, 'Quarta-feira'),
    (4, 'Quinta-feira'),
    (5, 'Sexta-feira'),
    (6, 'Sábado'),
    (7, 'Domingo'),
)