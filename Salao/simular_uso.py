"""
simular_uso.py

Simulação de uso REAL do sistema, ponta a ponta.

Exercita as duas camadas:
  1. HTTP (django.test.Client) — como um navegador de verdade faria:
     login, abrir páginas, enviar formulários, chamar a API de horários.
  2. Camada de serviços (agendaService) — regras de negócio diretas:
     conflito de horário, fora do expediente, dia sem jornada, edição.

Os dados criados ficam PERSISTIDOS no banco local (SQLite) para que possam
ser inspecionados depois no /admin-dashboard ou no Django admin.

Como rodar (a partir de salao/Salao/):
    python simular_uso.py
"""

import io
import os
import sys

import django

# Garante saída UTF-8 no console do Windows (evita 'S�bado' quebrado).
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Salao.settings')
django.setup()

# Fora do test runner é preciso instrumentar manualmente o ambiente de teste:
#  - conecta o signal que popula response.context (senão fica None);
#  - adiciona o host 'testserver' ao ALLOWED_HOSTS usado pelo Client.
from django.test.utils import setup_test_environment
setup_test_environment()

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from gestao.models import (
    Agendamento,
    ClienteProfile,
    Funcionario,
    JornadaTrabalho,
    Servico,
)
from gestao.services.agendaService import (
    criar_agendamento,
    editar_agendamento,
    gerar_horarios_disponiveis,
)

Usuario = get_user_model()

# -------------------------------------------------------------------------
# Infra de relatório
# -------------------------------------------------------------------------
_total = {'ok': 0, 'falha': 0}


def secao(titulo: str) -> None:
    print('\n' + '=' * 70)
    print(f'  {titulo}')
    print('=' * 70)


def checa(descricao: str, condicao: bool, detalhe: str = '') -> None:
    """Registra um passo da simulação como [OK] ou [FALHA]."""
    tag = '[OK]   ' if condicao else '[FALHA]'
    if condicao:
        _total['ok'] += 1
    else:
        _total['falha'] += 1
    linha = f'  {tag} {descricao}'
    if detalhe:
        linha += f'  ->  {detalhe}'
    print(linha)


def _proximo_dia_semana(alvo: int, hora: int = 10):
    """Retorna o próximo datetime aware no dia da semana 'alvo' (0=seg)."""
    hoje = timezone.localtime(timezone.now())
    delta = (alvo - hoje.weekday()) % 7
    if delta == 0:
        delta = 7
    dia = hoje + timedelta(days=delta)
    return dia.replace(hour=hora, minute=0, second=0, microsecond=0)


# -------------------------------------------------------------------------
# 0. Limpeza — torna a simulação idempotente (pode rodar várias vezes)
# -------------------------------------------------------------------------
def limpar_dados_simulacao() -> None:
    secao('0. LIMPEZA DE DADOS ANTERIORES DA SIMULAÇÃO')
    Agendamento.objects.all().delete()
    JornadaTrabalho.objects.all().delete()
    # Remove usuários da simulação (mantém qualquer outro que já existisse).
    apagados, _ = Usuario.objects.filter(email__endswith='@sim.salao').delete()
    Servico.objects.filter(nome__startswith='[SIM]').delete()
    print(f'  Dados de simulações anteriores removidos ({apagados} registros de usuário).')


# -------------------------------------------------------------------------
# 1. Cadastro de funcionários, serviços e jornadas
# -------------------------------------------------------------------------
def montar_salao():
    secao('1. MONTAGEM DO SALÃO (funcionários, serviços, jornadas)')

    # Admin / dona do salão
    admin = Usuario.objects.create_superuser(
        username='eduarda@sim.salao', email='eduarda@sim.salao',
        password='Admin@123', first_name='Eduarda', last_name='Ferraz',
        celular='11900000001',
    )
    checa('Superusuária (admin) criada', admin.is_superuser, admin.get_full_name())

    # Funcionários
    profissionais = []
    dados_func = [
        ('Joana', 'Cabeleireira', 'joana@sim.salao', '11900000002', 'Cabeleireira'),
        ('Carla', 'Manicure', 'carla@sim.salao', '11900000003', 'Manicure'),
    ]
    for nome, _cargo, email, cel, espec in dados_func:
        u = Usuario.objects.create_user(
            username=email, email=email, password='Func@123',
            first_name=nome, last_name='Profissional', celular=cel,
        )
        u.is_staff = True
        u.save()
        f = Funcionario.objects.create(usuario=u, especializacao=espec, esta_ativo=True)
        profissionais.append(f)
        checa(f'Funcionária "{nome}" criada', f.pk is not None, espec)

    # Jornadas: segunda(0) a sexta(4), 09h-18h para ambas
    for f in profissionais:
        for dia in range(5):
            JornadaTrabalho.objects.create(
                funcionario=f, dia_da_semana=dia,
                hora_inicio='09:00', hora_fim='18:00',
            )
    total_jornadas = JornadaTrabalho.objects.count()
    checa('Jornadas de trabalho cadastradas (seg-sex)', total_jornadas == 10,
          f'{total_jornadas} jornadas')

    # Serviços
    servicos = []
    dados_serv = [
        ('[SIM] Corte Feminino', 'Corte e finalização', 60, 80.00),
        ('[SIM] Manicure', 'Esmaltação em gel', 45, 50.00),
        ('[SIM] Coloração', 'Tintura completa', 120, 180.00),
    ]
    for nome, desc, dur, preco in dados_serv:
        s = Servico.objects.create(
            nome=nome, descricao=desc, duracao_minutos=dur, preco=preco,
        )
        servicos.append(s)
        checa(f'Serviço "{nome}" criado', s.pk is not None,
              f'{dur}min / R$ {preco:.2f}')

    return admin, profissionais, servicos


