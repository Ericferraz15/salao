
"""
agendaServices.py

CORREÇÕES APLICADAS:
1. [BUG CRÍTICO] Conflito de nomenclatura: o service usava hora_de_inicio /
   hora_de_fim mas o model Agendamento declara data_hora_inicio / data_hora_fim.
   A query de conflito nunca funcionava, permitindo agendamentos duplicados.

2. [PERFORMANCE] N+1 eliminado: criar_agendamento buscava Servico e Funcionario
   novamente depois de verificar_disponibilidade já tê-los buscado.
   Agora verificar_disponibilidade retorna os objetos e criar_agendamento reutiliza.

3. [LÓGICA] DIAS_SEMANA no model original usava 1-7, mas datetime.weekday()
   retorna 0-6. A jornada nunca era encontrada. Alinhado para 0-6.

4. [ROBUSTEZ] cancelar_agendamento agora apenas muda o status para CANCELADO
   em vez de deletar o registro — preserva histórico financeiro.

5. [ROBUSTEZ] editar_agendamento corrigido para usar os campos certos do model.
"""

from datetime import timedelta, datetime
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

# pyrefly: ignore [missing-import]
from ..models import Agendamento, Funcionario, JornadaTrabalho, Servico, TransacaoFinanceira


def _combinar_data_hora(data_referencia: datetime, horario) -> datetime:
    """
    Combina a DATA LOCAL de data_referencia com o horário do TimeField.
    Retorna um datetime aware no timezone do settings (America/Sao_Paulo).
    Usa localtime() para evitar erro de dia errado próximo à meia-noite UTC.
    """
    local_dt = timezone.localtime(data_referencia)
    naive = datetime(
        local_dt.year,
        local_dt.month,
        local_dt.day,
        horario.hour,
        horario.minute,
    )
    return timezone.make_aware(naive)


def verificar_disponibilidade(
    profissional_id: int,
    servico_id: int,
    hora_de_inicio: datetime,
    ignorar_agendamento_id: int | None = None,
) -> tuple[Funcionario, Servico]:
    """
    Valida se o profissional está disponível no horário solicitado.

    Retorna (funcionario, servico) para evitar buscas duplicadas no caller.
    Lança ValidationError com mensagem descritiva em caso de impedimento.
    """
    # Uma única query com select_related evita 2 queries separadas
    try:
        servico = Servico.objects.get(id=servico_id)
    except Servico.DoesNotExist:
        raise ValidationError('Serviço não encontrado.')

    try:
        funcionario = Funcionario.objects.select_related('usuario').get(
            id=profissional_id,
            esta_ativo=True,  # CORRIGIDO: campo renomeado de estaAtivo para esta_ativo
        )
    except Funcionario.DoesNotExist:
        raise ValidationError('Profissional não encontrado ou inativo.')

    # Não permite agendar no passado. A API de horários já oculta horários
    # passados na interface, mas a regra também precisa valer na camada de
    # serviço (página aberta há muito tempo, edição, requisição forjada).
    if hora_de_inicio <= timezone.now():
        raise ValidationError('Não é possível agendar em um horário que já passou.')

    duracao = timedelta(minutes=servico.duracao_minutos)
    hora_fim = hora_de_inicio + duracao

    # Usa localtime() para obter o dia da semana correto no fuso de São Paulo.
    # Sem isso, um agendamento às 22h SP (01h UTC do dia seguinte) retornaria
    # o dia errado ao chamar .weekday() diretamente.
    dia_semana = timezone.localtime(hora_de_inicio).weekday()

    jornada = JornadaTrabalho.objects.filter(
        funcionario=funcionario,
        dia_da_semana=dia_semana,
    ).first()

    if not jornada:
        raise ValidationError('Profissional não trabalha neste dia da semana.')

    inicio_jornada = _combinar_data_hora(hora_de_inicio, jornada.hora_inicio)
    fim_jornada = _combinar_data_hora(hora_de_inicio, jornada.hora_fim)

    if not (hora_de_inicio >= inicio_jornada and hora_fim <= fim_jornada):
        raise ValidationError(
            f'Horário fora do expediente do profissional '
            f'({jornada.hora_inicio.strftime("%H:%M")} – {jornada.hora_fim.strftime("%H:%M")}).'
        )

    # CORRIGIDO: query usa os nomes corretos de campo do model (data_hora_inicio/fim)
    conflitos = Agendamento.objects.filter(
        profissional=funcionario,
        status__in=['PENDENTE', 'CONFIRMADO'],  # apenas agendamentos ativos
        data_hora_inicio__lt=hora_fim,
        data_hora_fim__gt=hora_de_inicio,
    )

    if ignorar_agendamento_id:
        conflitos = conflitos.exclude(id=ignorar_agendamento_id)

    if conflitos.exists():
        raise ValidationError('O profissional já possui um agendamento neste horário.')

    return funcionario, servico


