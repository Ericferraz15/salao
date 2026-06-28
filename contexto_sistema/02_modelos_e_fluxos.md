# Modelos de Dados e Fluxos Principais

## Modelos (`gestao/models.py`)

| Modelo | Papel | Campos-chave |
|---|---|---|
| **Usuario** | Usuário customizado (`AbstractUser`, `AUTH_USER_MODEL`) | `email` (unique), `celular` (unique, opcional), `first_name`, `last_name` |
| **ClienteProfile** | Perfil 1‑1 do cliente | `usuario` (OneToOne, PK) |
| **Funcionario** | Profissional | `usuario` (OneToOne), `especializacao`, `esta_ativo` |
| **Servico** | Serviço oferecido | `nome`, `descricao`, `duracao_minutos`, `preco` |
| **Agendamento** | Reserva | `cliente`, `profissional`, `servico`, `data_hora_inicio`, `data_hora_fim`, `valor_cobrado`, `status` |
| **JornadaTrabalho** | Expediente do profissional | `funcionario`, `dia_da_semana` (0=Seg … 6=Dom), `hora_inicio`, `hora_fim`; `unique(funcionario, dia_da_semana)` |
| **Produto** | Estoque | `nome`, `preco`, `quantidade_estoque`, `estoque_minimo`, `@property abaixo_estoque_minimo` |
| **TransacaoFinanceira** | Caixa | `tipo` (ENTRADA/SAIDA), `valor`, `data_hora`, `descricao`, `agendamento` (FK opcional) |

**Status do agendamento** (`utils/constants.py`): `PENDENTE → CONFIRMADO → CONCLUIDO`, além de `CANCELADO` e `NO_SHOW`.

### Detalhe crítico de fuso e dia da semana
- `USE_TZ=True`, `TIME_ZONE='America/Sao_Paulo'`. Datas são guardadas em UTC e
  convertidas para o fuso local nas comparações.
- `JornadaTrabalho.dia_da_semana` usa **0–6** para casar com
  `datetime.weekday()` (0=segunda). A migration `0004` já alinhou os choices;
  dados antigos (1–7) precisam ser reinseridos (ver comentário em `constants.py`).

## Fluxos principais

### 1. Cadastro de cliente (`/cadastro/`)
`cadastroController.cliente_registro_controller` → `ClienteRegistrationForm`
(valida e‑mail único e celular) → cria `Usuario` + `ClienteProfile` → faz login
automático. Usuário já autenticado é redirecionado para a home.

### 2. Agendamento (cliente) (`/agendar/`)
- GET renderiza serviços, profissionais e as jornadas (JSON) para o front.
- O front chama `GET /api/horarios-disponiveis/?profissional_id&servico_id`
  (`agendaController.api_horarios_disponiveis` → `gerar_horarios_disponiveis`)
  que devolve os próximos 5 dias úteis com slots de 30 min livres, já
  descontando agendamentos existentes e horários passados.
- POST envia `profissionalId`, `servicoId`, `hora_de_inicio` →
  `criar_agendamento` valida disponibilidade (`verificar_disponibilidade`):
  serviço/profissional existem, **horário não está no passado**, dia tem
  jornada, está dentro do expediente e não há conflito. Cria com status
  PENDENTE e `valor_cobrado = servico.preco`.

### 3. Dashboard do cliente (`/meus-agendamentos/`)
Lista agendamentos ativos (PENDENTE/CONFIRMADO) e histórico
(CONCLUIDO/CANCELADO/NO_SHOW). Cancelamento via POST muda o status para
CANCELADO (não deleta — preserva histórico).

### 4. Painel admin (`/admin-dashboard/`)
Restrito a `is_staff`/`is_superuser`. Métricas (agendamentos de hoje, receita do
mês, nº de profissionais/serviços), cadastro de serviço e de profissional
(gera senha temporária), e ações por agendamento
(`/admin-dashboard/agendamento/<id>/`): confirmar, concluir (lança
`TransacaoFinanceira` de ENTRADA, idempotente), cancelar, marcar falta.

## Camada de serviços (`services/agendaServices.py`)
- `verificar_disponibilidade(...)` → retorna `(funcionario, servico)` e lança
  `ValidationError` em qualquer impedimento (evita N+1 reaproveitando os objetos).
- `criar_agendamento`, `editar_agendamento`, `cancelar_agendamento`,
  `confirmar_agendamento`, `concluir_agendamento`, `marcar_no_show`,
  `listar_agendamentos_cliente`, `gerar_horarios_disponiveis`.

## Scripts úteis (em `salao/Salao/`)
- `seed.py` — popula admin, jornadas, serviços, cliente e 2 agendamentos.
- `simular_uso.py` — simulação ponta‑a‑ponta (HTTP + serviços) com relatório
  `[OK]/[FALHA]`. Idempotente.
- `navegador_demo.py` — demo visual com Playwright (navegador real). Requer
  `pip install playwright && playwright install chromium`.