# -------------------------------------------------------------------------
# 2. Cadastro de cliente via HTTP (formulário real de registro)
# -------------------------------------------------------------------------
def cadastrar_cliente_via_http():
    secao('2. CADASTRO DE CLIENTE (via formulário HTTP /cadastro/)')
    c = Client()
    # Sem 'username': o formulário não tem mais esse campo (e-mail é o login).
    # Senha simples de 6+ caracteres, como uma cliente real usaria.
    resp = c.post(reverse('cadastro_cliente'), {
        'first_name': 'Mariana',
        'last_name': 'Souza',
        'email': 'mariana@sim.salao',
        'celular': '(11) 90000-0004',
        'password1': 'mari123',
        'password2': 'mari123',
    })
    existe = Usuario.objects.filter(email='mariana@sim.salao').exists()
    checa('POST /cadastro/ retorna redirect (302)', resp.status_code == 302,
          f'status={resp.status_code}')
    checa('Usuário cliente persistido no banco', existe)
    tem_perfil = ClienteProfile.objects.filter(
        usuario__email='mariana@sim.salao').exists()
    checa('ClienteProfile criado automaticamente', tem_perfil)
    return Usuario.objects.get(email='mariana@sim.salao')


# -------------------------------------------------------------------------
# 3. Fluxo do cliente: login, API de horários, agendar, ver, cancelar
# -------------------------------------------------------------------------
def fluxo_cliente(cliente_user, profissionais, servicos):
    secao('3. FLUXO DO CLIENTE (login -> agendar -> dashboard -> cancelar)')
    c = Client()
    logado = c.login(username='mariana@sim.salao', password='mari123')
    checa('Login do cliente', logado)

    joana = profissionais[0]
    corte = servicos[0]

    # 3.1 Abre a página de agendamento
    resp = c.get(reverse('criar_agendamento'))
    checa('GET /agendar/ carrega (200)', resp.status_code == 200,
          f'status={resp.status_code}')

    # 3.2 Chama a API de horários disponíveis (como o JS do front faz)
    resp = c.get(reverse('api_horarios_disponiveis'), {
        'profissional_id': joana.pk,
        'servico_id': corte.pk,
    })
    data = resp.json()
    tem_horarios = bool(data.get('dias'))
    checa('API horários-disponiveis retorna dias', tem_horarios,
          f'{len(data.get("dias", []))} dia(s) com vagas')

    # Usa o primeiro horário sugerido pela própria API (realista)
    primeiro_dia = data['dias'][0]
    primeiro_horario = primeiro_dia['horarios'][0]['datetime_completo']

    # 3.3 Envia o formulário de agendamento (POST real)
    resp = c.post(reverse('criar_agendamento'), {
        'profissionalId': joana.pk,
        'servicoId': corte.pk,
        'hora_de_inicio': primeiro_horario,
    })
    ag = Agendamento.objects.filter(
        cliente__usuario=cliente_user, profissional=joana,
    ).first()
    checa('POST /agendar/ cria agendamento (redirect 302)', resp.status_code == 302)
    checa('Agendamento persistido com status PENDENTE',
          ag is not None and ag.status == 'PENDENTE',
          f'{primeiro_dia["data_formatada"]} {primeiro_horario[-5:]}' if ag else 'não criado')
    checa('Valor cobrado preenchido a partir do serviço',
          ag is not None and ag.valor_cobrado == corte.preco,
          f'R$ {ag.valor_cobrado}' if ag else '')

    # 3.4 Tenta agendar conflito no MESMO horário (deve falhar via service)
    try:
        criar_agendamento(
            profissional_id=joana.pk, servico_id=corte.pk,
            cliente_id=cliente_user.clienteprofile.pk,
            hora_de_inicio=ag.data_hora_inicio,
        )
        checa('Conflito de horário é bloqueado', False, 'NÃO bloqueou (bug!)')
    except ValidationError:
        checa('Conflito de horário é bloqueado', True, 'ValidationError lançada')

    # 3.5 Dashboard do cliente mostra o agendamento ativo
    resp = c.get(reverse('dashboard_cliente'))
    checa('GET /meus-agendamentos/ carrega (200)', resp.status_code == 200)
    ativos = resp.context['ativos']
    checa('Agendamento aparece na lista de ativos', ativos.count() == 1,
          f'{ativos.count()} ativo(s)')

    # 3.6 Cliente cancela o agendamento (POST real)
    resp = c.post(reverse('cancelar_agendamento', args=[ag.pk]))
    ag.refresh_from_db()
    checa('POST cancelamento redireciona (302)', resp.status_code == 302)
    checa('Status muda para CANCELADO (não deletado)', ag.status == 'CANCELADO')

    # 3.7 Após cancelar, some dos ativos e entra no histórico
    resp = c.get(reverse('dashboard_cliente'))
    checa('Cancelado sai dos ativos', resp.context['ativos'].count() == 0)
    checa('Cancelado entra no histórico', resp.context['historico'].count() == 1)


