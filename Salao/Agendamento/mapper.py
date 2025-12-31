from .models import Agendamento
from .dtos import AgendamentoResponseDTO

class AgendamentoMapper:
    @staticmethod
    def to_dto(entity: Agendamento) -> AgendamentoResponseDTO:
        # Mapeamento de cores para o status
        cores = {
            'PENDENTE': 'text-warning',
            'CONFIRMADO': 'text-primary',
            'CONCLUIDO': 'text-success',
            'CANCELADO': 'text-danger',
        }

        return AgendamentoResponseDTO(
            id=entity.pk,
            cliente_nome=entity.cliente.usuario.get_full_name(),
            profissional_nome=entity.profissional.usuario.get_full_name(),
            servico_nome=entity.servico.nome,
            inicio=entity.data_hora_inicio.strftime('%d/%m/%Y %H:%M'),
            fim=entity.data_hora_fim.strftime('%H:%M'),
            valor=entity.valor_cobrado,
            status_display=entity.get_status_display(),#type:ignore
            cor_status=cores.get(entity.status, 'text-dark')
        )