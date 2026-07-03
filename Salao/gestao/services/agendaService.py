"""
agendaService.py — o CORAÇÃO do sistema: regras de negócio da agenda.

Aqui vive tudo que decide se um horário pode ou não ser marcado:
disponibilidade, conflito, expediente, transições de status
(PENDENTE -> CONFIRMADO -> CONCLUIDO / CANCELADO / NO_SHOW) e a
geração dos horários livres que o site mostra para a cliente.

Convenções deste módulo (valem para os outros services também):
- Erros de regra de negócio viram ValidationError com mensagem amigável;
  o controller captura e mostra na tela. Nunca deixamos vazar erro cru.
- Todos os datetimes são "aware" (têm fuso). O banco guarda em UTC e nós
  convertemos para America/Sao_Paulo com timezone.localtime() sempre que
  a REGRA depende do relógio local (dia da semana, "hoje", etc.).
"""

from datetime import timedelta, datetime

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

# pyrefly: ignore [missing-import]
from ..models import Agendamento, Funcionario, JornadaTrabalho, Servico, TransacaoFinanceira


def _combinar_data_hora(data_referencia: datetime, horario) -> datetime:
    """Junta a DATA local de `data_referencia` com um horário de TimeField.

    Exemplo: (2026-07-03 15:00 SP, time(9, 0)) -> 2026-07-03 09:00 SP.
    Usamos localtime() antes de extrair a data para não errar o dia perto
    da meia-noite: 22h em SP já é o dia seguinte em UTC.
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
    """Valida se o profissional pode atender naquele horário.

    Checa, nesta ordem: serviço existe -> profissional existe e está
    ativo -> horário não está no passado -> profissional trabalha nesse
    dia -> horário cabe no expediente -> não conflita com outra reserva.

    Devolve (funcionario, servico) já carregados para o chamador
    reaproveitar (evita repetir as mesmas queries — problema N+1).
    `ignorar_agendamento_id` serve para a EDIÇÃO: o agendamento não pode
    conflitar consigo mesmo.
    """
    try:
        servico = Servico.objects.get(id=servico_id)
    except Servico.DoesNotExist:
        raise ValidationError('Serviço não encontrado.')

    try:
        # select_related traz o Usuario junto, em uma query só
        funcionario = Funcionario.objects.select_related('usuario').get(
            id=profissional_id,
            esta_ativo=True,
        )
    except Funcionario.DoesNotExist:
        raise ValidationError('Profissional não encontrado ou inativo.')

    # O front já oculta horários passados, mas a regra PRECISA valer aqui
    # também: página aberta há horas, edição ou requisição forjada
    # driblariam uma checagem que existisse só na interface.
    if hora_de_inicio <= timezone.now():
        raise ValidationError('Não é possível agendar em um horário que já passou.')

    duracao = timedelta(minutes=servico.duracao_minutos)
    hora_fim = hora_de_inicio + duracao

    # weekday() no fuso LOCAL: um agendamento às 22h de SP é 01h UTC do
    # dia seguinte — sem localtime() o dia da semana sairia errado.
    dia_semana = timezone.localtime(hora_de_inicio).weekday()

    jornada = JornadaTrabalho.objects.filter(
        funcionario=funcionario,
        dia_da_semana=dia_semana,
    ).first()

    if not jornada:
        raise ValidationError('Profissional não trabalha neste dia da semana.')

    inicio_jornada = _combinar_data_hora(hora_de_inicio, jornada.hora_inicio)
    fim_jornada = _combinar_data_hora(hora_de_inicio, jornada.hora_fim)

    # O atendimento INTEIRO (início e fim) precisa caber no expediente
    if not (hora_de_inicio >= inicio_jornada and hora_fim <= fim_jornada):
        raise ValidationError(
            f'Horário fora do expediente do profissional '
            f'({jornada.hora_inicio.strftime("%H:%M")} – {jornada.hora_fim.strftime("%H:%M")}).'
        )

    # Detecção de sobreposição de intervalos: A conflita com B quando
    # A.inicio < B.fim E A.fim > B.inicio. Só reservas ativas contam —
    # canceladas/no-show liberam o horário.
    conflitos = Agendamento.objects.filter(
        profissional=funcionario,
        status__in=['PENDENTE', 'CONFIRMADO'],
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
    """Cria um agendamento PENDENTE após validar a disponibilidade.

    O preço é "congelado" em valor_cobrado no momento da reserva: se a
    dona reajustar o serviço depois, quem já agendou paga o combinado.
    """
    # atomic + lock na linha do profissional serializa reservas
    # concorrentes: se duas clientes clicarem juntas no mesmo horário, a
    # segunda espera a primeira terminar e o check de conflito enxerga a
    # reserva recém-criada (sem isso haveria "double booking" na corrida).
    # No SQLite o lock é no-op (a escrita já é serializada); no
    # PostgreSQL ele vale de verdade.
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
            data_hora_inicio=hora_de_inicio,
            data_hora_fim=hora_fim,
            valor_cobrado=servico.preco,
            status='PENDENTE',
        )
    return agendamento


def listar_agendamentos_cliente(cliente_id: int):
    """Todos os agendamentos de um cliente, do mais antigo ao mais novo.

    select_related evita o N+1: sem ele, exibir 20 agendamentos faria
    20+ queries extras para buscar profissional/serviço de cada linha.
    """
    return (
        Agendamento.objects
        .filter(cliente_id=cliente_id)
        .select_related('profissional__usuario', 'servico')
        .order_by('data_hora_inicio')
    )


def cancelar_agendamento(agendamento_id: int, usuario_solicitante=None) -> Agendamento:
    """Cancela mudando o STATUS — nunca deletamos o registro.

    Apagar faria os relatórios financeiros e o histórico mentirem;
    cancelado continua no histórico e o horário fica livre de novo.
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
    """PENDENTE -> CONFIRMADO (a dona confirma que vai atender)."""
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
    """Conclui o atendimento e lança a receita no caixa, sem duplicar.

    É aqui que agenda e financeiro se encontram: concluir cria a
    TransacaoFinanceira de ENTRADA correspondente.
    """
    try:
        agendamento = Agendamento.objects.get(id=agendamento_id)
    except Agendamento.DoesNotExist:
        raise ValidationError('Agendamento não encontrado.')

    if agendamento.status not in ('PENDENTE', 'CONFIRMADO'):
        raise ValidationError('Só é possível concluir agendamentos pendentes ou confirmados.')

    # atomic: status e receita são gravados JUNTOS. Sem isso, uma falha no
    # meio deixaria um agendamento CONCLUIDO sem a receita correspondente.
    with transaction.atomic():
        agendamento.status = 'CONCLUIDO'
        agendamento.save(update_fields=['status'])

        # Idempotente: se a receita deste agendamento já existe, não cria
        # outra (protege contra clique duplo / reenvio do form).
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
    """Cliente faltou (-> NO_SHOW). Não vale para concluídos/cancelados."""
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
    """Reagenda: troca profissional/serviço/horário revalidando tudo.

    Passa ignorar_agendamento_id para o conflito não acusar o próprio
    agendamento que está sendo movido.
    """
    try:
        agendamento = Agendamento.objects.get(id=agendamento_id)
    except Agendamento.DoesNotExist:
        raise ValidationError('Agendamento não encontrado.')

    if agendamento.status in ['CONCLUIDO', 'CANCELADO']:
        raise ValidationError('Agendamento concluído ou cancelado não pode ser editado.')

    # Mesmo lock de criar_agendamento: serializa a remarcação contra
    # reservas simultâneas do mesmo profissional.
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
        agendamento.data_hora_inicio = nova_hora_de_inicio
        agendamento.data_hora_fim = nova_hora_fim
        agendamento.valor_cobrado = servico.preco

        agendamento.save(update_fields=[
            'profissional', 'servico', 'data_hora_inicio', 'data_hora_fim', 'valor_cobrado'
        ])
    return agendamento


