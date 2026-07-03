"""
agendaController.py — rotas de AGENDAMENTO do cliente.

- /agendar/ (GET) renderiza a tela com os cards de serviço/profissional;
  (POST) recebe a escolha e pede ao agendaService para criar a reserva.
- /api/horarios-disponiveis/ é a mini-API JSON que o JavaScript da tela
  chama para montar os chips de dia/horário.
"""

import logging
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone

# pyrefly: ignore [missing-import]
from ..models import ClienteProfile, Funcionario, Servico
# pyrefly: ignore [missing-import]
from ..services.agendaService import criar_agendamento, gerar_horarios_disponiveis


logger = logging.getLogger(__name__)


@login_required
def criar_agendamento_controller(request):
    try:
        cliente_profile = ClienteProfile.objects.get(usuario=request.user)
    except ClienteProfile.DoesNotExist:
        # Contas da equipe (dona/profissionais) não têm perfil de cliente —
        # agendamento de cliente se gerencia pelo painel administrativo.
        if request.user.is_staff:
            messages.info(
                request,
                'Sua conta é administrativa: os agendamentos das clientes '
                'são gerenciados pelo painel.'
            )
            return redirect('dashboard_admin')
        messages.error(
            request,
            'Seu usuário não possui um perfil de cliente. Contate o suporte.'
        )
        return redirect('home')

    if request.method == 'POST':
        profissional_id = request.POST.get('profissionalId')
        servico_id = request.POST.get('servicoId')
        hora_inicio_raw = request.POST.get('hora_de_inicio')

        if not all([profissional_id, servico_id, hora_inicio_raw]):
            messages.error(request, 'Preencha todos os campos obrigatórios.')
            return redirect('criar_agendamento')

        try:
            # make_aware converte o horário local (SP) selecionado pelo usuário
            # para datetime aware, necessário com USE_TZ=True e PostgreSQL.
            # strptime lança ValueError quando o formato não bate; capturar
            # apenas isso evita mascarar erros inesperados como "data inválida".
            hora_de_inicio = timezone.make_aware(
                datetime.strptime(hora_inicio_raw, '%Y-%m-%dT%H:%M')
            )
        except ValueError:
            messages.error(request, 'Formato de data/hora inválido.')
            return redirect('criar_agendamento')

        try:
            criar_agendamento(
                profissional_id=int(profissional_id),
                servico_id=int(servico_id),
                cliente_id=cliente_profile.pk,
                hora_de_inicio=hora_de_inicio,
            )
            messages.success(request, 'Agendamento criado com sucesso.')
            # Vai para "Meus Agendamentos": a home não renderiza mensagens, então
            # a confirmação se perderia. Lá o cliente vê o agendamento recém-criado.
            return redirect('dashboard_cliente')

        except ValidationError as error:
            for msg in error.messages:
                messages.error(request, msg)
            return redirect('criar_agendamento')

    # A UI carrega os horários sob demanda via /api/horarios-disponiveis/, então
    # só precisamos popular os selects de profissional e serviço aqui. (A antiga
    # exportação de "jornadas_json" não era usada por nenhum template.)
    funcionarios = (
        Funcionario.objects
        .filter(esta_ativo=True)
        .select_related('usuario')
    )
    servicos = Servico.objects.all()

    return render(
        request,
        'templateCliente/agendamento/criar_agendamento.html',
        context={
            'funcionarios': funcionarios,
            'servicos': servicos,
        },
    )


@login_required
def api_horarios_disponiveis(request):
    profissional_id = request.GET.get('profissional_id')
    servico_id = request.GET.get('servico_id')

    if not profissional_id or not servico_id:
        return JsonResponse({
            'success': False,
            'error': 'Parâmetros profissional_id e servico_id são obrigatórios.',
        }, status=400)

    try:
        pid = int(profissional_id)
        sid = int(servico_id)
    except (ValueError, TypeError):
        return JsonResponse({
            'success': False,
            'error': 'IDs devem ser números inteiros.',
        }, status=400)

    try:
        dias = gerar_horarios_disponiveis(pid, sid)
        return JsonResponse({'success': True, 'dias': dias})
    except Exception:
        logger.exception('Erro ao gerar horários disponíveis')
        return JsonResponse({
            'success': False,
            'error': 'Erro interno ao buscar horários. Tente novamente.',
        }, status=500)
