from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.crypto import get_random_string

# pyrefly: ignore [missing-import]
from ..models import (
    Agendamento, ClienteProfile, Funcionario,
    Servico, TransacaoFinanceira,
)

# pyrefly: ignore [missing-import]
from ..services.agendaServices import (
    listar_agendamentos_cliente,
    cancelar_agendamento,
    confirmar_agendamento,
    concluir_agendamento,
    marcar_no_show,
)
# pyrefly: ignore [missing-import]
from ..forms import ServicoForm, FuncionarioForm

Usuario = get_user_model()


@login_required
def dashboard_cliente_controller(request):
    try:
        cliente_profile = ClienteProfile.objects.get(usuario=request.user)
    except ClienteProfile.DoesNotExist:
        messages.error(request, 'Seu usuário não possui perfil de cliente.')
        return redirect('home')

    agendamentos = listar_agendamentos_cliente(cliente_profile.pk)

    ativos = agendamentos.filter(status__in=['PENDENTE', 'CONFIRMADO'])
    historico = agendamentos.filter(status__in=['CONCLUIDO', 'CANCELADO', 'NO_SHOW'])

    return render(request, 'templateCliente/dashboard/dashboard.html', {
        'ativos': ativos,
        'historico': historico,
    })


@login_required
def cancelar_agendamento_controller(request, agendamento_id: int):
    if request.method != 'POST':
        return redirect('dashboard_cliente')

    try:
        cliente_profile = ClienteProfile.objects.get(usuario=request.user)
    except ClienteProfile.DoesNotExist:
        messages.error(request, 'Perfil de cliente não encontrado.')
        return redirect('home')

    try:
        agendamento = Agendamento.objects.get(
            id=agendamento_id, cliente=cliente_profile,
        )
    except Agendamento.DoesNotExist:
        messages.error(request, 'Agendamento não encontrado.')
        return redirect('dashboard_cliente')

    try:
        cancelar_agendamento(agendamento.pk)
        messages.success(request, 'Agendamento cancelado com sucesso.')
    except ValidationError as e:
        for msg in e.messages:
            messages.error(request, msg)

    return redirect('dashboard_cliente')


def is_admin(user) -> bool:
    return user.is_staff or user.is_superuser


@login_required
@user_passes_test(is_admin, login_url='home')
def dashboard_admin_controller(request):
    servico_form = ServicoForm()
    funcionario_form = FuncionarioForm()

    if request.method == 'POST':
        if 'add_servico' in request.POST:
            servico_form = ServicoForm(request.POST)
            if servico_form.is_valid():
                servico_form.save()
                messages.success(request, 'Serviço adicionado com sucesso!')
                return redirect('dashboard_admin')
            else:
                messages.error(request, 'Erro ao adicionar serviço. Verifique os dados.')

        elif 'add_funcionario' in request.POST:
            funcionario_form = FuncionarioForm(request.POST)
            if funcionario_form.is_valid():
                email = funcionario_form.cleaned_data['email']
                if Usuario.objects.filter(email=email).exists():
                    messages.error(request, 'Já existe um usuário com este e-mail.')
                else:
                    senha_temporaria = get_random_string(length=12)
                    celular_raw = funcionario_form.cleaned_data.get('celular', '')
                    celular = celular_raw if celular_raw else None

                    try:
                        user = Usuario.objects.create_user(
                            username=email,
                            email=email,
                            first_name=funcionario_form.cleaned_data['first_name'],
                            last_name=funcionario_form.cleaned_data['last_name'],
                            celular=celular,
                            password=senha_temporaria,
                        )
                    except IntegrityError:
                        # Celular já cadastrado para outro usuário
                        messages.error(request, 'Este número de celular já está cadastrado.')
                    else:
                        user.is_staff = True
                        user.save()

                        funcionario = funcionario_form.save(commit=False)
                        funcionario.usuario = user
                        funcionario.save()
                        messages.success(
                            request,
                            f'Profissional adicionado! Senha temporária: {senha_temporaria}'
                        )
                        return redirect('dashboard_admin')

    hoje = timezone.now().date()
    # Conta apenas agendamentos ativos (PENDENTE/CONFIRMADO) para refletir
    # a carga de trabalho real do dia — cancelados não entram na métrica.
    agendamentos_hoje = Agendamento.objects.filter(
        data_hora_inicio__date=hoje,
        status__in=['PENDENTE', 'CONFIRMADO'],
    ).count()

    mes_atual = timezone.now().month
    ano_atual = timezone.now().year
    receita_mes = TransacaoFinanceira.objects.filter(
        tipo='ENTRADA',
        data_hora__year=ano_atual,
        data_hora__month=mes_atual
    ).aggregate(total=Sum('valor'))['total'] or 0.00

    total_funcionarios = Funcionario.objects.filter(esta_ativo=True).count()
    total_servicos = Servico.objects.count()

    servicos = Servico.objects.all()
    funcionarios = Funcionario.objects.select_related('usuario').all()
    ultimos_agendamentos = (
        Agendamento.objects
        .select_related('profissional__usuario', 'servico', 'cliente__usuario')
        .order_by('-data_hora_inicio')[:10]
    )

    context = {
        'agendamentos_hoje': agendamentos_hoje,
        'receita_mes': receita_mes,
        'total_funcionarios': total_funcionarios,
        'total_servicos': total_servicos,
        'servico_form': servico_form,
        'funcionario_form': funcionario_form,
        'servicos': servicos,
        'funcionarios': funcionarios,
        'ultimos_agendamentos': ultimos_agendamentos,
    }

    return render(request, 'templateAdmin/dashboard.html', context)


@login_required
@user_passes_test(is_admin, login_url='home')
def gerenciar_agendamento_controller(request, agendamento_id: int):
    """
    Ações do admin sobre um agendamento: confirmar, concluir (lança receita),
    cancelar ou marcar falta. Só aceita POST e é restrito a staff/admin.
    """
    if request.method != 'POST':
        return redirect('dashboard_admin')

    acoes = {
        'confirmar': (confirmar_agendamento, 'Agendamento confirmado com sucesso!'),
        'concluir': (concluir_agendamento, 'Agendamento concluído e receita lançada!'),
        'cancelar': (cancelar_agendamento, 'Agendamento cancelado.'),
        'no_show': (marcar_no_show, 'Agendamento marcado como falta (não compareceu).'),
    }

    acao = request.POST.get('acao')
    if acao not in acoes:
        messages.error(request, 'Ação inválida.')
        return redirect('dashboard_admin')

    funcao, msg_sucesso = acoes[acao]
    try:
        funcao(agendamento_id)
        messages.success(request, msg_sucesso)
    except ValidationError as erro:
        for msg in erro.messages:
            messages.error(request, msg)

    return redirect('dashboard_admin')