def gerar_horarios_disponiveis(profissional_id: int, servico_id: int) -> list:
    """Monta os horários livres dos próximos 5 dias de expediente.

    É o que alimenta a tela de agendamento (via /api/horarios-disponiveis/).
    A ideia: para cada dia em que o profissional trabalha, percorre o
    expediente em passos de 30 min e guarda cada slot em que o serviço
    INTEIRO cabe sem esbarrar em outra reserva nem no fim do expediente.

    Devolve no formato pronto para o front:
    [{'data': '2026-07-06', 'data_formatada': '06/07/2026',
      'dia_semana_nome': 'Segunda', 'horarios': [{'hora': '09:00',
      'datetime_completo': '2026-07-06T09:00'}, ...]}, ...]
    """
    try:
        servico = Servico.objects.get(id=servico_id)
        funcionario = Funcionario.objects.get(id=profissional_id, esta_ativo=True)
    except (Servico.DoesNotExist, Funcionario.DoesNotExist):
        # A API devolve lista vazia (o front mostra "sem horários") em vez
        # de estourar erro por um id inválido na URL.
        return []

    jornadas = list(JornadaTrabalho.objects.filter(funcionario=funcionario))
    if not jornadas:
        return []

    dias_trabalho = {j.dia_da_semana: j for j in jornadas}

    # Busca TODAS as reservas ativas futuras de uma vez e agrupa por dia:
    # uma query, em vez de uma por dia dentro do laço.
    hoje = timezone.localtime(timezone.now()).date()
    agendamentos = Agendamento.objects.filter(
        profissional=funcionario,
        status__in=['PENDENTE', 'CONFIRMADO'],
        data_hora_inicio__date__gte=hoje,
    ).order_by('data_hora_inicio')

    agendamentos_por_dia = {}
    for ag in agendamentos:
        dia_str = timezone.localtime(ag.data_hora_inicio).date().isoformat()
        agendamentos_por_dia.setdefault(dia_str, []).append(ag)

    dias_encontrados = []
    data_atual = hoje
    dias_checados = 0

    # Anda dia a dia até juntar 5 dias com vaga (teto de 30 dias para não
    # varrer o calendário inteiro se a agenda estiver lotada).
    while len(dias_encontrados) < 5 and dias_checados < 30:
        dia_semana = data_atual.weekday()
        if dia_semana in dias_trabalho:
            jornada = dias_trabalho[dia_semana]

            dia_str = data_atual.isoformat()
            horarios_do_dia = []

            # No dia de HOJE, esconde horários que já passaram
            hora_minima = None
            if data_atual == hoje:
                hora_minima = timezone.localtime(timezone.now()).time()

            inicio_expediente = datetime.combine(data_atual, jornada.hora_inicio)
            fim_expediente = datetime.combine(data_atual, jornada.hora_fim)

            slot_atual = timezone.make_aware(inicio_expediente)
            fim_expediente_aware = timezone.make_aware(fim_expediente)
            duracao = timedelta(minutes=servico.duracao_minutos)

            reservas_do_dia = agendamentos_por_dia.get(dia_str, [])

            # O serviço inteiro precisa caber: slot + duração <= fim
            while slot_atual + duracao <= fim_expediente_aware:
                slot_fim = slot_atual + duracao

                if hora_minima is not None and slot_atual.time() <= hora_minima:
                    slot_atual += timedelta(minutes=30)
                    continue

                # Mesma regra de sobreposição do verificar_disponibilidade
                conflito = False
                for ag in reservas_do_dia:
                    if slot_atual < ag.data_hora_fim and slot_fim > ag.data_hora_inicio:
                        conflito = True
                        break

                if not conflito:
                    horarios_do_dia.append({
                        'hora': slot_atual.strftime('%H:%M'),
                        'datetime_completo': slot_atual.strftime('%Y-%m-%dT%H:%M'),
                    })

                slot_atual += timedelta(minutes=30)  # grade de 30 em 30 min

            if horarios_do_dia:
                dias_encontrados.append({
                    'data': dia_str,
                    'data_formatada': data_atual.strftime('%d/%m/%Y'),
                    'dia_semana_nome': ['Segunda', 'Terça', 'Quarta', 'Quinta',
                                        'Sexta', 'Sábado', 'Domingo'][dia_semana],
                    'horarios': horarios_do_dia,
                })

        data_atual += timedelta(days=1)
        dias_checados += 1

    return dias_encontrados
