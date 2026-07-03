"""
financeiroService.py — regras de negócio do CAIXA do salão.

Tudo que envolve dinheiro passa por TransacaoFinanceira:
- ENTRADA: receita (agendamento concluído lança sozinho; venda avulsa
  a dona lança manualmente pelo painel);
- SAIDA: despesa (aluguel, luz, reposição de produto...).

Este módulo calcula os números que o painel admin mostra. Uma decisão
importante de fuso horário: "hoje" e "este mês" são sempre definidos no
horário LOCAL (America/Sao_Paulo) — à noite, a data em UTC já é o dia
seguinte, e usar UTC faria as métricas contarem o período errado.
"""

from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.utils import timezone

# pyrefly: ignore [missing-import]
from ..models import TransacaoFinanceira
# pyrefly: ignore [missing-import]
from ..utils.constants import META_RECEITA_MENSAL


def _soma(queryset) -> Decimal:
    """Sum(valor) do queryset, devolvendo Decimal('0') quando vazio."""
    return queryset.aggregate(total=Sum('valor'))['total'] or Decimal('0')


def resumo_financeiro(agora_local) -> dict:
    """Números do painel: receita de hoje/mês, despesas, lucro e meta.

    Recebe o "agora" local por parâmetro (em vez de calculá-lo aqui)
    para o controller usar o MESMO instante em todas as métricas e para
    os testes conseguirem fixar uma data.
    """
    hoje = agora_local.date()

    transacoes_mes = TransacaoFinanceira.objects.filter(
        data_hora__year=agora_local.year,
        data_hora__month=agora_local.month,
    )

    receita_mes = _soma(transacoes_mes.filter(tipo='ENTRADA'))
    despesa_mes = _soma(transacoes_mes.filter(tipo='SAIDA'))
    receita_hoje = _soma(
        TransacaoFinanceira.objects.filter(tipo='ENTRADA', data_hora__date=hoje)
    )

    # Progresso rumo à meta, limitado a 100% (a barra não passa do fim).
    progresso = min(100, round(receita_mes / META_RECEITA_MENSAL * 100)) \
        if META_RECEITA_MENSAL else 0

    return {
        'receita_hoje': receita_hoje,
        'receita_mes': receita_mes,
        'despesa_mes': despesa_mes,
        'lucro_mes': receita_mes - despesa_mes,
        'meta_mensal': META_RECEITA_MENSAL,
        'meta_progresso_pct': progresso,
        'meta_batida': receita_mes >= META_RECEITA_MENSAL,
    }


def receita_por_dia(agora_local, dias: int = 7) -> list[dict]:
    """Receita dos últimos `dias` dias — dados prontos para o gráfico.

    Devolve um item por dia (mesmo os zerados, para o gráfico não ter
    "buracos"): rótulo curto ('Seg'), data, total e altura da barra em %
    relativa ao melhor dia do período.
    """
    hoje = agora_local.date()
    inicio = hoje - timedelta(days=dias - 1)

    # Uma query só: totais agrupados por dia (no fuso local, via __date).
    linhas = (
        TransacaoFinanceira.objects
        .filter(tipo='ENTRADA', data_hora__date__gte=inicio)
        .values('data_hora__date')
        .annotate(total=Sum('valor'))
    )
    totais = {linha['data_hora__date']: linha['total'] for linha in linhas}

    rotulos = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
    serie = []
    for i in range(dias):
        dia = inicio + timedelta(days=i)
        serie.append({
            'rotulo': rotulos[dia.weekday()],
            'data': dia,
            'total': totais.get(dia, Decimal('0')),
        })

    maior = max((item['total'] for item in serie), default=Decimal('0'))
    for item in serie:
        item['altura_pct'] = round(item['total'] / maior * 100) if maior else 0

    return serie


def lancar_transacao(tipo: str, valor, descricao: str) -> TransacaoFinanceira:
    """Registra uma entrada/saída manual no caixa, validando a entrada.

    Levanta ValidationError com mensagem amigável (o controller converte
    em mensagem na tela) — mesmo padrão do agendaServices.
    """
    if tipo not in ('ENTRADA', 'SAIDA'):
        raise ValidationError('Tipo de transação inválido.')

    try:
        valor = Decimal(str(valor).replace(',', '.'))
    except Exception:
        raise ValidationError('Valor inválido. Use números, ex.: 150.00.')

    if valor <= 0:
        raise ValidationError('O valor deve ser maior que zero.')

    descricao = (descricao or '').strip()
    if not descricao:
        raise ValidationError('Descreva a transação (ex.: "Aluguel de julho").')

    return TransacaoFinanceira.objects.create(
        tipo=tipo, valor=valor, descricao=descricao,
    )
