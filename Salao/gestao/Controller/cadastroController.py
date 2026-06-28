"""
cadastroController.py

CORREÇÕES APLICADAS:
1. [BUG] O controller extraía first_name, last_name, email do cleaned_data e
   os reatribuía manualmente — isso é desnecessário porque form.save() já
   cuida disso. Código duplicado removido.

2. [BUG] ClienteProfile.objects.create(telefone=...) — o model não tem campo
   'telefone', causava TypeError. Corrigido: ClienteProfile não precisa
   de campos extras além do usuario.

3. [SEGURANÇA] Usuário autenticado acessando /cadastro/ agora é redirecionado
   em vez de ver o formulário vazio (sem sentido lógico).

4. [UX] Erros de formulário agora exibem o label do campo em português
   em vez do nome do campo interno.
"""

from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect, render

from ..models import ClienteProfile
from ..services.cadastroService import ClienteRegistrationForm


def cliente_registro_controller(request):
    # NOVO: redireciona usuário já autenticado
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = ClienteRegistrationForm(request.POST)
        if form.is_valid():
            # CORRIGIDO: form.save() já atribui todos os campos corretamente
            user = form.save()

            # CORRIGIDO: ClienteProfile só precisa do usuario — sem campo 'telefone'
            ClienteProfile.objects.create(usuario=user)

            login(request, user)
            messages.success(
                request,
                f'Bem-vindo(a), {user.first_name}! Sua conta foi criada com sucesso.'
            )
            # Vai para "Meus Agendamentos": a home não renderiza mensagens (a
            # saudação se perderia) e essa tela faz o onboarding com o CTA de
            # agendar.
            return redirect('dashboard_cliente')

        # CORRIGIDO: usa o label do campo (em português) na mensagem de erro
        for field, errors in form.errors.items():
            label = form.fields[field].label if field in form.fields else field
            for error in errors:
                messages.error(request, f'{label}: {error}')

    else:
        form = ClienteRegistrationForm()

    return render(request, 'templateCliente/cadastro/cadastro.html', {'form': form})