# -------------------------------------------------------------------------
# 4. Fluxo do admin: dashboard, adicionar serviço e funcionário via HTTP
# -------------------------------------------------------------------------
def fluxo_admin():
    secao('4. FLUXO DO ADMIN (dashboard + cadastros via HTTP)')
    c = Client()
    logado = c.login(username='eduarda@sim.salao', password='Admin@123')
    checa('Login do admin', logado)

    # 4.1 Acessa o painel
    resp = c.get(reverse('dashboard_admin'))
    checa('GET /admin-dashboard/ carrega (200)', resp.status_code == 200)
    ctx = resp.context
    checa('Métricas presentes no contexto',
          all(k in ctx for k in ('agendamentos_hoje', 'receita_mes',
                                 'total_funcionarios', 'total_servicos')),
          f'func={ctx["total_funcionarios"]} serv={ctx["total_servicos"]}')

    # 4.2 Adiciona um serviço novo pelo formulário do painel
    qtd_antes = Servico.objects.count()
    resp = c.post(reverse('dashboard_admin'), {
        'add_servico': '1',
        'nome': '[SIM] Hidratação',
        'descricao': 'Hidratação profunda',
        'duracao_minutos': 40,
        'preco': '70.00',
    })
    checa('POST add_servico cria serviço (302)',
          resp.status_code == 302 and Servico.objects.count() == qtd_antes + 1,
          f'{qtd_antes} -> {Servico.objects.count()}')

    # 4.3 Adiciona um funcionário pelo formulário do painel
    qtd_func_antes = Funcionario.objects.count()
    resp = c.post(reverse('dashboard_admin'), {
        'add_funcionario': '1',
        'first_name': 'Patrícia',
        'last_name': 'Lima',
        'email': 'patricia@sim.salao',
        'celular': '11900000099',
        'especializacao': 'Designer de Sobrancelhas',
        'esta_ativo': 'on',
    })
    nova = Funcionario.objects.filter(usuario__email='patricia@sim.salao').first()
    checa('POST add_funcionario cria profissional (302)',
          resp.status_code == 302 and Funcionario.objects.count() == qtd_func_antes + 1)
    checa('Novo funcionário recebe is_staff=True',
          nova is not None and nova.usuario.is_staff)

    # 4.4 Tenta adicionar funcionário com e-mail duplicado (deve recusar)
    qtd_func = Funcionario.objects.count()
    resp = c.post(reverse('dashboard_admin'), {
        'add_funcionario': '1',
        'first_name': 'Outra',
        'last_name': 'Pessoa',
        'email': 'patricia@sim.salao',  # já existe
        'celular': '11900000098',
        'especializacao': 'Maquiadora',
        'esta_ativo': 'on',
    })
    checa('E-mail duplicado é recusado (sem 500)',
          resp.status_code == 200 and Funcionario.objects.count() == qtd_func,
          'nenhum funcionário duplicado criado')


