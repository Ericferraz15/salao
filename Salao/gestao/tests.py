import tempfile
from datetime import datetime, timedelta, timezone as dt_timezone
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase, Client as HttpClient, override_settings
from django.urls import reverse
from django.utils import timezone

# pyrefly: ignore [missing-import]
from .models import (
    ClienteProfile,
    Funcionario,
    JornadaTrabalho,
    Servico,
    Agendamento,
    TransacaoFinanceira,
)

# pyrefly: ignore [missing-import]
from .services.agendaService import (
    criar_agendamento,
    cancelar_agendamento,
    confirmar_agendamento,
    concluir_agendamento,
    marcar_no_show,
    editar_agendamento,
    gerar_horarios_disponiveis,
    verificar_disponibilidade,
)
# pyrefly: ignore [missing-import]
from .services.cadastroService import ClienteRegistrationForm
# pyrefly: ignore [missing-import]
from .services.financeiroService import (
    lancar_transacao,
    receita_por_dia,
    resumo_financeiro,
)
# pyrefly: ignore [missing-import]
from .services.estoqueService import ajustar_estoque
# pyrefly: ignore [missing-import]
from .forms import FuncionarioForm, JornadaForm, ServicoForm
# pyrefly: ignore [missing-import]
from .models import Produto

Usuario = get_user_model()


def proxima_segunda_10h():
    """Próxima segunda-feira às 10h (datetime aware, fuso SP). Sempre futuro."""
    hoje = timezone.localtime(timezone.now())
    dias = (7 - hoje.weekday()) % 7 or 7
    return (hoje + timedelta(days=dias)).replace(
        hour=10, minute=0, second=0, microsecond=0,
    )


