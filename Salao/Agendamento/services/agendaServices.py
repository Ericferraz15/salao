from datetime import timedelta, datetime
from django.db import transaction
from django.core.exceptions import ValidationError
from ..models import *
from ..dtos import AgendamentoRequestDTO, AgendamentoResponseDTO
from ..mapper import AgendamentoMapper

class AgendamentoService:
    def __init__(self):
        self.mapper = AgendamentoMapper()

    def verificar_disponibilidade(self, profissional_id, servico_id, data_inicio, ignorar_id=None):
        servico = Servico.objects.get(id=servico_id)
        duracao = timedelta(minutes=servico.duracao_minutos)
        data_fim = data_inicio + duracao
        jornada = JornadaTrabalho.objects.filter(
            funcionario_id=profissional_id,
            dia_da_semana=data_inicio.weekday()
        ).first()
        if not jornada:
            raise ValidationError("Funcionário não trabalha neste dia.")
        inicio_jornada = data_inicio.replace(hour=jornada.hora_inicio.hour, minute=jornada.hora_inicio.minute)
        fim_jornada = data_inicio.replace(hour=jornada.hora_fim.hour, minute=jornada.hora_fim.minute)
        if not (data_inicio >= inicio_jornada and data_fim <= fim_jornada):
            raise ValidationError("Fora do horário de expediente do profissional.")
        conflitos = Agendamento.objects.filter(
            profissional_id=profissional_id,
            data_hora_inicio__lt=data_fim,
            data_hora_fim__gt=data_inicio
        ).exclude(status='CANCELADO')
        if ignorar_id:
            conflitos = conflitos.exclude(id=ignorar_id)
        if conflitos.exists():
            raise ValidationError("Já existe um agendamento para este profissional neste horário.")

    @transaction.atomic
    def criar(self, dto: AgendamentoRequestDTO) -> AgendamentoResponseDTO:
        self.verificar_disponibilidade(dto.profissional_id, dto.servico_id, dto.data_hora_inicio)    
        servico = Servico.objects.get(id=dto.servico_id)
        data_fim = dto.data_hora_inicio + timedelta(minutes=servico.duracao_minutos)
        agendamento = Agendamento.objects.create(
            cliente_id=dto.cliente_id,
            profissional_id=dto.profissional_id,
            servico=servico,
            data_hora_inicio=dto.data_hora_inicio,
            data_hora_fim=data_fim,
            valor_cobrado=servico.preco
        )
        return self.mapper.to_dto(agendamento)

    def listar_por_cliente(self, cliente_id: int) -> list[AgendamentoResponseDTO]:
        agendamentos = Agendamento.objects.filter(cliente__usuario_id=cliente_id).order_by('data_hora_inicio')
        return [self.mapper.to_dto(horarios) for horarios in agendamentos]

    @transaction.atomic
    def cancelar(self, agendamento_id: int) -> None:
        try:
            agendamento = Agendamento.objects.get(id=agendamento_id)
            if agendamento.status == 'CONCLUIDO':
                raise ValidationError("Não é possível cancelar um agendamento já concluído.")
            agendamento.status = 'CANCELADO'
            agendamento.save()
        except Agendamento.DoesNotExist:
            raise ValidationError("Agendamento não encontrado.")