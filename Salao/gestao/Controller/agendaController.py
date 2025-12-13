from django.contrib import messages
from datetime import timedelta, datetime
from django.core.exceptions import ValidationError
from ..services.agendaServices import criar_agendamento
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from ..models import ClienteProfile, Funcionario, Servico

# @login_required #type: ignore
def criar_agendamento_Controller(request):
    if request.method == 'POST':
        profissional = request.POST.get('profissionalId')
        servico = request.POST.get('servicoId')
        hora_de_inicio_bruto = request.POST.get('hora_de_inicio')

        try:
            hora_de_inicio = datetime.strptime(hora_de_inicio_bruto, '%Y-%m-%dT%H:%M')
            cliente = ClienteProfile.objects.get(usuario=request.user).pk
            criar_agendamento(profissionalId=profissional, servicoId=servico, clienteId=cliente, hora_de_inicio=hora_de_inicio)
            messages.success(request, "Agendamento criado com sucesso.")
            return redirect('home')
        except ValidationError as error:
            messages.error(request, f"Erro ao criar agendamento: {error.message}")
            return redirect('home')   

    if request.method == 'GET':
        funcionarios = Funcionario.objects.all()
        servicos = Servico.objects.all()
        context = {
            'funcionarios': funcionarios,
            'servicos': servicos,
        }
        return render(request, 'templateCliente/agendamento/criar_agendamento.html', context=context)
        