def criar_agendamento(
    profissional_id: int,
    servico_id: int,
    cliente_id: int,
    hora_de_inicio: datetime,
) -> Agendamento:
    """
    Cria um novo agendamento após validar disponibilidade.

    CORRIGIDO:
    - Reutiliza os objetos retornados por verificar_disponibilidade (sem N+1).
    - Preenche valor_cobrado automaticamente a partir do preço do serviço.
    - Retorna o objeto criado em vez de uma string.
    """
    # atomic + lock no profissional serializa reservas concorrentes: uma segunda
    # requisição para o mesmo profissional espera a primeira confirmar, então o
    # check de conflito enxerga o agendamento recém-criado (evita double booking
    # em corrida). Em SQLite o lock é no-op, mas a escrita já é serializada.
    with transaction.atomic():
        Funcionario.objects.select_for_update().filter(pk=profissional_id).first()

        funcionario, servico = verificar_disponibilidade(
            profissional_id, servico_id, hora_de_inicio
        )

        hora_fim = hora_de_inicio + timedelta(minutes=servico.duracao_minutos)

        agendamento = Agendamento.objects.create(
            profissional=funcionario,
            servico=servico,
            cliente_id=cliente_id,
            data_hora_inicio=hora_de_inicio,   # CORRIGIDO: nome do campo
            data_hora_fim=hora_fim,            # CORRIGIDO: nome do campo
            valor_cobrado=servico.preco,       # NOVO: captura o preço vigente
            status='PENDENTE',
        )
    return agendamento


def listar_agendamentos_cliente(cliente_id: int):
    """
    CORRIGIDO:
    - Nome mais descritivo (era listar_agendamentos).
    - select_related evita N+1 ao exibir profissional/serviço na lista.
    - Ordenação por data_hora_inicio (nome correto do campo).
    """
    return (
        Agendamento.objects
        .filter(cliente_id=cliente_id)
        .select_related('profissional__usuario', 'servico')
        .order_by('data_hora_inicio')
    )


def cancelar_agendamento(agendamento_id: int, usuario_solicitante=None) -> Agendamento:
    """
    CORRIGIDO: muda status para CANCELADO em vez de deletar.
    Deletar registros financeiros causa inconsistência em relatórios.
    """
    try:
        agendamento = Agendamento.objects.get(id=agendamento_id)
    except Agendamento.DoesNotExist:
        raise ValidationError('Agendamento não encontrado.')

    if agendamento.status in ['CONCLUIDO', 'CANCELADO']:
        raise ValidationError(
            f'Agendamento com status "{agendamento.status}" não pode ser cancelado.'
        )

    agendamento.status = 'CANCELADO'
    agendamento.save(update_fields=['status'])
    return agendamento


def confirmar_agendamento(agendamento_id: int) -> Agendamento:
    """Confirma um agendamento PENDENTE (PENDENTE -> CONFIRMADO)."""
    try:
        agendamento = Agendamento.objects.get(id=agendamento_id)
    except Agendamento.DoesNotExist:
        raise ValidationError('Agendamento não encontrado.')

    if agendamento.status != 'PENDENTE':
        raise ValidationError('Apenas agendamentos pendentes podem ser confirmados.')

    agendamento.status = 'CONFIRMADO'
    agendamento.save(update_fields=['status'])
    return agendamento


