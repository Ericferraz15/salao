from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from datetime import datetime
from ..services.agendaServices import *
from ..dtos import AgendamentoRequestDTO
from ..models import Funcionario, Servico

service = AgendamentoService()

@login_required
def criar_agendamento_View(request):
    if request.method == 'POST':
        try:
            dto_request = AgendamentoRequestDTO(
                cliente_id=request.user.id,
                profissional_id=int(request.POST.get('profissionalId')),
                servico_id=int(request.POST.get('servicoId')),
                data_hora_inicio=datetime.strptime(
                    request.POST.get('hora_de_inicio'), '%Y-%m-%dT%H:%M'
                )
            )
            service.criar(dto_request)
            messages.success(request, "Agendamento realizado com sucesso!")
            return redirect('listar_agendamentos_View')
        except ValueError:
            messages.error(request, "Formato de data ou ID inválido.")
        except Exception as error:
            messages.error(request, str(error))
    context = {
        'funcionarios': Funcionario.objects.filter(estaAtivo=True),
        'servicos': Servico.objects.all(),
    }
    return render(request, 'criar_agendamento.html', context)


@login_required
def listar_agendamentos_View(request):
    agendamentos = service.listar_por_cliente(request.user.id)
    return render(request, 'listar_agendamento.html', {'agendamentos': agendamentos})

@login_required
@require_POST
def cancelar_agendamento_View(request, agendamento_ID):
    try:
        service.cancelar(agendamento_id=agendamento_ID)
        messages.success(request, "Agendamento cancelado com sucesso.")
    except Exception as error:
        messages.error(request, f"Erro ao cancelar: {str(error)}")
    return redirect('listar_agendamentos_View')
