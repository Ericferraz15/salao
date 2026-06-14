from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, Client as HttpClient
from django.urls import reverse
from django.utils import timezone

# pyrefly: ignore [missing-import]
from .models import (
    ClienteProfile,
    Funcionario,
    JornadaTrabalho,
    Servico,
    Agendamento,
)

# pyrefly: ignore [missing-import]
from .services.agendaServices import (
    criar_agendamento,
    cancelar_agendamento,
    verificar_disponibilidade,
)
# pyrefly: ignore [missing-import]
from .services.cadastroService import ClienteRegistrationForm

Usuario = get_user_model()


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
        user = Usuario.objects.create_user(
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
