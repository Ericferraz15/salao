# Modelos de Dados e Fluxos Principais

> Atualizado em 2026-07-03.

## Modelos (`gestao/models.py`)

| Modelo | Papel | Campos-chave |
|---|---|---|
| **Usuario** | Usuário customizado (`AUTH_USER_MODEL`) | `email` (unique, é o login das contas novas), `celular` (unique, só dígitos nos cadastros novos), `@property celular_digitos` |
| **ClienteProfile** | "Crachá" de cliente (1‑1) | `usuario` (OneToOne, PK) |
| **Funcionario** | Profissional | `usuario` (OneToOne), `especializacao`, **`foto`** (equipe/), `esta_ativo` |
| **Servico** | Serviço do catálogo | `nome`, `descricao`, `duracao_minutos`, `preco`, **`foto`** (servicos/) |
| **Agendamento** | Reserva | `cliente`, `profissional`, `servico`, `data_hora_inicio/fim`, `valor_cobrado` (preço congelado), `status` |
| **JornadaTrabalho** | Expediente | `funcionario`, `dia_da_semana` (0=Seg…6=Dom), `hora_inicio/fim`; `unique(funcionario, dia)` |
| **Produto** | Estoque | `preco`, `quantidade_estoque`, `estoque_minimo`, `@property abaixo_estoque_minimo` |
| **TransacaoFinanceira** | Caixa | `tipo` (ENTRADA/SAIDA), `valor`, `descricao`, `agendamento` (FK opcional) |

**Constraints no banco** (migração 0006): preço ≥ 0, duração ≥ 1,
`data_hora_fim > data_hora_inicio` — defesa em profundidade além dos forms.

**Status** (`utils/constants.py`): `PENDENTE → CONFIRMADO → CONCLUIDO`,
mais `CANCELADO` e `NO_SHOW`. `META_RECEITA_MENSAL = R$ 5.000`.

### Fuso e dia da semana (pegadinhas clássicas daqui)
- `USE_TZ=True`, `TIME_ZONE='America/Sao_Paulo'`: banco em UTC, regras no
  fuso local via `timezone.localtime()` ("hoje", mês, weekday()).
- `JornadaTrabalho.dia_da_semana` usa **0–6** = `datetime.weekday()`.

## Fluxos principais

### 1. Cadastro (`/cadastro/`)
Sem campo de username: `ClienteRegistrationForm` valida nome, e-mail
(único, vira o login), celular (10-11 dígitos, salvo SÓ com dígitos,
único) e senha (**mínimo 6 caracteres** — validadores chatos removidos).
Cria `Usuario` + `ClienteProfile` em transação atômica, loga e cai em
"Meus Agendamentos". Botão de mostrar/ocultar senha no form.

### 2. Login (`/login/`)
`LoginForm` com rótulo "E-mail"; `gestao/backends.py` autentica por
username OU e-mail (contas antigas tipo `admin` continuam entrando).

### 3. Agendamento (`/agendar/`)
- GET renderiza **cards com foto**: passo 1 serviço (foto do trabalho +
  duração + preço), passo 2 profissional (foto/avatar + especialização);
  radios reais escondidos (acessível via teclado).
- O JS chama `GET /api/horarios-disponiveis/?profissional_id&servico_id`
  (`gerar_horarios_disponiveis`): próximos 5 dias com expediente, slots
  de 30 min livres, sem horários passados.
- POST → `criar_agendamento` valida tudo de novo na camada de serviço
  (com lock `select_for_update` contra double booking) e cria PENDENTE
  com `valor_cobrado = servico.preco`.

### 4. Painel do cliente (`/meus-agendamentos/`)
Ativos (com foto do serviço e avatar da profissional) + histórico
(mais recente primeiro). Cancelamento via POST muda status (não deleta).

### 5. Painel da dona (`/admin-dashboard/`) — restrito a staff
- **Métricas:** agendamentos hoje, receita hoje/mês, despesas, lucro,
  equipe/serviços.
- **Meta:** barra de progresso da receita do mês vs. R$ 5.000.
- **Agenda do Dia:** horários de hoje em ordem, com botão de WhatsApp
  (`wa.me/55<celular>?text=<confirmação pronta>`) e ações por linha.
- **Gráfico:** receita dos últimos 7 dias (barras CSS).
- **Caixa:** lançar ENTRADA/SAIDA manual + últimos lançamentos.
- **Cadastros com foto:** serviço e profissional (senha temporária).
- **Jornadas:** cadastrar/remover expediente por dia da semana.
- **Estoque:** cadastrar produto, alerta "repor!", botões +/− com trava
  contra negativo.
- **Ações de agendamento** (`/admin-dashboard/agendamento/<id>/`):
  confirmar, concluir (lança receita, idempotente), cancelar, falta.
- Rotas auxiliares: `/admin-dashboard/produto/<id>/estoque/`,
  `/admin-dashboard/jornada/<id>/remover/`.

## Camada de serviços
- `agendaService.py` — `verificar_disponibilidade`, `criar/editar/
  cancelar/confirmar/concluir/marcar_no_show`, `listar_agendamentos_cliente`,
  `gerar_horarios_disponiveis`.
- `financeiroService.py` — `resumo_financeiro`, `receita_por_dia`,
  `lancar_transacao`.
- `estoqueService.py` — `ajustar_estoque` (atômico, sem negativo).
- `cadastroService.py` — `ClienteRegistrationForm`.

## Scripts (em `salao/Salao/`)
- `seed.py` — admin/cliente de exemplo, jornadas, 4 serviços COM FOTO
  (copiadas de static para media), produtos de estoque, 2 agendamentos.
- `simular_uso.py` — simulação ponta-a-ponta idempotente (35 checks);
  limpa apenas os dados `@sim.salao`/`[SIM]` que ela mesma criou.
- `navegador_demo.py` — demo visual com Playwright.
