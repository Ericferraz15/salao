from ..models import Servico, Funcionario, JornadaTrabalho, Agendamento
from datetime import timedelta , datetime
from django.core.exceptions import ValidationError

def verificar_disponibilidade(profissionalId,servicoId, hora_de_inicio,ignorar_agendamento_id=None)-> None:
    try:
        servico = Servico.objects.get(id=servicoId)
        funcionario = Funcionario.objects.get(id = profissionalId)
    except (Servico.DoesNotExist, Funcionario.DoesNotExist):
        raise ValidationError("Serviço ou Funcionario não encontrado.")

    duracao_servico = timedelta(minutes=servico.duracao_minutos)
    hora_fim = hora_de_inicio + duracao_servico
    dia_semana = hora_de_inicio.weekday()

    jornada_Funcionario = JornadaTrabalho.objects.filter(
        funcionario=funcionario,
        dia_da_semana=dia_semana,
    ).first()

    if not jornada_Funcionario:
        raise ValidationError("Funcionário não trabalha neste dia.")

    hora_de_inicio_jornada = datetime(
        hora_de_inicio.year,
        hora_de_inicio.month,
        hora_de_inicio.day,
        jornada_Funcionario.hora_inicio.hour,
        jornada_Funcionario.hora_inicio.minute
        )
    
    hora_de_fim_jornada = datetime(
        hora_de_inicio.year,
        hora_de_inicio.month,
        hora_de_inicio.day,
        jornada_Funcionario.hora_fim.hour,
        jornada_Funcionario.hora_fim.minute
        )

    if not (hora_de_inicio >= hora_de_inicio_jornada and hora_fim <= hora_de_fim_jornada):
        raise ValidationError("Agendamento fora do horário de trabalho do funcionário.")

    conflitos_query = Agendamento.objects.filter(
        profissional=funcionario,
        hora_de_inicio__lt=hora_fim,
        hora_de_fim__gt=hora_de_inicio
    )

    if ignorar_agendamento_id:
        conflitos_query = conflitos_query.exclude(id=ignorar_agendamento_id)
    if conflitos_query.exists():
        raise ValidationError("Conflito de agendamento para o profissional neste horário.")

def criar_agendamento(profissionalId, servicoId, clienteId, hora_de_inicio)-> Agendamento:
    verificar_disponibilidade(profissionalId, servicoId, hora_de_inicio)

    servico = Servico.objects.get(id=servicoId)
    funcionario = Funcionario.objects.get(id=profissionalId)

    duracao_servico = timedelta(minutes=servico.duracao_minutos)
    hora_fim = hora_de_inicio + duracao_servico

    try:
        response =Agendamento.objects.create(
        profissional=funcionario,
        servico=servico,
        cliente_id=clienteId,
        hora_de_inicio=hora_de_inicio,
        hora_de_fim=hora_fim
    )
    except Exception as e:
        raise ValidationError(f"Erro ao criar agendamento: {str(e)}")
    return response

def listar_agendamentos(clienteId):
    agendamentos = Agendamento.objects.filter(cliente_id=clienteId).order_by('data_hora_inicio')
    return agendamentos

def cancelar_agendamento(agendamentoId) -> bool: 
    try:
        agendamento = Agendamento.objects.get(id=agendamentoId)
        agendamento.delete()
        return True
    except Agendamento.DoesNotExist:
        raise ValidationError("Agendamento não encontrado.")

def editar_agendamento(agendamentoId, novo_profissionalId, novo_servicoId, nova_hora_de_inicio)-> bool:
    try:
        agendamento = Agendamento.objects.get(id=agendamentoId)
    except Agendamento.DoesNotExist:
        raise ValidationError("Agendamento não encontrado.")
        
    try:
        verificar_disponibilidade(novo_profissionalId, novo_servicoId, nova_hora_de_inicio, ignorar_agendamento_id=agendamentoId)
        servico = Servico.objects.get(id=novo_servicoId)
        funcionario = Funcionario.objects.get(id=novo_profissionalId)

        duracao_servico = timedelta(minutes=servico.duracao_minutos)
        nova_hora_fim = nova_hora_de_inicio + duracao_servico

        agendamento.profissional = funcionario
        agendamento.servico = servico
        agendamento.data_hora_inicio = nova_hora_de_inicio
        agendamento.data_hora_fim = nova_hora_fim
        agendamento.save()
        return True
    except Exception as e:
        raise ValidationError(f"Erro ao editar agendamento: {str(e)}")