# -------------------------------------------------------------------------
# 5. Regras de negócio na camada de serviços (casos de borda)
# -------------------------------------------------------------------------
def regras_negocio(profissionais, servicos):
    secao('5. REGRAS DE NEGÓCIO (camada de serviços / casos de borda)')
    joana = profissionais[0]
    corte = servicos[0]
    cliente = ClienteProfile.objects.get(usuario__email='mariana@sim.salao')

    # 5.1 Fora do expediente (07h, antes das 09h)
    try:
        criar_agendamento(
            profissional_id=joana.pk, servico_id=corte.pk, cliente_id=cliente.pk,
            hora_de_inicio=_proximo_dia_semana(0, hora=7),
        )
        checa('Agendamento fora do expediente é bloqueado', False, 'NÃO bloqueou')
    except ValidationError as e:
        checa('Agendamento fora do expediente é bloqueado', True, e.messages[0])

    # 5.2 Dia sem jornada (sábado=5)
    try:
        criar_agendamento(
            profissional_id=joana.pk, servico_id=corte.pk, cliente_id=cliente.pk,
            hora_de_inicio=_proximo_dia_semana(5, hora=10),
        )
        checa('Agendamento em dia sem jornada é bloqueado', False, 'NÃO bloqueou')
    except ValidationError as e:
        checa('Agendamento em dia sem jornada é bloqueado', True, e.messages[0])

    # 5.3 Criar e depois EDITAR um agendamento (troca de horário)
    h1 = _proximo_dia_semana(1, hora=11)   # terça 11h
    ag = criar_agendamento(
        profissional_id=joana.pk, servico_id=corte.pk, cliente_id=cliente.pk,
        hora_de_inicio=h1,
    )
    checa('Agendamento de teste criado para edição', ag.status == 'PENDENTE')

    h2 = _proximo_dia_semana(1, hora=15)   # terça 15h
    ag_edit = editar_agendamento(
        agendamento_id=ag.pk, novo_profissional_id=joana.pk,
        novo_servico_id=corte.pk, nova_hora_de_inicio=h2,
    )
    checa('Edição move o horário corretamente',
          ag_edit.data_hora_inicio == h2,
          timezone.localtime(ag_edit.data_hora_inicio).strftime('%d/%m %H:%M'))

    # 5.4 gerar_horarios_disponiveis exclui horários já ocupados
    dias = gerar_horarios_disponiveis(joana.pk, corte.pk)
    # Procura a terça e confirma que 15h NÃO está mais livre
    ocupado_aparece_livre = False
    alvo = timezone.localtime(h2)
    for d in dias:
        if d['data'] == alvo.date().isoformat():
            horas = [h['hora'] for h in d['horarios']]
            if '15:00' in horas:
                ocupado_aparece_livre = True
    checa('Horário ocupado some das vagas disponíveis', not ocupado_aparece_livre,
          'API não oferece 15:00 já reservado')


# -------------------------------------------------------------------------
# Execução
# -------------------------------------------------------------------------
def main() -> None:
    print('\n' + '#' * 70)
    print('#  SIMULAÇÃO DE USO REAL — Salão Eduarda Ferraz')
    print('#' * 70)

    limpar_dados_simulacao()
    _admin, profissionais, servicos = montar_salao()
    cliente_user = cadastrar_cliente_via_http()
    fluxo_cliente(cliente_user, profissionais, servicos)
    fluxo_admin()
    regras_negocio(profissionais, servicos)

    secao('RESUMO FINAL')
    total = _total['ok'] + _total['falha']
    print(f'  Verificações executadas : {total}')
    print(f'  [OK]    aprovadas        : {_total["ok"]}')
    print(f'  [FALHA] reprovadas       : {_total["falha"]}')
    print('\n  Estado final do banco (dados persistidos para inspeção):')
    print(f'    Funcionários : {Funcionario.objects.count()}')
    print(f'    Serviços     : {Servico.objects.count()}')
    print(f'    Clientes     : {ClienteProfile.objects.count()}')
    print(f'    Agendamentos : {Agendamento.objects.count()} '
          f'(ativos={Agendamento.objects.filter(status__in=["PENDENTE","CONFIRMADO"]).count()}, '
          f'cancelados={Agendamento.objects.filter(status="CANCELADO").count()})')

    if _total['falha'] == 0:
        print('\n  >>> SIMULAÇÃO CONCLUÍDA: todos os passos passaram. <<<\n')
    else:
        print('\n  >>> ATENÇÃO: houve falhas na simulação (ver acima). <<<\n')
        sys.exit(1)


if __name__ == '__main__':
    main()
