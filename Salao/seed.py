import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Salao.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from gestao.models import ClienteProfile, Funcionario, Servico, Agendamento, JornadaTrabalho
from datetime import timedelta

Usuario = get_user_model()

def seed():
    # Cria superuser e funcionário
    if not Usuario.objects.filter(username='admin').exists():
        admin = Usuario.objects.create_superuser('admin', 'admin@salao.com', 'admin123', first_name='Admin', celular='11999990000')
        Funcionario.objects.create(usuario=admin, especializacao='Nail Designer', esta_ativo=True)
        print("Admin criado.")

    func = Funcionario.objects.first()

    # Cria jornadas de trabalho se não existirem
    if not JornadaTrabalho.objects.filter(funcionario=func).exists():
        for i in range(6): # Segunda a sábado
            JornadaTrabalho.objects.create(funcionario=func, dia_da_semana=i, hora_inicio='09:00', hora_fim='18:00')

    # Cria serviços
    if not Servico.objects.exists():
        Servico.objects.create(nome='Alongamento em Fibra de Vidro', descricao='Alongamento com fibra para unhas longas e resistentes.', duracao_minutos=120, preco=150.00)
        Servico.objects.create(nome='Esmaltação em Gel', descricao='Esmaltação em gel com brilho e longa duração.', duracao_minutos=60, preco=70.00)
        print("Serviços criados.")

    servico = Servico.objects.first()

    # Cria usuário de teste
    if not Usuario.objects.filter(username='cliente').exists():
        cli_user = Usuario.objects.create_user('cliente', 'cliente@teste.com', 'cliente123', first_name='Maria', last_name='Cliente', celular='11999991111')
        cliente = ClienteProfile.objects.create(usuario=cli_user)
        print("Cliente criado.")
    else:
        cliente = ClienteProfile.objects.get(usuario__username='cliente')

    # Cria alguns agendamentos
    if not Agendamento.objects.filter(cliente=cliente).exists():
        hoje = timezone.now()
        amanha = hoje + timedelta(days=1)
        semana_passada = hoje - timedelta(days=7)

        # Ativo
        Agendamento.objects.create(
            cliente=cliente, profissional=func, servico=servico,
            data_hora_inicio=amanha.replace(hour=14, minute=0, second=0, microsecond=0),
            data_hora_fim=amanha.replace(hour=15, minute=0, second=0, microsecond=0),
            status='CONFIRMADO', valor_cobrado=servico.preco
        )
        # Histórico
        Agendamento.objects.create(
            cliente=cliente, profissional=func, servico=servico,
            data_hora_inicio=semana_passada.replace(hour=10, minute=0, second=0, microsecond=0),
            data_hora_fim=semana_passada.replace(hour=11, minute=0, second=0, microsecond=0),
            status='CONCLUIDO', valor_cobrado=servico.preco
        )
        print("Agendamentos criados.")

if __name__ == '__main__':
    seed()
