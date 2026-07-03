"""
cadastroController.py — rota /cadastro/ (criação de conta do cliente).

Fluxo: GET mostra o formulário -> POST valida com o
ClienteRegistrationForm (services/cadastroService.py) -> cria Usuario +
ClienteProfile -> já faz o login -> manda para "Meus Agendamentos".
"""

from django.contrib import messages
from django.contrib.auth import login
from django.db import transaction
from django.shortcuts import redirect, render

from ..models import ClienteProfile
from ..services.cadastroService import ClienteRegistrationForm


def cliente_registro_controller(request):
    # Quem já está logado não tem o que fazer na tela de cadastro
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = ClienteRegistrationForm(request.POST)
        if form.is_valid():
            # Cria usuário e perfil na mesma transação: se a criação do perfil
            # falhar, o usuário não fica órfão (sem perfil e com e-mail/celular
            # "presos" pela constraint unique, bloqueando uma nova tentativa).
            with transaction.atomic():
                user = form.save()
                ClienteProfile.objects.create(usuario=user)

            # login() abre a sessão — a cliente já sai da tela autenticada,
            # sem precisar digitar e-mail e senha de novo.
            login(request, user)
            messages.success(
                request,
                f'Bem-vindo(a), {user.first_name}! Sua conta foi criada com sucesso.'
            )
            # Vai para "Meus Agendamentos": a home não renderiza mensagens (a
            # saudação se perderia) e essa tela faz o onboarding com o CTA de
            # agendar.
            return redirect('dashboard_cliente')

        # Mostra os erros com o LABEL do campo ("Celular: ...") em vez do
        # nome interno ("celular: ..."), que soaria técnico para a cliente.
        for field, errors in form.errors.items():
            label = form.fields[field].label if field in form.fields else field
            for error in errors:
                messages.error(request, f'{label}: {error}')

    else:
        form = ClienteRegistrationForm()

    return render(request, 'templateCliente/cadastro/cadastro.html', {'form': form})
