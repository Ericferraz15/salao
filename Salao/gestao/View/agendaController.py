from django.contrib import messages
from datetime import timedelta, datetime
from django.core.exceptions import ValidationError
from ..services.AgendaServices import criar_agendamento, listar_agendamentos, cancelar_agendamento
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect
from ..models import *

# @login_required #type: ignore
def criar_agendamento_View(request):
    if request.method == 'POST':
        profissional = request.POST.get('profissionalId')
        servico = request.POST.get('servicoId')
        hora_de_inicio_bruto = request.POST.get('hora_de_inicio')

        try:
            hora_de_inicio = datetime.strptime(hora_de_inicio_bruto, '%Y-%m-%dT%H:%M')
            cliente = ClienteProfile.objects.get(usuario=request.user).pk
            criar_agendamento(profissionalId=profissional, servicoId=servico, clienteId=cliente, hora_de_inicio=hora_de_inicio)
            messages.success(request, "Agendamento criado com sucesso.")
            return redirect('listar_agendamentos_View')
        except ValidationError as error:
            messages.error(request, f"Erro ao criar agendamento: {error.message}")

    if request.method == 'GET':
        funcionarios = Funcionario.objects.all()
        servicos = Servico.objects.all()
        context = {
            'funcionarios': funcionarios,
            'servicos': servicos,
        }
        return render(request, 'templateCliente/agendamento/criar_agendamento.html', context=context)


# @login_required #type: ignore
def listar_agendamentos_View(request):
    cliente = request.user.id
    agendamentos = listar_agendamentos(clienteId=cliente)
    context = {
        'agendamentos': agendamentos
    }
    return render(request, 'templateCliente/agendamento/listar_agendamento.html', context=context)


# @login_required #type: ignore
@require_POST
def cancelar_agendamento_View(request, agendamento_ID):
    try:
        cancelar_agendamento(agendamentoId=agendamento_ID)
        messages.success(request, "Agendamento cancelado com sucesso.")

    except ValidationError as error:
        messages.error(request, f"Erro ao cancelar agendamento: {error.message}")
    return redirect('listar_agendamentos_View')