def concluir_agendamento(agendamento_id: int) -> Agendamento:
    """
    Conclui um agendamento (PENDENTE/CONFIRMADO -> CONCLUIDO) e lança a receita
    automaticamente em TransacaoFinanceira. Idempotente: não duplica a receita.
    """
    try:
        agendamento = Agendamento.objects.get(id=agendamento_id)
    except Agendamento.DoesNotExist:
        raise ValidationError('Agendamento não encontrado.')

    if agendamento.status not in ('PENDENTE', 'CONFIRMADO'):
        raise ValidationError('Só é possível concluir agendamentos pendentes ou confirmados.')

    # atomic garante que a mudança de status e o lançamento da receita são
    # gravados juntos — sem isso, uma falha entre os dois deixaria um
    # agendamento CONCLUIDO sem a TransacaoFinanceira correspondente.
    with transaction.atomic():
        agendamento.status = 'CONCLUIDO'
        agendamento.save(update_fields=['status'])

        # Lança a receita só uma vez (evita duplicar caso a ação seja repetida)
        if agendamento.valor_cobrado and not agendamento.transacoes.filter(tipo='ENTRADA').exists():
            TransacaoFinanceira.objects.create(
                tipo='ENTRADA',
                valor=agendamento.valor_cobrado,
                descricao=(
                    f'{agendamento.servico.nome} - '
                    f'{agendamento.cliente.usuario.get_full_name()}'
                ),
                agendamento=agendamento,
            )
    return agendamento


def marcar_no_show(agendamento_id: int) -> Agendamento:
    """Marca falta do cliente (-> NO_SHOW). Não vale para concluídos/cancelados."""
    try:
        agendamento = Agendamento.objects.get(id=agendamento_id)
    except Agendamento.DoesNotExist:
        raise ValidationError('Agendamento não encontrado.')

    if agendamento.status in ('CONCLUIDO', 'CANCELADO'):
        raise ValidationError(
            f'Agendamento com status "{agendamento.get_status_display()}" '
            f'não pode ser marcado como falta.'
        )

    agendamento.status = 'NO_SHOW'
    agendamento.save(update_fields=['status'])
    return agendamento


def editar_agendamento(
    agendamento_id: int,
    novo_profissional_id: int,
    novo_servico_id: int,
    nova_hora_de_inicio: datetime,
) -> Agendamento:
    """
    CORRIGIDO:
    - Usa nomes corretos de campo (data_hora_inicio, data_hora_fim).
    - Reutiliza objetos de verificar_disponibilidade (sem N+1).
    - Usa update_fields para salvar apenas os campos alterados.
    """
    try:
        agendamento = Agendamento.objects.get(id=agendamento_id)
    except Agendamento.DoesNotExist:
        raise ValidationError('Agendamento não encontrado.')

    if agendamento.status in ['CONCLUIDO', 'CANCELADO']:
        raise ValidationError('Agendamento concluído ou cancelado não pode ser editado.')

    # Mesmo lock de criar_agendamento: serializa a remarcação contra reservas
    # concorrentes do mesmo profissional (evita double booking na corrida).
    with transaction.atomic():
        Funcionario.objects.select_for_update().filter(pk=novo_profissional_id).first()

        funcionario, servico = verificar_disponibilidade(
            novo_profissional_id,
            novo_servico_id,
            nova_hora_de_inicio,
            ignorar_agendamento_id=agendamento_id,
        )

        nova_hora_fim = nova_hora_de_inicio + timedelta(minutes=servico.duracao_minutos)

        agendamento.profissional = funcionario
        agendamento.servico = servico
        agendamento.data_hora_inicio = nova_hora_de_inicio   # CORRIGIDO
        agendamento.data_hora_fim = nova_hora_fim             # CORRIGIDO
        agendamento.valor_cobrado = servico.preco

        agendamento.save(update_fields=[
            'profissional', 'servico', 'data_hora_inicio', 'data_hora_fim', 'valor_cobrado'
        ])
    return agendamento

