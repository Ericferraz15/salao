from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages
from django.core.exceptions import ValidationError
from ..models import ClienteProfile
from ..services.CadastroService import ClienteRegistrationForm 


def cliente_registro_Controller(request):
    if request.method == 'POST':
        form = ClienteRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            
            user.first_name = form.cleaned_data.get('first_name')
            user.last_name = form.cleaned_data.get('last_name')
            user.email = form.cleaned_data.get('email')
            user.save()

            ClienteProfile.objects.create(
                usuario=user,
                telefone=form.cleaned_data.get('telefone')
            )
            
            login(request, user)
            messages.success(request, f"Conta criada com sucesso, {user.first_name}! Você já está logado.")
            return redirect('home')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Erro no campo '{field}': {error}")
            
    else:
        form = ClienteRegistrationForm()
        
    context = {'form': form}
    return render(request, 'templateCliente/cadastro/cadastro.html', context)