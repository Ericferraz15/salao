"""
navegador_demo.py

Demonstração VISUAL: abre um navegador Chromium de verdade (janela visível,
em câmera lenta) e clica pelo site como um usuário faria.

Sobe o servidor Django numa thread interna (mesmo processo) e dirige o
navegador com Playwright. Você assiste a janela navegando sozinha:

  CLIENTE: home -> Cadastro -> (auto-login) -> Agendar -> escolhe serviço,
           profissional, dia e horário -> confirma -> Minha Conta -> Cancela
  ADMIN:   Sair -> Login admin -> Painel -> adiciona um novo serviço

Como rodar (a partir de salao/Salao/):
    python navegador_demo.py
"""

import os
import threading
import time
import urllib.request

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Salao.settings')
os.environ.setdefault('USE_POSTGRES', '0')
django.setup()

from django.contrib.auth import get_user_model
from django.core.management import call_command

from gestao.models import (
    Funcionario,
    JornadaTrabalho,
    Servico,
)

Usuario = get_user_model()

BASE = 'http://127.0.0.1:8000'
PORTA = '127.0.0.1:8000'

# Credenciais usadas na demonstração
ADMIN_EMAIL = 'eduarda@sim.salao'
ADMIN_SENHA = 'Admin@123'
CLI_EMAIL = 'joao.cliente@sim.salao'
CLI_SENHA = 'ClienteForte@123'


def passo(texto: str) -> None:
    print(f'\n>>> {texto}', flush=True)


# -------------------------------------------------------------------------
# Garante dados mínimos no banco (idempotente)
# -------------------------------------------------------------------------
def preparar_dados() -> None:
    passo('Preparando dados (admin, profissional, serviços, jornadas)...')

    # Cliente da demo: remove (por e-mail e por celular) para o cadastro
    # começar do zero e não colidir com a constraint unique de celular.
    Usuario.objects.filter(email=CLI_EMAIL).delete()
    Usuario.objects.filter(celular='(11) 96543-2100').delete()

    # Admin / dona do salão
    if not Usuario.objects.filter(email=ADMIN_EMAIL).exists():
        Usuario.objects.create_superuser(
            username=ADMIN_EMAIL, email=ADMIN_EMAIL, password=ADMIN_SENHA,
            first_name='Eduarda', last_name='Ferraz', celular='11900000001',
        )

    # Profissional ativo com jornada seg-sex
    func = Funcionario.objects.filter(esta_ativo=True).first()
    if func is None:
        u = Usuario.objects.filter(email='joana@sim.salao').first()
        if u is None:
            u = Usuario.objects.create_user(
                username='joana@sim.salao', email='joana@sim.salao',
                password='Func@123', first_name='Joana', last_name='Profissional',
                celular='11900000002',
            )
            u.is_staff = True
            u.save()
        func = Funcionario.objects.create(
            usuario=u, especializacao='Cabeleireira', esta_ativo=True,
        )
    if not JornadaTrabalho.objects.filter(funcionario=func).exists():
        for dia in range(5):  # segunda a sexta
            JornadaTrabalho.objects.create(
                funcionario=func, dia_da_semana=dia,
                hora_inicio='09:00', hora_fim='18:00',
            )

    # Serviços
    if not Servico.objects.exists():
        Servico.objects.create(nome='Corte Feminino', descricao='Corte e finalização',
                               duracao_minutos=60, preco=80.00)
        Servico.objects.create(nome='Manicure', descricao='Esmaltação em gel',
                               duracao_minutos=45, preco=50.00)


# -------------------------------------------------------------------------
# Servidor Django numa thread (mesmo processo)
# -------------------------------------------------------------------------
def iniciar_servidor() -> None:
    def _run():
        call_command('runserver', PORTA, use_reloader=False, skip_checks=True)

    t = threading.Thread(target=_run, daemon=True)
    t.start()

    passo('Subindo o servidor Django...')
    for _ in range(60):
        try:
            urllib.request.urlopen(f'{BASE}/login/', timeout=1)
            print('    Servidor no ar em ' + BASE, flush=True)
            return
        except Exception:
            time.sleep(0.5)
    raise RuntimeError('Servidor não respondeu a tempo.')


