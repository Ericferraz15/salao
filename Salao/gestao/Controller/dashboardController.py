"""
dashboardController.py — telas logadas: painel do CLIENTE e painel da DONA.

Lembrete da arquitetura (Controller fino, service gordo):
- o controller recebe o request, valida o básico, chama o service e
  devolve render/redirect com mensagens;
- as regras de negócio de verdade moram em services/ (agendaServices,
  financeiroService, estoqueService).

Rotas atendidas aqui (ver gestao/urls.py):
- /meus-agendamentos/                      -> dashboard_cliente_controller
- /cancelar-agendamento/<id>/              -> cancelar_agendamento_controller
- /admin-dashboard/                        -> dashboard_admin_controller
- /admin-dashboard/agendamento/<id>/       -> gerenciar_agendamento_controller
- /admin-dashboard/produto/<id>/estoque/   -> ajustar_estoque_controller
- /admin-dashboard/jornada/<id>/remover/   -> remover_jornada_controller
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.crypto import get_random_string

# pyrefly: ignore [missing-import]
from ..models import (
    Agendamento, ClienteProfile, Funcionario, JornadaTrabalho,
    Produto, Servico, TransacaoFinanceira,
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
from ..services.financeiroService import (
    lancar_transacao,
    receita_por_dia,
    resumo_financeiro,
)
# pyrefly: ignore [missing-import]
from ..services.estoqueService import ajustar_estoque
# pyrefly: ignore [missing-import]
from ..forms import (
    FuncionarioForm, JornadaForm, ProdutoForm, ServicoForm, TransacaoForm,
)

Usuario = get_user_model()


# ═══════════════════════════════════════════════════════════════════════════
# PAINEL DO CLIENTE
# ═══════════════════════════════════════════════════════════════════════════

@login_required
def dashboard_cliente_controller(request):
    """"Meus Agendamentos": próximos horários + histórico do cliente."""
    try:
        cliente_profile = ClienteProfile.objects.get(usuario=request.user)
    except ClienteProfile.DoesNotExist:
        messages.error(request, 'Seu usuário não possui perfil de cliente.')
        return redirect('home')

    agendamentos = listar_agendamentos_cliente(cliente_profile.pk)

    # Ativos em ordem crescente (o próximo primeiro); histórico em ordem
    # decrescente (o mais recente primeiro), como se espera de um histórico.
    ativos = agendamentos.filter(status__in=['PENDENTE', 'CONFIRMADO'])
    historico = (
        agendamentos
        .filter(status__in=['CONCLUIDO', 'CANCELADO', 'NO_SHOW'])
        .order_by('-data_hora_inicio')
    )

    return render(request, 'templateCliente/dashboard/dashboard.html', {
        'ativos': ativos,
        'historico': historico,
    })


@login_required
def cancelar_agendamento_controller(request, agendamento_id: int):
    """Cliente cancela o PRÓPRIO agendamento (vira CANCELADO, não some)."""
    if request.method != 'POST':
        return redirect('dashboard_cliente')

    try:
        cliente_profile = ClienteProfile.objects.get(usuario=request.user)
    except ClienteProfile.DoesNotExist:
        messages.error(request, 'Perfil de cliente não encontrado.')
        return redirect('home')

    # Filtrar por cliente=cliente_profile é a AUTORIZAÇÃO: um cliente não
    # enxerga (nem cancela) agendamento que não é dele.
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


# ═══════════════════════════════════════════════════════════════════════════
# PAINEL DA DONA (ADMIN)
# ═══════════════════════════════════════════════════════════════════════════

def is_admin(user) -> bool:
    return user.is_staff or user.is_superuser


# ── Handlers de cada formulário do painel (POST) ────────────────────────────
# O template envia um botão com name= diferente por formulário
# (add_servico, add_funcionario, ...); o controller principal despacha
# para o handler certo. Cada handler devolve um redirect em caso de
# sucesso, ou None para re-renderizar a página com os erros do form.

def _tratar_add_servico(request, forms_da_pagina):
    form = ServicoForm(request.POST, request.FILES)
    forms_da_pagina['servico_form'] = form
    if form.is_valid():
        form.save()
        messages.success(request, 'Serviço adicionado com sucesso!')
        return redirect('dashboard_admin')
    messages.error(request, 'Erro ao adicionar serviço. Verifique os dados.')
    return None


def _tratar_add_funcionario(request, forms_da_pagina):
    form = FuncionarioForm(request.POST, request.FILES)
    forms_da_pagina['funcionario_form'] = form
    if not form.is_valid():
        messages.error(request, 'Erro ao adicionar profissional. Verifique os dados.')
        return None

    email = form.cleaned_data['email']
    if Usuario.objects.filter(email=email).exists():
        messages.error(request, 'Já existe um usuário com este e-mail.')
        return None

    senha_temporaria = get_random_string(length=12)
    celular = form.cleaned_data.get('celular') or None

    try:
        # Usuário + Funcionário na mesma transação: se a criação do
        # Funcionário falhar, o usuário não fica órfão (staff sem registro
        # de profissional, com e-mail/celular presos pelo unique).
        with transaction.atomic():
            user = Usuario.objects.create_user(
                username=email,
                email=email,
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                celular=celular,
                password=senha_temporaria,
            )
            user.is_staff = True
            user.save(update_fields=['is_staff'])

            funcionario = form.save(commit=False)
            funcionario.usuario = user
            funcionario.save()
    except IntegrityError:
        messages.error(request, 'Este número de celular já está cadastrado.')
        return None

    messages.success(
        request,
        f'Profissional adicionado! Senha temporária: {senha_temporaria}'
    )
    return redirect('dashboard_admin')


def _tratar_add_transacao(request, forms_da_pagina):
    form = TransacaoForm(request.POST)
    forms_da_pagina['transacao_form'] = form
    if form.is_valid():
        try:
            lancar_transacao(
                tipo=form.cleaned_data['tipo'],
                valor=form.cleaned_data['valor'],
                descricao=form.cleaned_data['descricao'],
            )
        except ValidationError as erro:
            for msg in erro.messages:
                messages.error(request, msg)
            return None
        messages.success(request, 'Lançamento registrado no caixa!')
        return redirect('dashboard_admin')
    messages.error(request, 'Erro no lançamento. Verifique os dados.')
    return None


def _tratar_add_produto(request, forms_da_pagina):
    form = ProdutoForm(request.POST)
    forms_da_pagina['produto_form'] = form
    if form.is_valid():
        form.save()
        messages.success(request, 'Produto adicionado ao estoque!')
        return redirect('dashboard_admin')
    messages.error(request, 'Erro ao adicionar produto. Verifique os dados.')
    return None


def _tratar_add_jornada(request, forms_da_pagina):
    form = JornadaForm(request.POST)
    forms_da_pagina['jornada_form'] = form
    if form.is_valid():
        jornada = form.save()
        messages.success(
            request,
            f'Jornada cadastrada: {jornada.funcionario.usuario.first_name} — '
            f'{jornada.get_dia_da_semana_display()}, '
            f'{jornada.hora_inicio:%H:%M} às {jornada.hora_fim:%H:%M}.'
        )
        return redirect('dashboard_admin')
    # Os erros específicos (dia duplicado, fim antes do início) aparecem
    # junto do próprio formulário na página.
    messages.error(request, 'Erro ao cadastrar jornada. Verifique os dados.')
    return None


@login_required
@user_passes_test(is_admin, login_url='home')
def dashboard_admin_controller(request):
    """Painel completo da dona: visão do dia, financeiro e cadastros."""

    # Forms "limpos" por padrão; se um POST falhar na validação, o handler
    # substitui o form correspondente pela versão com os erros do usuário.
    forms_da_pagina = {
        'servico_form': ServicoForm(),
        'funcionario_form': FuncionarioForm(),
        'transacao_form': TransacaoForm(),
        'produto_form': ProdutoForm(),
        'jornada_form': JornadaForm(),
    }

    if request.method == 'POST':
        handlers = {
            'add_servico': _tratar_add_servico,
            'add_funcionario': _tratar_add_funcionario,
            'add_transacao': _tratar_add_transacao,
            'add_produto': _tratar_add_produto,
            'add_jornada': _tratar_add_jornada,
        }
        for chave, handler in handlers.items():
            if chave in request.POST:
                resposta = handler(request, forms_da_pagina)
                if resposta is not None:
                    return resposta
                break  # form inválido: cai no render abaixo com os erros

    # ── Métricas ─────────────────────────────────────────────────────────
    # Horário LOCAL (America/Sao_Paulo) para definir "hoje" e o mês: com
    # timezone.now() (UTC), à noite no Brasil a data/mês já viram o dia
    # seguinte, e as métricas contariam o período errado.
    agora_local = timezone.localtime(timezone.now())
    hoje = agora_local.date()

    # Conta apenas agendamentos ativos (PENDENTE/CONFIRMADO) para refletir
    # a carga de trabalho real do dia — cancelados não entram na métrica.
    agendamentos_hoje = Agendamento.objects.filter(
        data_hora_inicio__date=hoje,
        status__in=['PENDENTE', 'CONFIRMADO'],
    ).count()

    financeiro = resumo_financeiro(agora_local)
    grafico_receita = receita_por_dia(agora_local, dias=7)

    # ── Agenda do dia ────────────────────────────────────────────────────
    # Tudo que acontece hoje (inclusive concluídos, para a dona acompanhar
    # o dia inteiro), em ordem de horário. select_related evita uma query
    # por linha ao mostrar cliente/profissional/serviço (problema N+1).
    agenda_do_dia = (
        Agendamento.objects
        .filter(data_hora_inicio__date=hoje)
        .exclude(status='CANCELADO')
        .select_related('cliente__usuario', 'profissional__usuario', 'servico')
        .order_by('data_hora_inicio')
    )

    # ── Listas de apoio ──────────────────────────────────────────────────
    servicos = Servico.objects.all()
    funcionarios = (
        Funcionario.objects
        .select_related('usuario')
        .prefetch_related('jornadatrabalho_set')
        .all()
    )
    produtos = Produto.objects.order_by('nome')
    produtos_em_falta = [p for p in produtos if p.abaixo_estoque_minimo]
    transacoes_recentes = TransacaoFinanceira.objects.order_by('-data_hora')[:8]
    ultimos_agendamentos = (
        Agendamento.objects
        .select_related('profissional__usuario', 'servico', 'cliente__usuario')
        .order_by('-data_hora_inicio')[:10]
    )
    jornadas = (
        JornadaTrabalho.objects
        .select_related('funcionario__usuario')
        .order_by('funcionario__usuario__first_name', 'dia_da_semana')
    )

    context = {
        'hoje': hoje,
        'agendamentos_hoje': agendamentos_hoje,
        'agenda_do_dia': agenda_do_dia,
        'grafico_receita': grafico_receita,
        'servicos': servicos,
        'funcionarios': funcionarios,
        'produtos': produtos,
        'produtos_em_falta': produtos_em_falta,
        'transacoes_recentes': transacoes_recentes,
        'ultimos_agendamentos': ultimos_agendamentos,
        'jornadas': jornadas,
        'total_funcionarios': Funcionario.objects.filter(esta_ativo=True).count(),
        'total_servicos': servicos.count(),
        **financeiro,        # receita_hoje, receita_mes, despesa_mes, lucro_mes, meta_*
        **forms_da_pagina,   # servico_form, funcionario_form, transacao_form, ...
    }

    return render(request, 'templateAdmin/dashboard.html', context)


@login_required
@user_passes_test(is_admin, login_url='home')
def gerenciar_agendamento_controller(request, agendamento_id: int):
    """Ações do admin sobre um agendamento: confirmar, concluir (lança
    receita), cancelar ou marcar falta. Só aceita POST."""
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


@login_required
@user_passes_test(is_admin, login_url='home')
def ajustar_estoque_controller(request, produto_id: int):
    """Botões +1/-1 do estoque no painel."""
    if request.method != 'POST':
        return redirect('dashboard_admin')

    try:
        delta = int(request.POST.get('delta', ''))
    except ValueError:
        messages.error(request, 'Ajuste de estoque inválido.')
        return redirect('dashboard_admin')

    try:
        produto = ajustar_estoque(produto_id, delta)
        messages.success(
            request,
            f'Estoque de "{produto.nome}" atualizado: {produto.quantidade_estoque} unidade(s).'
        )
    except ValidationError as erro:
        for msg in erro.messages:
            messages.error(request, msg)

    return redirect('dashboard_admin')


@login_required
@user_passes_test(is_admin, login_url='home')
def remover_jornada_controller(request, jornada_id: int):
    """Remove um dia de expediente de uma profissional."""
    if request.method != 'POST':
        return redirect('dashboard_admin')

    try:
        jornada = JornadaTrabalho.objects.select_related('funcionario__usuario').get(id=jornada_id)
    except JornadaTrabalho.DoesNotExist:
        messages.error(request, 'Jornada não encontrada.')
        return redirect('dashboard_admin')

    jornada.delete()
    messages.success(
        request,
        f'Jornada de {jornada.funcionario.usuario.first_name} '
        f'({jornada.get_dia_da_semana_display()}) removida.'
    )
    return redirect('dashboard_admin')