def gerar_horarios_disponiveis(profissional_id: int, servico_id: int) -> list:
    """
    Gera a lista de dias e horários disponíveis para os próximos 5 dias úteis do profissional.
    """
    try:
        servico = Servico.objects.get(id=servico_id)
        funcionario = Funcionario.objects.get(id=profissional_id, esta_ativo=True)
    except (Servico.DoesNotExist, Funcionario.DoesNotExist):
        return []

    jornadas = list(JornadaTrabalho.objects.filter(funcionario=funcionario))
    if not jornadas:
        return []
        
    dias_trabalho = {j.dia_da_semana: j for j in jornadas}

    hoje = timezone.localtime(timezone.now()).date()
    agendamentos = Agendamento.objects.filter(
        profissional=funcionario,
        status__in=['PENDENTE', 'CONFIRMADO'],
        data_hora_inicio__date__gte=hoje
    ).order_by('data_hora_inicio')

    # Agrupar agendamentos por data (string YYYY-MM-DD) para busca rápida
    agendamentos_por_dia = {}
    for ag in agendamentos:
        dia_str = timezone.localtime(ag.data_hora_inicio).date().isoformat()
        if dia_str not in agendamentos_por_dia:
            agendamentos_por_dia[dia_str] = []
        agendamentos_por_dia[dia_str].append(ag)

    dias_encontrados = []
    data_atual = hoje
    dias_checados = 0

    while len(dias_encontrados) < 5 and dias_checados < 30:
        dia_semana = data_atual.weekday()
        if dia_semana in dias_trabalho:
            jornada = dias_trabalho[dia_semana]
            
            # Construir horários do dia
            dia_str = data_atual.isoformat()
            horarios_do_dia = []
            
            # Se for hoje, oculta os horários que já passaram (só mostra futuros).
            hora_minima = None
            if data_atual == hoje:
                hora_minima = timezone.localtime(timezone.now()).time()

            inicio_expediente = datetime.combine(data_atual, jornada.hora_inicio)
            fim_expediente = datetime.combine(data_atual, jornada.hora_fim)
            
            slot_atual = timezone.make_aware(inicio_expediente)
            fim_expediente_aware = timezone.make_aware(fim_expediente)
            duracao = timedelta(minutes=servico.duracao_minutos)
            
            agendamentos_hoje = agendamentos_por_dia.get(dia_str, [])

            while slot_atual + duracao <= fim_expediente_aware:
                slot_fim = slot_atual + duracao
                
                # Pular se o horário já passou (caso seja o dia atual)
                if hora_minima and slot_atual.time() <= hora_minima:
                    slot_atual += timedelta(minutes=30)
                    continue

                # Checar conflitos com agendamentos existentes
                conflito = False
                for ag in agendamentos_hoje:
                    # Conflito se o slot solicitado se sobrepõe ao agendamento
                    if slot_atual < ag.data_hora_fim and slot_fim > ag.data_hora_inicio:
                        conflito = True
                        break
                
                if not conflito:
                    horarios_do_dia.append({
                        'hora': slot_atual.strftime('%H:%M'),
                        'datetime_completo': slot_atual.strftime('%Y-%m-%dT%H:%M')
                    })
                
                slot_atual += timedelta(minutes=30) # Intervalos de 30 mins

            if horarios_do_dia:
                dias_encontrados.append({
                    'data': dia_str,
                    'data_formatada': data_atual.strftime('%d/%m/%Y'),
                    'dia_semana_nome': ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'][dia_semana],
                    'horarios': horarios_do_dia
                })
                
        data_atual += timedelta(days=1)
        dias_checados += 1

    return dias_encontrados