class UsuarioEPerfilTests(TestCase):
    """Testes de criação de usuário e perfil de cliente."""

    def test_criar_usuario_basico(self) -> None:
        user = Usuario.objects.create_user(
            username='maria',
            password='Senha@Forte1',
            first_name='Maria',
            last_name='Silva',
            email='maria@teste.com',
            celular='11999990000',
        )
        self.assertEqual(str(user), 'Maria Silva')
        self.assertTrue(user.check_password('Senha@Forte1'))

    def test_email_unico(self) -> None:
        Usuario.objects.create_user(
            username='u1', password='abc12345', email='dup@teste.com', celular='11000000001',
        )
        with self.assertRaises(Exception):
            Usuario.objects.create_user(
                username='u2', password='abc12345', email='dup@teste.com', celular='11000000002',
            )

    def test_celular_unico(self) -> None:
        Usuario.objects.create_user(
            username='u1', password='abc12345', email='a@t.com', celular='11999990001',
        )
        with self.assertRaises(Exception):
            Usuario.objects.create_user(
                username='u2', password='abc12345', email='b@t.com', celular='11999990001',
            )

    def test_cliente_profile_criado(self) -> None:
        user = Usuario.objects.create_user(
            username='ana', password='abc12345', email='ana@t.com', celular='11999990003',
        )
        profile = ClienteProfile.objects.create(usuario=user)
        self.assertEqual(str(profile), user.get_full_name())

    def test_form_registro_valido(self) -> None:
        form = ClienteRegistrationForm(data={
            'username': 'novousuario',
            'first_name': 'Novo',
            'last_name': 'Usuario',
            'email': 'novo@teste.com',
            'celular': '(11) 99999-0000',
            'password1': 'SenhaForte@123',
            'password2': 'SenhaForte@123',
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_registro_email_duplicado(self) -> None:
        Usuario.objects.create_user(
            username='existente', password='abc12345', email='dup@teste.com', celular='11000000010',
        )
        form = ClienteRegistrationForm(data={
            'username': 'outro',
            'first_name': 'Outro',
            'last_name': 'User',
            'email': 'dup@teste.com',
            'celular': '(11) 99999-1111',
            'password1': 'SenhaForte@123',
            'password2': 'SenhaForte@123',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_form_registro_celular_invalido(self) -> None:
        form = ClienteRegistrationForm(data={
            'username': 'user1',
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@teste.com',
            'celular': '123',
            'password1': 'SenhaForte@123',
            'password2': 'SenhaForte@123',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('celular', form.errors)

    def test_form_registro_first_name_longo_invalido(self) -> None:
        """first_name > 30 é barrado na validação do ModelForm (Usuario.first_name=30
        está em Meta.fields, então _post_clean valida contra o model). Documenta o
        limite e o mantém alinhado ao max_length declarado no form."""
        form = ClienteRegistrationForm(data={
            'username': 'userlong',
            'first_name': 'A' * 31,
            'last_name': 'User',
            'email': 'long@teste.com',
            'celular': '(11) 99999-2222',
            'password1': 'SenhaForte@123',
            'password2': 'SenhaForte@123',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('first_name', form.errors)


class AgendamentoServiceTests(TestCase):
    """Testes da lógica de agendamento."""

    def setUp(self) -> None:
        self.user_pro = Usuario.objects.create_user(
            username='pro1', password='abc12345',
            email='pro@t.com', celular='11000000020',
        )
        self.funcionario = Funcionario.objects.create(
            usuario=self.user_pro, especializacao='Cabeleireira', esta_ativo=True,
        )

        self.servico = Servico.objects.create(
            nome='Corte Feminino', descricao='Corte simples',
            duracao_minutos=60, preco=80.00,
        )

        self.user_cli = Usuario.objects.create_user(
            username='cli1', password='abc12345',
            email='cli@t.com', celular='11000000030',
        )
        self.cliente = ClienteProfile.objects.create(usuario=self.user_cli)

        # Jornada: segunda a sexta, 09h-18h
        for dia in range(5):
            JornadaTrabalho.objects.create(
                funcionario=self.funcionario,
                dia_da_semana=dia,
                hora_inicio='09:00',
                hora_fim='18:00',
            )

    def _proxima_segunda(self):
        """Retorna a próxima segunda-feira às 10h como datetime aware (fuso SP)."""
        hoje = timezone.localtime(timezone.now())
        dias_ate_segunda = (7 - hoje.weekday()) % 7
        if dias_ate_segunda == 0:
            dias_ate_segunda = 7
        segunda = hoje + timedelta(days=dias_ate_segunda)
        segunda_10h = segunda.replace(hour=10, minute=0, second=0, microsecond=0)
        return segunda_10h

    def test_criar_agendamento_sucesso(self) -> None:
        hora = self._proxima_segunda()
        ag = criar_agendamento(
            profissional_id=self.funcionario.pk,
            servico_id=self.servico.pk,
            cliente_id=self.cliente.pk,
            hora_de_inicio=hora,
        )
        self.assertEqual(ag.status, 'PENDENTE')
        self.assertEqual(ag.valor_cobrado, self.servico.preco)
        self.assertEqual(ag.data_hora_fim, hora + timedelta(minutes=60))

    def test_conflito_horario(self) -> None:
        hora = self._proxima_segunda()
        criar_agendamento(
            profissional_id=self.funcionario.pk,
            servico_id=self.servico.pk,
            cliente_id=self.cliente.pk,
            hora_de_inicio=hora,
        )
        with self.assertRaises(ValidationError):
            criar_agendamento(
                profissional_id=self.funcionario.pk,
                servico_id=self.servico.pk,
                cliente_id=self.cliente.pk,
                hora_de_inicio=hora + timedelta(minutes=30),
            )

    def test_fora_do_expediente(self) -> None:
        segunda = self._proxima_segunda().replace(hour=7, minute=0)
        with self.assertRaises(ValidationError):
            criar_agendamento(
                profissional_id=self.funcionario.pk,
                servico_id=self.servico.pk,
                cliente_id=self.cliente.pk,
                hora_de_inicio=segunda,
            )

    def test_dia_sem_jornada(self) -> None:
        """Sábado (dia 5) não tem jornada cadastrada."""
        hoje = timezone.localtime(timezone.now())
        dias_ate_sabado = (5 - hoje.weekday()) % 7
        if dias_ate_sabado == 0:
            dias_ate_sabado = 7
        sabado = (hoje + timedelta(days=dias_ate_sabado)).replace(
            hour=10, minute=0, second=0, microsecond=0,
        )
        with self.assertRaises(ValidationError):
            criar_agendamento(
                profissional_id=self.funcionario.pk,
                servico_id=self.servico.pk,
                cliente_id=self.cliente.pk,
                hora_de_inicio=sabado,
            )

    def test_cancelar_agendamento(self) -> None:
        hora = self._proxima_segunda()
        ag = criar_agendamento(
            profissional_id=self.funcionario.pk,
            servico_id=self.servico.pk,
            cliente_id=self.cliente.pk,
            hora_de_inicio=hora,
        )
        ag_cancelado = cancelar_agendamento(ag.pk)
        self.assertEqual(ag_cancelado.status, 'CANCELADO')

    def test_cancelar_agendamento_ja_cancelado(self) -> None:
        hora = self._proxima_segunda()
        ag = criar_agendamento(
            profissional_id=self.funcionario.pk,
            servico_id=self.servico.pk,
            cliente_id=self.cliente.pk,
            hora_de_inicio=hora,
        )
        cancelar_agendamento(ag.pk)
        with self.assertRaises(ValidationError):
            cancelar_agendamento(ag.pk)

    def test_profissional_inexistente(self) -> None:
        with self.assertRaises(ValidationError):
            verificar_disponibilidade(
                profissional_id=9999,
                servico_id=self.servico.pk,
                hora_de_inicio=self._proxima_segunda(),
            )

    def test_servico_inexistente(self) -> None:
        with self.assertRaises(ValidationError):
            verificar_disponibilidade(
                profissional_id=self.funcionario.pk,
                servico_id=9999,
                hora_de_inicio=self._proxima_segunda(),
            )

    def test_agendamento_no_passado_bloqueado(self) -> None:
        """Regressão: a camada de serviço não pode aceitar horário passado."""
        ontem_10h = (timezone.localtime(timezone.now()) - timedelta(days=1)).replace(
            hour=10, minute=0, second=0, microsecond=0,
        )
        with self.assertRaises(ValidationError):
            criar_agendamento(
                profissional_id=self.funcionario.pk,
                servico_id=self.servico.pk,
                cliente_id=self.cliente.pk,
                hora_de_inicio=ontem_10h,
            )


class PermissaoViewTests(TestCase):
    """Testes de acesso/permissão nas views."""

    def test_agendar_redireciona_sem_login(self) -> None:
        client = HttpClient()
        response = client.get(reverse('criar_agendamento'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_dashboard_redireciona_sem_login(self) -> None:
        client = HttpClient()
        response = client.get(reverse('dashboard_cliente'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_home_acessivel_sem_login(self) -> None:
        client = HttpClient()
        response = client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)

    def test_cadastro_acessivel_sem_login(self) -> None:
        client = HttpClient()
        response = client.get(reverse('cadastro_cliente'))
        self.assertEqual(response.status_code, 200)

    def test_cadastro_redireciona_usuario_logado(self) -> None:
        Usuario.objects.create_user(
            username='logado', password='abc12345',
            email='logado@t.com', celular='11000000040',
        )
        client = HttpClient()
        client.login(username='logado', password='abc12345')
        response = client.get(reverse('cadastro_cliente'))
        self.assertEqual(response.status_code, 302)


class ApiHorariosDisponiveisTests(TestCase):
    """Testes do endpoint de horários disponíveis."""

    def setUp(self) -> None:
        self.user = Usuario.objects.create_user(
            username='api_user', password='abc12345',
            email='api@t.com', celular='11000000050',
        )
        self.client_http = HttpClient()
        self.client_http.login(username='api_user', password='abc12345')

        self.user_pro = Usuario.objects.create_user(
            username='pro_api', password='abc12345',
            email='pro_api@t.com', celular='11000000060',
        )
        self.funcionario = Funcionario.objects.create(
            usuario=self.user_pro, especializacao='Manicure', esta_ativo=True,
        )
        self.servico = Servico.objects.create(
            nome='Manicure', descricao='Unha gel',
            duracao_minutos=30, preco=50.00,
        )
        for dia in range(5):
            JornadaTrabalho.objects.create(
                funcionario=self.funcionario,
                dia_da_semana=dia,
                hora_inicio='09:00',
                hora_fim='18:00',
            )

    def test_parametros_incompletos(self) -> None:
        response = self.client_http.get(reverse('api_horarios_disponiveis'))
        self.assertEqual(response.status_code, 400)

    def test_retorna_dias(self) -> None:
        url = reverse('api_horarios_disponiveis')
        response = self.client_http.get(url, {
            'profissional_id': self.funcionario.pk,
            'servico_id': self.servico.pk,
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('dias', data)

    def test_sem_login_redireciona(self) -> None:
        client = HttpClient()
        response = client.get(reverse('api_horarios_disponiveis'))
        self.assertEqual(response.status_code, 302)


class DashboardAdminTimezoneTests(TestCase):
    """Regressão: as métricas do painel usam o horário LOCAL, não UTC."""

    def setUp(self) -> None:
        self.admin = Usuario.objects.create_superuser(
            username='boss', password='abc12345',
            email='boss@t.com', celular='11000000099',
        )
        self.http = HttpClient()
        self.http.login(username='boss', password='abc12345')

        user_pro = Usuario.objects.create_user(
            username='proz', password='abc12345',
            email='proz@t.com', celular='11000000098',
        )
        self.func = Funcionario.objects.create(
            usuario=user_pro, especializacao='Manicure', esta_ativo=True,
        )
        user_cli = Usuario.objects.create_user(
            username='cliz', password='abc12345',
            email='cliz@t.com', celular='11000000097',
        )
        self.cliente = ClienteProfile.objects.create(usuario=user_cli)
        self.servico = Servico.objects.create(
            nome='Corte', descricao='x', duracao_minutos=60, preco=80.00,
        )

    @patch('gestao.Controller.dashboardController.timezone.now')
    def test_agendamentos_hoje_usa_data_local(self, mock_now) -> None:
        # 15/06 00:30 UTC == 14/06 21:30 em São Paulo (UTC-3).
        # "Hoje" local é 14/06; usar a data de UTC contaria o dia errado.
        mock_now.return_value = datetime(2026, 6, 15, 0, 30, tzinfo=dt_timezone.utc)

        inicio_local = timezone.make_aware(datetime(2026, 6, 14, 10, 0))
        Agendamento.objects.create(
            cliente=self.cliente, profissional=self.func, servico=self.servico,
            data_hora_inicio=inicio_local,
            data_hora_fim=inicio_local + timedelta(minutes=60),
            status='PENDENTE', valor_cobrado=self.servico.preco,
        )

        response = self.http.get(reverse('dashboard_admin'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['agendamentos_hoje'], 1)


class CriarAgendamentoControllerTests(TestCase):
    """Garante que entrada de data inválida é tratada com mensagem amigável."""

    def setUp(self) -> None:
        self.user = Usuario.objects.create_user(
            username='cform', password='abc12345',
            email='cform@t.com', celular='11000000088',
        )
        ClienteProfile.objects.create(usuario=self.user)
        self.http = HttpClient()
        self.http.login(username='cform', password='abc12345')

    def test_post_data_invalida_redireciona_com_erro(self) -> None:
        response = self.http.post(reverse('criar_agendamento'), {
            'profissionalId': '1',
            'servicoId': '1',
            'hora_de_inicio': 'data-invalida',
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        mensagens = [str(m) for m in response.context['messages']]
        self.assertTrue(any('inválido' in m for m in mensagens), mensagens)


class _BaseAgenda(TestCase):
    """Cenário comum: 1 profissional (seg-sex 09-18), 1 serviço (60min), 1 cliente."""

    def setUp(self) -> None:
        self.user_pro = Usuario.objects.create_user(
            username='p', password='abc12345', email='p@t.com', celular='12000000001',
        )
        self.func = Funcionario.objects.create(
            usuario=self.user_pro, especializacao='Nail', esta_ativo=True,
        )
        self.servico = Servico.objects.create(
            nome='Gel', descricao='x', duracao_minutos=60, preco=100.00,
        )
        self.user_cli = Usuario.objects.create_user(
            username='cl', password='abc12345', email='cl@t.com', celular='12000000002',
        )
        self.cliente = ClienteProfile.objects.create(usuario=self.user_cli)
        for dia in range(5):
            JornadaTrabalho.objects.create(
                funcionario=self.func, dia_da_semana=dia,
                hora_inicio='09:00', hora_fim='18:00',
            )

    def _novo_agendamento(self, hora=None):
        return criar_agendamento(
            profissional_id=self.func.pk, servico_id=self.servico.pk,
            cliente_id=self.cliente.pk, hora_de_inicio=hora or proxima_segunda_10h(),
        )


class TransicoesStatusServiceTests(_BaseAgenda):
    """Confirmar / concluir (receita) / no-show e suas pré-condições."""

    def test_confirmar(self) -> None:
        ag = self._novo_agendamento()
        self.assertEqual(confirmar_agendamento(ag.pk).status, 'CONFIRMADO')

    def test_confirmar_apenas_pendente(self) -> None:
        ag = self._novo_agendamento()
        confirmar_agendamento(ag.pk)
        with self.assertRaises(ValidationError):
            confirmar_agendamento(ag.pk)

    def test_concluir_lanca_uma_receita(self) -> None:
        ag = self._novo_agendamento()
        concluir_agendamento(ag.pk)
        ag.refresh_from_db()
        self.assertEqual(ag.status, 'CONCLUIDO')
        entradas = TransacaoFinanceira.objects.filter(tipo='ENTRADA', agendamento=ag)
        self.assertEqual(entradas.count(), 1)
        self.assertEqual(entradas.first().valor, ag.valor_cobrado)

    def test_concluir_idempotente_nao_duplica_receita(self) -> None:
        ag = self._novo_agendamento()
        concluir_agendamento(ag.pk)
        with self.assertRaises(ValidationError):
            concluir_agendamento(ag.pk)  # status já é CONCLUIDO
        self.assertEqual(
            TransacaoFinanceira.objects.filter(agendamento=ag, tipo='ENTRADA').count(), 1,
        )

    def test_no_show(self) -> None:
        ag = self._novo_agendamento()
        self.assertEqual(marcar_no_show(ag.pk).status, 'NO_SHOW')

    def test_no_show_nao_vale_para_concluido(self) -> None:
        ag = self._novo_agendamento()
        concluir_agendamento(ag.pk)
        with self.assertRaises(ValidationError):
            marcar_no_show(ag.pk)

    def test_cancelar_nao_vale_para_concluido(self) -> None:
        ag = self._novo_agendamento()
        concluir_agendamento(ag.pk)
        with self.assertRaises(ValidationError):
            cancelar_agendamento(ag.pk)


class EditarAgendamentoServiceTests(_BaseAgenda):
    """Reagendamento: move horário, detecta conflito e ignora a si mesmo."""

    def test_editar_move_horario(self) -> None:
        ag = self._novo_agendamento(proxima_segunda_10h())
        nova = proxima_segunda_10h().replace(hour=14)
        out = editar_agendamento(ag.pk, self.func.pk, self.servico.pk, nova)
        self.assertEqual(out.data_hora_inicio, nova)
        self.assertEqual(out.data_hora_fim, nova + timedelta(minutes=60))

    def test_editar_detecta_conflito(self) -> None:
        h1 = proxima_segunda_10h()
        self._novo_agendamento(h1)                    # 10h-11h
        ag2 = self._novo_agendamento(h1.replace(hour=14))  # 14h-15h
        with self.assertRaises(ValidationError):
            editar_agendamento(ag2.pk, self.func.pk, self.servico.pk, h1)

    def test_editar_ignora_o_proprio(self) -> None:
        h1 = proxima_segunda_10h()
        ag = self._novo_agendamento(h1)
        out = editar_agendamento(ag.pk, self.func.pk, self.servico.pk, h1)
        self.assertEqual(out.data_hora_inicio, h1)

    def test_nao_edita_concluido(self) -> None:
        ag = self._novo_agendamento()
        concluir_agendamento(ag.pk)
        with self.assertRaises(ValidationError):
            editar_agendamento(
                ag.pk, self.func.pk, self.servico.pk,
                proxima_segunda_10h().replace(hour=15),
            )


class GerarHorariosDisponiveisTests(_BaseAgenda):
    """Geração de slots: exclui ocupados e trata entradas inválidas."""

    def test_exclui_horario_ocupado(self) -> None:
        h = proxima_segunda_10h()
        self._novo_agendamento(h)  # ocupa 10:00-11:00
        dias = gerar_horarios_disponiveis(self.func.pk, self.servico.pk)
        alvo = timezone.localtime(h).date().isoformat()
        dia = next((d for d in dias if d['data'] == alvo), None)
        self.assertIsNotNone(dia)
        horas = [x['hora'] for x in dia['horarios']]
        self.assertNotIn('10:00', horas)  # exatamente ocupado
        self.assertNotIn('10:30', horas)  # sobreposto pelo serviço de 60min

    def test_profissional_sem_jornada_retorna_vazio(self) -> None:
        u = Usuario.objects.create_user(
            username='semj', password='abc12345', email='semj@t.com', celular='12000000009',
        )
        f = Funcionario.objects.create(usuario=u, especializacao='X', esta_ativo=True)
        self.assertEqual(gerar_horarios_disponiveis(f.pk, self.servico.pk), [])

    def test_ids_inexistentes_retornam_vazio(self) -> None:
        self.assertEqual(gerar_horarios_disponiveis(99999, self.servico.pk), [])
        self.assertEqual(gerar_horarios_disponiveis(self.func.pk, 99999), [])


class GerenciarAgendamentoAdminTests(_BaseAgenda):
    """Ações do admin sobre agendamentos via HTTP + permissão."""

    def setUp(self) -> None:
        super().setUp()
        self.admin = Usuario.objects.create_superuser(
            username='adm', password='abc12345', email='adm@t.com', celular='12000000003',
        )
        self.http = HttpClient()
        self.http.login(username='adm', password='abc12345')
        self.ag = self._novo_agendamento()

    def _post(self, acao):
        return self.http.post(
            reverse('gerenciar_agendamento', args=[self.ag.pk]),
            {'acao': acao}, follow=True,
        )

    def test_confirmar_via_http(self) -> None:
        resp = self._post('confirmar')
        self.ag.refresh_from_db()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.ag.status, 'CONFIRMADO')

    def test_concluir_via_http_lanca_receita_e_metrica(self) -> None:
        self._post('concluir')
        self.ag.refresh_from_db()
        self.assertEqual(self.ag.status, 'CONCLUIDO')
        self.assertEqual(
            TransacaoFinanceira.objects.filter(agendamento=self.ag, tipo='ENTRADA').count(), 1,
        )
        resp = self.http.get(reverse('dashboard_admin'))
        self.assertEqual(resp.context['receita_mes'], self.ag.valor_cobrado)

    def test_acao_invalida(self) -> None:
        resp = self._post('explodir')
        msgs = [str(m).lower() for m in resp.context['messages']]
        self.assertTrue(any('inválida' in m for m in msgs), msgs)

    def test_get_redireciona(self) -> None:
        resp = self.http.get(reverse('gerenciar_agendamento', args=[self.ag.pk]))
        self.assertEqual(resp.status_code, 302)

    def test_nao_admin_bloqueado(self) -> None:
        c = HttpClient()
        c.login(username='cl', password='abc12345')  # cliente comum
        resp = c.post(
            reverse('gerenciar_agendamento', args=[self.ag.pk]), {'acao': 'confirmar'},
        )
        self.assertEqual(resp.status_code, 302)
        self.ag.refresh_from_db()
        self.assertEqual(self.ag.status, 'PENDENTE')  # nada mudou

    def test_cancelar_via_http(self) -> None:
        self._post('cancelar')
        self.ag.refresh_from_db()
        self.assertEqual(self.ag.status, 'CANCELADO')

    def test_no_show_via_http(self) -> None:
        self._post('no_show')
        self.ag.refresh_from_db()
        self.assertEqual(self.ag.status, 'NO_SHOW')

    def test_acao_em_concluido_mostra_erro_sem_alterar(self) -> None:
        concluir_agendamento(self.ag.pk)  # vira CONCLUIDO
        resp = self._post('cancelar')     # não se cancela um concluído
        self.ag.refresh_from_db()
        self.assertEqual(self.ag.status, 'CONCLUIDO')  # inalterado
        msgs = [str(m).lower() for m in resp.context['messages']]
        self.assertTrue(any('não pode' in m for m in msgs), msgs)


class CancelarAgendamentoClienteTests(_BaseAgenda):
    """Autorização: cliente não pode cancelar agendamento de outro cliente."""

    def test_cliente_nao_cancela_de_outro(self) -> None:
        ag = self._novo_agendamento()  # pertence a self.cliente
        outro = Usuario.objects.create_user(
            username='outro', password='abc12345', email='outro@t.com', celular='12000000004',
        )
        ClienteProfile.objects.create(usuario=outro)
        c = HttpClient()
        c.login(username='outro', password='abc12345')
        resp = c.post(reverse('cancelar_agendamento', args=[ag.pk]), follow=True)
        ag.refresh_from_db()
        self.assertEqual(ag.status, 'PENDENTE')  # não foi cancelado
        msgs = [str(m).lower() for m in resp.context['messages']]
        self.assertTrue(any('não encontrado' in m for m in msgs), msgs)


class DashboardAdminCadastrosTests(_BaseAgenda):
    """Cadastro de serviço e profissional pelo painel (HTTP)."""

    def setUp(self) -> None:
        super().setUp()
        self.admin = Usuario.objects.create_superuser(
            username='adm2', password='abc12345', email='adm2@t.com', celular='12000000005',
        )
        self.http = HttpClient()
        self.http.login(username='adm2', password='abc12345')

    def test_add_servico(self) -> None:
        n = Servico.objects.count()
        resp = self.http.post(reverse('dashboard_admin'), {
            'add_servico': '1', 'nome': 'Spa', 'descricao': 'd',
            'duracao_minutos': 30, 'preco': '45.00',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Servico.objects.count(), n + 1)

    def test_add_funcionario_cria_staff(self) -> None:
        resp = self.http.post(reverse('dashboard_admin'), {
            'add_funcionario': '1', 'first_name': 'Ana', 'last_name': 'Paula',
            'email': 'ana.nova@t.com', 'celular': '12999990000',
            'especializacao': 'Manicure', 'esta_ativo': 'on',
        })
        self.assertEqual(resp.status_code, 302)
        u = Usuario.objects.filter(email='ana.nova@t.com').first()
        self.assertIsNotNone(u)
        self.assertTrue(u.is_staff)
        self.assertTrue(Funcionario.objects.filter(usuario=u).exists())

    def test_add_funcionario_email_duplicado_recusado(self) -> None:
        Usuario.objects.create_user(
            username='dup', password='abc12345', email='dup@t.com', celular='12999990001',
        )
        n = Funcionario.objects.count()
        resp = self.http.post(reverse('dashboard_admin'), {
            'add_funcionario': '1', 'first_name': 'X', 'last_name': 'Y',
            'email': 'dup@t.com', 'celular': '12999990002',
            'especializacao': 'M', 'esta_ativo': 'on',
        })
        self.assertEqual(resp.status_code, 200)  # re-renderiza com erro
        self.assertEqual(Funcionario.objects.count(), n)


class FuncionarioFormTests(TestCase):
    """Regressão: o e-mail do FuncionarioForm precisa respeitar o limite do model.

    email é um campo *declarado* (não pertence ao model Funcionario), então não há
    _post_clean validando contra Usuario.email (max_length=100). Sem max_length no
    form, um e-mail acima de 100 caracteres passaria e quebraria o INSERT no
    PostgreSQL ('value too long').
    """

    def test_email_acima_de_100_invalido(self) -> None:
        email_longo = 'a' * 90 + '@example.com'  # 102 caracteres, formato válido
        self.assertGreater(len(email_longo), 100)
        form = FuncionarioForm(data={
            'first_name': 'Ana', 'last_name': 'Lima',
            'email': email_longo, 'celular': '11999990000',
            'especializacao': 'Manicure', 'esta_ativo': True,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_email_dentro_do_limite_valido(self) -> None:
        form = FuncionarioForm(data={
            'first_name': 'Ana', 'last_name': 'Lima',
            'email': 'ana@example.com', 'celular': '11999990000',
            'especializacao': 'Manicure', 'esta_ativo': True,
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_email_normalizado_para_minusculas(self) -> None:
        form = FuncionarioForm(data={
            'first_name': 'Ana', 'last_name': 'Lima',
            'email': '  Ana.Lima@EXEMPLO.com ', 'celular': '11999990000',
            'especializacao': 'Manicure', 'esta_ativo': True,
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['email'], 'ana.lima@exemplo.com')


class CriarAgendamentoSucessoControllerTests(_BaseAgenda):
    """Após agendar com sucesso, o cliente cai em 'Meus Agendamentos' e vê a
    confirmação (a home não renderiza mensagens, então redirecionar para lá
    perderia o feedback)."""

    def test_post_valido_redireciona_para_dashboard_com_mensagem(self) -> None:
        http = HttpClient()
        http.login(username='cl', password='abc12345')
        hora = proxima_segunda_10h().strftime('%Y-%m-%dT%H:%M')
        resp = http.post(reverse('criar_agendamento'), {
            'profissionalId': self.func.pk,
            'servicoId': self.servico.pk,
            'hora_de_inicio': hora,
        }, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.request['PATH_INFO'], reverse('dashboard_cliente'))
        msgs = [str(m).lower() for m in resp.context['messages']]
        self.assertTrue(any('sucesso' in m for m in msgs), msgs)
        self.assertEqual(resp.context['ativos'].count(), 1)


class CadastroSucessoControllerTests(TestCase):
    """Após cadastrar, o cliente é logado, cai em 'Meus Agendamentos' e vê a
    saudação (a home não renderiza mensagens)."""

    def test_cadastro_valido_loga_e_mostra_boas_vindas(self) -> None:
        http = HttpClient()
        resp = http.post(reverse('cadastro_cliente'), {
            'username': 'novacliente',
            'first_name': 'Nova', 'last_name': 'Cliente',
            'email': 'nova@teste.com', 'celular': '(11) 98888-0000',
            'password1': 'SenhaForte@123', 'password2': 'SenhaForte@123',
        }, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.request['PATH_INFO'], reverse('dashboard_cliente'))
        msgs = [str(m).lower() for m in resp.context['messages']]
        self.assertTrue(any('bem-vindo' in m for m in msgs), msgs)

    def test_cadastro_e_atomico_rollback_se_perfil_falha(self) -> None:
        """Se a criação do ClienteProfile falha, o Usuario é desfeito (atomic)."""
        http = HttpClient()
        with patch.object(ClienteProfile.objects, 'create', side_effect=RuntimeError('boom')):
            with self.assertRaises(RuntimeError):
                http.post(reverse('cadastro_cliente'), {
                    'username': 'rollback', 'first_name': 'Roll', 'last_name': 'Back',
                    'email': 'rollback@teste.com', 'celular': '(11) 97777-0000',
                    'password1': 'SenhaForte@123', 'password2': 'SenhaForte@123',
                })
        self.assertFalse(Usuario.objects.filter(email='rollback@teste.com').exists())


class CadastroSimplificadoTests(TestCase):
    """Cadastro sem campo de username, senha simples (6+) e login por e-mail."""

    DADOS = {
        'first_name': 'Julia', 'last_name': 'Ramos',
        'email': 'julia@teste.com', 'celular': '(11) 98888-7777',
        'password1': '123456', 'password2': '123456',
    }

    def _form(self, **override):
        dados = {**self.DADOS, **override}
        return ClienteRegistrationForm(data=dados)

    def test_formulario_nao_tem_campo_username(self) -> None:
        self.assertNotIn('username', ClienteRegistrationForm().fields)

    def test_senha_simples_de_6_caracteres_aceita(self) -> None:
        form = self._form()
        self.assertTrue(form.is_valid(), form.errors)

    def test_senha_com_5_caracteres_recusada(self) -> None:
        form = self._form(password1='12345', password2='12345')
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)

    def test_username_vira_o_email(self) -> None:
        form = self._form()
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(user.username, 'julia@teste.com')

    def test_celular_gravado_so_com_digitos(self) -> None:
        form = self._form()
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(user.celular, '11988887777')

    def test_celular_duplicado_com_formatacao_diferente_recusado(self) -> None:
        """'(11) 98888-7777' e '11 98888 7777' são o MESMO número."""
        primeira = self._form()
        self.assertTrue(primeira.is_valid(), primeira.errors)
        primeira.save()

        form = self._form(email='outra@teste.com', celular='11 98888 7777')
        self.assertFalse(form.is_valid())
        self.assertIn('celular', form.errors)

    def test_cadastro_http_sem_username_funciona(self) -> None:
        http = HttpClient()
        resp = http.post(reverse('cadastro_cliente'), self.DADOS, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Usuario.objects.filter(email='julia@teste.com').exists())

    def test_login_por_email_para_conta_antiga(self) -> None:
        """Conta com username != e-mail (ex.: 'cliente' do seed) entra pelo e-mail."""
        Usuario.objects.create_user(
            username='antiga', password='abc12345',
            email='antiga@t.com', celular='11977776666',
        )
        http = HttpClient()
        self.assertTrue(http.login(username='antiga@t.com', password='abc12345'))

    def test_login_por_username_continua_funcionando(self) -> None:
        Usuario.objects.create_user(
            username='apelido', password='abc12345',
            email='apelido@t.com', celular='11977776665',
        )
        http = HttpClient()
        self.assertTrue(http.login(username='apelido', password='abc12345'))

    def test_login_email_com_senha_errada_falha(self) -> None:
        Usuario.objects.create_user(
            username='segura', password='abc12345',
            email='segura@t.com', celular='11977776664',
        )
        http = HttpClient()
        self.assertFalse(http.login(username='segura@t.com', password='errada'))


class DashboardClienteHistoricoTests(_BaseAgenda):
    """O histórico deve listar o agendamento mais recente primeiro."""

    def _historico(self, quando, status):
        return Agendamento.objects.create(
            cliente=self.cliente, profissional=self.func, servico=self.servico,
            data_hora_inicio=quando, data_hora_fim=quando + timedelta(hours=1),
            status=status, valor_cobrado=self.servico.preco,
        )

    def test_historico_mais_recente_primeiro(self) -> None:
        antigo = self._historico(timezone.make_aware(datetime(2026, 1, 10, 10, 0)), 'CONCLUIDO')
        recente = self._historico(timezone.make_aware(datetime(2026, 3, 20, 10, 0)), 'CANCELADO')

        http = HttpClient()
        http.login(username='cl', password='abc12345')
        resp = http.get(reverse('dashboard_cliente'))

        historico = list(resp.context['historico'])
        self.assertEqual([a.pk for a in historico], [recente.pk, antigo.pk])


class FinanceiroServiceTests(TestCase):
    """Resumo financeiro, gráfico de receita e lançamentos manuais."""

    def _agora(self):
        return timezone.localtime(timezone.now())

    def test_resumo_calcula_receita_despesa_e_lucro(self) -> None:
        lancar_transacao('ENTRADA', '300.00', 'Serviço avulso')
        lancar_transacao('ENTRADA', '200.00', 'Venda de produto')
        lancar_transacao('SAIDA', '150.00', 'Reposição de esmaltes')

        resumo = resumo_financeiro(self._agora())
        self.assertEqual(resumo['receita_mes'], Decimal('500.00'))
        self.assertEqual(resumo['despesa_mes'], Decimal('150.00'))
        self.assertEqual(resumo['lucro_mes'], Decimal('350.00'))
        self.assertEqual(resumo['receita_hoje'], Decimal('500.00'))

    def test_progresso_da_meta_limitado_a_100(self) -> None:
        lancar_transacao('ENTRADA', '999999.00', 'Mês espetacular')
        resumo = resumo_financeiro(self._agora())
        self.assertEqual(resumo['meta_progresso_pct'], 100)
        self.assertTrue(resumo['meta_batida'])

    def test_resumo_zerado_sem_transacoes(self) -> None:
        resumo = resumo_financeiro(self._agora())
        self.assertEqual(resumo['receita_mes'], Decimal('0'))
        self.assertEqual(resumo['lucro_mes'], Decimal('0'))
        self.assertEqual(resumo['meta_progresso_pct'], 0)

    def test_receita_por_dia_tem_um_item_por_dia(self) -> None:
        lancar_transacao('ENTRADA', '100.00', 'Hoje')
        serie = receita_por_dia(self._agora(), dias=7)
        self.assertEqual(len(serie), 7)
        # O último item é hoje, com o valor lançado e barra no máximo
        self.assertEqual(serie[-1]['data'], self._agora().date())
        self.assertEqual(serie[-1]['total'], Decimal('100.00'))
        self.assertEqual(serie[-1]['altura_pct'], 100)
        # Dias sem receita aparecem zerados (sem "buracos" no gráfico)
        self.assertEqual(serie[0]['total'], Decimal('0'))

    def test_lancar_transacao_valida_entrada(self) -> None:
        with self.assertRaises(ValidationError):
            lancar_transacao('OUTRO', '10.00', 'tipo inválido')
        with self.assertRaises(ValidationError):
            lancar_transacao('SAIDA', '-5.00', 'valor negativo')
        with self.assertRaises(ValidationError):
            lancar_transacao('SAIDA', 'abc', 'valor não numérico')
        with self.assertRaises(ValidationError):
            lancar_transacao('SAIDA', '10.00', '   ')

    def test_lancar_transacao_aceita_virgula(self) -> None:
        t = lancar_transacao('SAIDA', '99,90', 'Compra com vírgula')
        self.assertEqual(t.valor, Decimal('99.90'))


class EstoqueServiceTests(TestCase):
    """Ajuste de estoque com proteção contra quantidade negativa."""

    def setUp(self) -> None:
        self.produto = Produto.objects.create(
            nome='Esmalte', descricao='x', preco=30,
            quantidade_estoque=2, estoque_minimo=3,
        )

    def test_ajuste_positivo_e_negativo(self) -> None:
        ajustar_estoque(self.produto.pk, +5)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade_estoque, 7)

        ajustar_estoque(self.produto.pk, -3)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade_estoque, 4)

    def test_nao_deixa_estoque_negativo(self) -> None:
        with self.assertRaises(ValidationError):
            ajustar_estoque(self.produto.pk, -10)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade_estoque, 2)  # intacto

    def test_produto_inexistente(self) -> None:
        with self.assertRaises(ValidationError):
            ajustar_estoque(99999, 1)

    def test_alerta_abaixo_do_minimo(self) -> None:
        self.assertTrue(self.produto.abaixo_estoque_minimo)   # 2 < 3
        ajustar_estoque(self.produto.pk, +5)
        self.produto.refresh_from_db()
        self.assertFalse(self.produto.abaixo_estoque_minimo)  # 7 >= 3


class PainelAdminCompletoTests(_BaseAgenda):
    """Fluxos HTTP do painel: caixa, produto, jornada e agenda do dia."""

    def setUp(self) -> None:
        super().setUp()
        self.admin = Usuario.objects.create_superuser(
            username='dona', password='abc12345',
            email='dona@t.com', celular='12000000066',
        )
        self.http = HttpClient()
        self.http.login(username='dona', password='abc12345')

    def test_contexto_tem_todas_as_secoes(self) -> None:
        resp = self.http.get(reverse('dashboard_admin'))
        self.assertEqual(resp.status_code, 200)
        for chave in ('agenda_do_dia', 'grafico_receita', 'receita_hoje',
                      'despesa_mes', 'lucro_mes', 'meta_mensal',
                      'meta_progresso_pct', 'produtos', 'transacoes_recentes',
                      'jornadas', 'transacao_form', 'produto_form', 'jornada_form'):
            self.assertIn(chave, resp.context, chave)

    def test_lancar_despesa_pelo_painel(self) -> None:
        resp = self.http.post(reverse('dashboard_admin'), {
            'add_transacao': '1', 'tipo': 'SAIDA',
            'valor': '120.50', 'descricao': 'Aluguel',
        })
        self.assertEqual(resp.status_code, 302)
        t = TransacaoFinanceira.objects.get(descricao='Aluguel')
        self.assertEqual(t.tipo, 'SAIDA')
        self.assertEqual(t.valor, Decimal('120.50'))

    def test_transacao_invalida_reexibe_erros(self) -> None:
        resp = self.http.post(reverse('dashboard_admin'), {
            'add_transacao': '1', 'tipo': 'SAIDA',
            'valor': '-1', 'descricao': 'inválida',
        })
        self.assertEqual(resp.status_code, 200)  # re-renderiza com erro
        self.assertFalse(TransacaoFinanceira.objects.exists())

    def test_add_produto_pelo_painel(self) -> None:
        resp = self.http.post(reverse('dashboard_admin'), {
            'add_produto': '1', 'nome': 'Acetona', 'descricao': 'uso interno',
            'preco': '15.00', 'quantidade_estoque': 10, 'estoque_minimo': 2,
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Produto.objects.filter(nome='Acetona').exists())

    def test_add_jornada_pelo_painel(self) -> None:
        n = JornadaTrabalho.objects.count()
        resp = self.http.post(reverse('dashboard_admin'), {
            'add_jornada': '1', 'funcionario': self.func.pk,
            'dia_da_semana': 5, 'hora_inicio': '09:00', 'hora_fim': '13:00',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(JornadaTrabalho.objects.count(), n + 1)

    def test_jornada_duplicada_recusada(self) -> None:
        n = JornadaTrabalho.objects.count()
        resp = self.http.post(reverse('dashboard_admin'), {
            'add_jornada': '1', 'funcionario': self.func.pk,
            'dia_da_semana': 0,  # segunda já existe no _BaseAgenda
            'hora_inicio': '09:00', 'hora_fim': '13:00',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(JornadaTrabalho.objects.count(), n)

    def test_jornada_fim_antes_do_inicio_recusada(self) -> None:
        form = JornadaForm(data={
            'funcionario': self.func.pk, 'dia_da_semana': 6,
            'hora_inicio': '14:00', 'hora_fim': '09:00',
        })
        self.assertFalse(form.is_valid())

    def test_remover_jornada(self) -> None:
        jornada = JornadaTrabalho.objects.filter(funcionario=self.func).first()
        resp = self.http.post(reverse('remover_jornada', args=[jornada.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(JornadaTrabalho.objects.filter(pk=jornada.pk).exists())

    def test_ajustar_estoque_pelo_painel(self) -> None:
        produto = Produto.objects.create(
            nome='Algodão', descricao='x', preco=5,
            quantidade_estoque=1, estoque_minimo=1,
        )
        self.http.post(reverse('ajustar_estoque', args=[produto.pk]), {'delta': '1'})
        produto.refresh_from_db()
        self.assertEqual(produto.quantidade_estoque, 2)

    def test_agenda_do_dia_mostra_agendamento_de_hoje(self) -> None:
        # Cria um agendamento HOJE direto no banco (pode ser de manhã cedo;
        # o service recusaria horário passado, o que não importa aqui).
        agora = timezone.localtime(timezone.now())
        inicio = agora.replace(hour=9, minute=0, second=0, microsecond=0)
        ag = Agendamento.objects.create(
            cliente=self.cliente, profissional=self.func, servico=self.servico,
            data_hora_inicio=inicio, data_hora_fim=inicio + timedelta(hours=1),
            status='CONFIRMADO', valor_cobrado=self.servico.preco,
        )
        resp = self.http.get(reverse('dashboard_admin'))
        self.assertIn(ag, list(resp.context['agenda_do_dia']))
        # Link de WhatsApp com o celular do cliente aparece na página
        self.assertContains(resp, 'wa.me/55' + self.cliente.usuario.celular_digitos)

    def test_nao_admin_bloqueado_nas_novas_rotas(self) -> None:
        produto = Produto.objects.create(
            nome='Bloqueio', descricao='x', preco=5,
            quantidade_estoque=1, estoque_minimo=1,
        )
        http = HttpClient()
        http.login(username='cl', password='abc12345')  # cliente comum
        resp = http.post(reverse('ajustar_estoque', args=[produto.pk]), {'delta': '1'})
        self.assertEqual(resp.status_code, 302)
        produto.refresh_from_db()
        self.assertEqual(produto.quantidade_estoque, 1)  # nada mudou


# Os testes de foto gravam em um diretório temporário para não sujar o
# media/ real do projeto.
_MEDIA_TESTES = tempfile.mkdtemp(prefix='salao-test-media-')


def _imagem_teste(nome='foto.gif'):
    """Menor GIF válido possível (1x1) — suficiente para o Pillow aceitar."""
    gif_1x1 = (
        b'GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00'
        b'\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
    )
    return SimpleUploadedFile(nome, gif_1x1, content_type='image/gif')


@override_settings(MEDIA_ROOT=_MEDIA_TESTES)
class FotosTests(_BaseAgenda):
    """Fotos de serviço/profissional: upload pelo painel e exibição ao agendar."""

    def setUp(self) -> None:
        super().setUp()
        self.admin = Usuario.objects.create_superuser(
            username='admfoto', password='abc12345',
            email='admfoto@t.com', celular='12000000077',
        )
        self.http_admin = HttpClient()
        self.http_admin.login(username='admfoto', password='abc12345')

    def test_add_servico_com_foto_pelo_painel(self) -> None:
        resp = self.http_admin.post(reverse('dashboard_admin'), {
            'add_servico': '1', 'nome': 'Spa com Foto', 'descricao': 'd',
            'duracao_minutos': 30, 'preco': '45.00',
            'foto': _imagem_teste('spa.gif'),
        })
        self.assertEqual(resp.status_code, 302)
        servico = Servico.objects.get(nome='Spa com Foto')
        self.assertTrue(servico.foto.name.startswith('servicos/'))

    def test_add_funcionario_com_foto_pelo_painel(self) -> None:
        resp = self.http_admin.post(reverse('dashboard_admin'), {
            'add_funcionario': '1', 'first_name': 'Bia', 'last_name': 'Foto',
            'email': 'bia.foto@t.com', 'celular': '12988880000',
            'especializacao': 'Manicure', 'esta_ativo': 'on',
            'foto': _imagem_teste('bia.gif'),
        })
        self.assertEqual(resp.status_code, 302)
        func = Funcionario.objects.get(usuario__email='bia.foto@t.com')
        self.assertTrue(func.foto.name.startswith('equipe/'))

    def test_foto_e_opcional_nos_forms(self) -> None:
        form = ServicoForm(data={
            'nome': 'Sem Foto', 'descricao': 'd',
            'duracao_minutos': 30, 'preco': '10.00',
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_agendar_mostra_placeholder_sem_foto(self) -> None:
        http = HttpClient()
        http.login(username='cl', password='abc12345')
        resp = http.get(reverse('criar_agendamento'))
        self.assertContains(resp, 'foto-placeholder')   # serviço sem foto
        self.assertContains(resp, 'avatar-inicial')      # profissional sem foto

    def test_agendar_mostra_foto_quando_existe(self) -> None:
        self.servico.foto.save('gel.gif', _imagem_teste('gel.gif'), save=True)
        self.func.foto.save('pro.gif', _imagem_teste('pro.gif'), save=True)

        http = HttpClient()
        http.login(username='cl', password='abc12345')
        resp = http.get(reverse('criar_agendamento'))
        self.assertContains(resp, self.servico.foto.url)
        self.assertContains(resp, self.func.foto.url)

    def test_url_de_media_serve_o_arquivo(self) -> None:
        """A rota /media/ devolve o upload (Django servindo os arquivos)."""
        self.servico.foto.save('rota.gif', _imagem_teste('rota.gif'), save=True)
        resp = HttpClient().get(self.servico.foto.url)
        self.assertEqual(resp.status_code, 200)


class ConstraintsBancoTests(_BaseAgenda):
    """Defesa em profundidade: as regras críticas também valem no BANCO.

    Os forms já validam (ServicoForm etc.), mas criações diretas (seed, shell,
    Django admin, código futuro) pulam o form. As CheckConstraints da migration
    0006 garantem que dados inválidos não entram nem por esses caminhos.
    """

    def test_banco_rejeita_preco_negativo(self) -> None:
        with self.assertRaises(IntegrityError), transaction.atomic():
            Servico.objects.create(
                nome='Inválido', descricao='x', duracao_minutos=30, preco=-1,
            )

    def test_banco_rejeita_duracao_zero(self) -> None:
        with self.assertRaises(IntegrityError), transaction.atomic():
            Servico.objects.create(
                nome='Inválido', descricao='x', duracao_minutos=0, preco=10,
            )

    def test_banco_rejeita_agendamento_com_fim_antes_do_inicio(self) -> None:
        inicio = proxima_segunda_10h()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Agendamento.objects.create(
                cliente=self.cliente, profissional=self.func, servico=self.servico,
                data_hora_inicio=inicio,
                data_hora_fim=inicio - timedelta(minutes=30),
                status='PENDENTE', valor_cobrado=self.servico.preco,
            )


class ServicoFormTests(TestCase):
    """Validação de entrada do serviço: duração positiva e preço não-negativo."""

    def _dados(self, **over):
        dados = {'nome': 'Corte', 'descricao': 'desc', 'duracao_minutos': 60, 'preco': '80.00'}
        dados.update(over)
        return dados

    def test_valido(self) -> None:
        self.assertTrue(ServicoForm(data=self._dados()).is_valid())

    def test_duracao_zero_invalida(self) -> None:
        form = ServicoForm(data=self._dados(duracao_minutos=0))
        self.assertFalse(form.is_valid())
        self.assertIn('duracao_minutos', form.errors)

    def test_preco_negativo_invalido(self) -> None:
        form = ServicoForm(data=self._dados(preco='-10.00'))
        self.assertFalse(form.is_valid())
        self.assertIn('preco', form.errors)
