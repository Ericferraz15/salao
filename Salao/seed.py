"""
seed.py — popula o banco com dados de exemplo para desenvolvimento.

Como rodar (a partir de salao/Salao/, com o venv ativo):
    python seed.py

O script é IDEMPOTENTE: pode rodar quantas vezes quiser sem duplicar
nada (cada bloco confere se o dado já existe antes de criar).

Credenciais criadas:
    admin   / admin123     (dona do salão, superusuária)
    cliente / cliente123   (cliente de exemplo)
"""

import os
from pathlib import Path

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Salao.settings')
django.setup()

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files import File
from django.utils import timezone

from gestao.models import (
    Agendamento,
    ClienteProfile,
    Funcionario,
    JornadaTrabalho,
    Produto,
    Servico,
)

Usuario = get_user_model()

# Pasta com as imagens fixas do site — usamos algumas como foto de exemplo
# dos serviços (em produção a dona sobe as fotos pelo painel).
PASTA_STATIC = Path(__file__).resolve().parent / 'gestao' / 'static'


def anexar_foto(instancia, caminho_relativo: str) -> None:
    """Copia uma imagem de static/ para o campo foto (vai para media/).

    Só age se a instância ainda não tem foto e se o arquivo existe —
    assim o seed continua idempotente e não quebra sem as imagens.
    """
    if instancia.foto:
        return
    origem = PASTA_STATIC / caminho_relativo
    if not origem.exists():
        print(f'  (aviso) imagem não encontrada: {origem}')
        return
    with origem.open('rb') as arquivo:
        instancia.foto.save(origem.name, File(arquivo), save=True)


def seed():
    # ── Dona do salão (admin) + registro de profissional ────────────────
    if not Usuario.objects.filter(username='admin').exists():
        Usuario.objects.create_superuser(
            'admin', 'admin@salao.com', 'admin123',
            first_name='Eduarda', last_name='Ferraz', celular='11999990000',
        )
        print('Admin criado (admin / admin123).')

    admin = Usuario.objects.get(username='admin')
    # Buscar a dona PELO usuário admin (e não com .first()): o banco pode
    # ter outros funcionários de teste, e .first() pegaria qualquer um.
    dona, _ = Funcionario.objects.get_or_create(
        usuario=admin,
        defaults={'especializacao': 'Nail Designer', 'esta_ativo': True},
    )
    anexar_foto(dona, 'images/dona.jpg')

    # ── Jornada de trabalho: segunda(0) a sábado(5), 09h-18h ────────────
    if not JornadaTrabalho.objects.filter(funcionario=dona).exists():
        for dia in range(6):
            JornadaTrabalho.objects.create(
                funcionario=dona, dia_da_semana=dia,
                hora_inicio='09:00', hora_fim='18:00',
            )
        print('Jornadas criadas (seg-sáb, 09h-18h).')

    # ── Serviços com foto de exemplo da galeria ─────────────────────────
    servicos_exemplo = [
        ('Alongamento em Fibra de Vidro',
         'Alongamento com fibra para unhas longas e resistentes.',
         120, 150.00, 'images/galeria/along-francesa-ouro.jpeg'),
        ('Esmaltação em Gel',
         'Esmaltação em gel com brilho e longa duração.',
         60, 70.00, 'images/galeria/gel-azul-strass.jpeg'),
        ('Nail Art Exclusiva',
         'Decoração artística feita à mão, do clássico ao ousado.',
         90, 110.00, 'images/galeria/art-stiletto-olho-grego.jpeg'),
        ('Pedicure Completa',
         'Cuidado completo dos pés com esmaltação impecável.',
         45, 55.00, 'images/galeria/pe-francesinha.jpeg'),
    ]
    for nome, descricao, duracao, preco, foto in servicos_exemplo:
        servico, criado = Servico.objects.get_or_create(
            nome=nome,
            defaults={
                'descricao': descricao,
                'duracao_minutos': duracao,
                'preco': preco,
            },
        )
        anexar_foto(servico, foto)
        if criado:
            print(f'Serviço criado: {nome}')

    servico = Servico.objects.first()

    # ── Produtos de estoque (para o painel financeiro/estoque) ──────────
    produtos_exemplo = [
        ('Esmalte em gel (unidade)', 'Uso interno nas esmaltações.', 35.00, 12, 5),
        ('Fibra de vidro (caixa)', 'Material para alongamentos.', 90.00, 3, 4),
        ('Óleo de cutícula', 'Venda ao cliente e uso interno.', 25.00, 8, 3),
    ]
    for nome, descricao, preco, qtd, minimo in produtos_exemplo:
        _, criado = Produto.objects.get_or_create(
            nome=nome,
            defaults={
                'descricao': descricao, 'preco': preco,
                'quantidade_estoque': qtd, 'estoque_minimo': minimo,
            },
        )
        if criado:
            print(f'Produto criado: {nome}')

    # ── Cliente de exemplo ───────────────────────────────────────────────
    if not Usuario.objects.filter(username='cliente').exists():
        cli_user = Usuario.objects.create_user(
            'cliente', 'cliente@teste.com', 'cliente123',
            first_name='Maria', last_name='Cliente', celular='11999991111',
        )
        ClienteProfile.objects.create(usuario=cli_user)
        print('Cliente criado (cliente / cliente123).')

    cliente = ClienteProfile.objects.get(usuario__username='cliente')

    # ── Agendamentos de exemplo (um futuro, um no histórico) ─────────────
    if not Agendamento.objects.filter(cliente=cliente).exists():
        hoje = timezone.now()
        amanha = hoje + timedelta(days=1)
        semana_passada = hoje - timedelta(days=7)

        Agendamento.objects.create(
            cliente=cliente, profissional=dona, servico=servico,
            data_hora_inicio=amanha.replace(hour=14, minute=0, second=0, microsecond=0),
            data_hora_fim=amanha.replace(hour=16, minute=0, second=0, microsecond=0),
            status='CONFIRMADO', valor_cobrado=servico.preco,
        )
        Agendamento.objects.create(
            cliente=cliente, profissional=dona, servico=servico,
            data_hora_inicio=semana_passada.replace(hour=10, minute=0, second=0, microsecond=0),
            data_hora_fim=semana_passada.replace(hour=12, minute=0, second=0, microsecond=0),
            status='CONCLUIDO', valor_cobrado=servico.preco,
        )
        print('Agendamentos de exemplo criados.')

    print('Seed concluído.')


if __name__ == '__main__':
    seed()