# -------------------------------------------------------------------------
# Demonstração com navegador visível
# -------------------------------------------------------------------------
def rodar_navegador() -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        navegador = p.chromium.launch(headless=False, slow_mo=1100)
        ctx = navegador.new_context(viewport={'width': 1280, 'height': 860})
        page = ctx.new_page()
        # Aceita automaticamente o confirm() do cancelamento
        page.on('dialog', lambda d: d.accept())
        page.set_default_timeout(20000)

        # ---------------- CLIENTE ----------------
        passo('CLIENTE: abrindo a home do salão')
        page.goto(BASE)
        page.wait_for_timeout(1200)

        passo('CLIENTE: clicando em "Cadastro"')
        page.get_by_role('link', name='Cadastro').first.click()
        page.wait_for_load_state()

        passo('CLIENTE: preenchendo o formulário de cadastro')
        page.fill('#id_username', CLI_EMAIL)
        page.fill('#id_first_name', 'João')
        page.fill('#id_last_name', 'Cliente')
        page.fill('#id_email', CLI_EMAIL)
        page.fill('#id_celular', '(11) 96543-2100')
        page.fill('#id_password1', CLI_SENHA)
        page.fill('#id_password2', CLI_SENHA)
        page.wait_for_timeout(800)

        passo('CLIENTE: clicando em "Cadastrar e Entrar" (auto-login)')
        page.click('button[type="submit"]')
        page.wait_for_load_state()
        page.wait_for_timeout(1200)

        # Se ainda estiver na página de cadastro, o formulário foi recusado.
        if '/cadastro' in page.url:
            erros = page.locator('.helptext, .alert-error').all_inner_texts()
            raise RuntimeError(f'Cadastro recusado pelo formulário: {erros}')

        passo('CLIENTE: clicando em "Agendar Horário"')
        page.get_by_role('link', name='Agendar Horário').first.click()
        page.wait_for_load_state()
        page.wait_for_timeout(800)

        passo('CLIENTE: escolhendo o Serviço no dropdown')
        page.select_option('#id_servico', index=1)
        page.wait_for_timeout(900)

        passo('CLIENTE: escolhendo o Profissional no dropdown')
        page.select_option('#id_profissional', index=1)

        passo('CLIENTE: aguardando a API carregar os dias disponíveis...')
        page.wait_for_selector('.date-chip', timeout=20000)
        page.wait_for_timeout(900)

        passo('CLIENTE: clicando no primeiro DIA disponível')
        page.locator('.date-chip').first.click()
        page.wait_for_selector('.time-chip', timeout=20000)
        page.wait_for_timeout(900)

        passo('CLIENTE: clicando no primeiro HORÁRIO disponível')
        page.locator('.time-chip').first.click()
        page.wait_for_timeout(900)

        passo('CLIENTE: clicando em "Confirmar Agendamento"')
        page.click('#btn-submit')
        page.wait_for_load_state()
        page.wait_for_timeout(1500)

        passo('CLIENTE: abrindo "Minha Conta" para ver o agendamento')
        page.get_by_role('link', name='Minha Conta').first.click()
        page.wait_for_load_state()
        page.wait_for_timeout(1500)

        passo('CLIENTE: clicando em "Cancelar" (confirma o alerta)')
        page.get_by_role('button', name='Cancelar').first.click()
        page.wait_for_load_state()
        page.wait_for_timeout(1500)

        # ---------------- ADMIN ----------------
        passo('ADMIN: voltando à home e clicando em "Sair"')
        page.goto(BASE)
        page.wait_for_timeout(800)
        page.get_by_role('button', name='Sair').first.click()
        page.wait_for_load_state()
        page.wait_for_timeout(1000)

        passo('ADMIN: clicando em "Login"')
        page.get_by_role('link', name='Login').first.click()
        page.wait_for_load_state()

        passo('ADMIN: preenchendo login da dona do salão')
        page.fill('#id_username', ADMIN_EMAIL)
        page.fill('#id_password', ADMIN_SENHA)
        page.wait_for_timeout(700)
        page.click('button[type="submit"]')
        page.wait_for_load_state()
        page.wait_for_timeout(1200)

        passo('ADMIN: abrindo o "Painel"')
        page.get_by_role('link', name='Painel').first.click()
        page.wait_for_load_state()
        page.wait_for_timeout(1200)

        passo('ADMIN: cadastrando um novo serviço pelo painel')
        nome_novo = f'Demo Hidratação {int(time.time())}'
        page.fill('#id_nome', nome_novo)
        page.fill('#id_descricao', 'Serviço criado durante a demonstração')
        page.fill('#id_duracao_minutos', '40')
        page.fill('#id_preco', '70.00')
        page.wait_for_timeout(800)
        page.click('button[name="add_servico"]')
        page.wait_for_load_state()
        page.wait_for_timeout(2000)

        passo('Demonstração concluída. Fechando a janela em 4s...')
        page.wait_for_timeout(4000)
        ctx.close()
        navegador.close()


def main() -> None:
    print('#' * 70)
    print('#  DEMONSTRAÇÃO VISUAL — Salão Eduarda Ferraz (navegador real)')
    print('#' * 70)
    preparar_dados()
    iniciar_servidor()
    rodar_navegador()
    print('\nOK — fluxo do cliente e do admin executados no navegador.\n', flush=True)


if __name__ == '__main__':
    main()
