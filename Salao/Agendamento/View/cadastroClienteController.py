from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.db import transaction
from django.contrib import messages
from ..forms import RegistroClienteForm
from django.core.exceptions import ValidationError
from ..models import ClienteProfile
from ..services.cadastroClienteService import ClienteRegistrationForm 

def cadastrar_Cliente_View(request):
    if request.method == 'POST':
        form = RegistroClienteForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save() 
                    ClienteProfile.objects.create(
                        usuario=user,
                    )
                login(request, user)
                messages.success(request, f"Conta criada com sucesso, {user.first_name}!")
                return redirect('home')

            except Exception as error:
                messages.error(request, f"Erro ao criar perfil: {error}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    label = form.fields[field].label or field
                    messages.error(request, f"{label}: {error}")
    else:
        form = ClienteRegistrationForm()
    return render(request, 'cadastro.html', {'form': form})