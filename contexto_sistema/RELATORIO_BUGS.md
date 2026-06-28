# Relatório de Verificação e Correção de Bugs

**Projeto:** Salão Eduarda Ferraz (Django 6.0)
**Data:** 2026-06-28
**Escopo:** Ler o sistema, rodar, verificar correção, corrigir bugs encontrados
(priorizando legibilidade e boas práticas), testar e versionar.

---

## 1. Metodologia (como o sistema foi verificado)

1. **Leitura completa** do código: settings, models, controllers, services,
   forms, admin, templates, JS, migrations, scripts e Docker.
2. **Ambiente** isolado: `venv` + `requirements.txt` (Django 6.0.6, SQLite).
3. **Checagens do Django:**
   - `manage.py check` → sem problemas.
   - `manage.py makemigrations --check --dry-run` → sem drift (modelos e
     migrations estão consistentes; a migration `0004` já alinhou
     `dia_da_semana` para 0–6).
4. **Suíte de testes existente:** 23 testes → todos passando.
5. **Simulação ponta-a-ponta** (`simular_uso.py`): 35 verificações → todas OK.
6. **Servidor real** (`runserver`) + sondagem de endpoints:
   - `/`, `/galeria/`, `/login/`, `/cadastro/` → **200**
   - `/agendar/`, `/admin-dashboard/`, `/api/horarios-disponiveis/` (sem login)
     → **302** (redireciona para login, como esperado)

> **Conclusão da verificação:** o "caminho feliz" está funcional e bem
> estruturado — o código já havia passado por uma rodada anterior de correções
> (comentários `CORRIGIDO`). Os bugs abaixo são problemas **remanescentes e
> mais sutis**, que os testes existentes não cobriam.

---

## 2. Bugs encontrados e corrigidos

### 🐞 Bug 1 — Métricas do painel admin usam UTC em vez do horário local *(funcional, médio/alto)*

- **Arquivo:** `Salao/gestao/Controller/dashboardController.py`
- **Sintoma:** "Agendamentos Hoje" e "Receita Mês" exibem valores errados em
  parte do dia.
- **Causa raiz:** o controller usava `timezone.now().date()`,
  `timezone.now().month` e `timezone.now().year`. Como `timezone.now()` retorna
  **UTC** e o projeto roda em `America/Sao_Paulo` (UTC‑3), todo dia entre
  ~21h e meia-noite (e nas viradas de mês) o "hoje"/"mês" em UTC já é o dia/mês
  seguinte. Pior: os lookups `__date`/`__month` do Django extraem a data no
  **fuso local** no banco, então os dois lados da comparação ficavam em fusos
  diferentes — à noite, a receita do mês podia aparecer como **R$ 0,00** e a
  contagem de agendamentos do dia ficava incorreta.
- **Inconsistência:** todo o resto do código já usava
  `timezone.localtime(timezone.now())` (services, scripts). O controller era a
  exceção.
- **Correção:** calcular `agora_local = timezone.localtime(timezone.now())` uma
  vez e derivar `date()`, `year`, `month` dele.
- **Boas práticas:** consistência com o restante do código; uma única fonte de
  "agora"; comentário explicando o porquê.

### 🐞 Bug 2 — `except (ValueError, Exception)` mascara erros reais *(robustez / boas práticas)*

- **Arquivo:** `Salao/gestao/Controller/agendaController.py`
- **Sintoma:** qualquer erro ao interpretar a data do agendamento vira a mesma
  mensagem genérica "Formato de data/hora inválido.", escondendo causas reais
  (ex.: bug interno, exceção inesperada de timezone).
- **Causa raiz:** `except (ValueError, Exception)` é redundante (`Exception` já
  engloba `ValueError`) e amplo demais — captura **tudo**, inclusive erros de
  programação, sem registrar log.
- **Correção:** capturar apenas `except ValueError` — exatamente o que
  `datetime.strptime` lança para formato inválido. Erros inesperados voltam a
  propagar (ficam visíveis em log/monitoramento) em vez de serem silenciados.
- **Boas práticas:** capturar a exceção mais específica possível.

### 🐞 Bug 3 — Agendamento no passado não é bloqueado na camada de serviço *(funcional / regra de negócio)*

- **Arquivo:** `Salao/gestao/services/agendaServices.py`
  (`verificar_disponibilidade`)
- **Sintoma:** era possível criar/editar um agendamento com horário **no
  passado**.
- **Causa raiz:** `gerar_horarios_disponiveis` oculta horários passados na
  **interface**, mas a regra não existia na **camada de serviço**. Cenários
  reais que driblavam a proteção: página de agendamento aberta há muito tempo
  (slot escolhido "envelhece" e vira passado antes do envio) e requisições
  POST forjadas. A validação acabava dependendo só do front-end.
- **Correção:** em `verificar_disponibilidade`, rejeitar
  `hora_de_inicio <= timezone.now()` com mensagem clara. Como essa função é
  usada por `criar_agendamento` **e** `editar_agendamento`, a regra passa a
  valer nos dois fluxos (defesa em profundidade).
- **Boas práticas:** validação de regra de negócio no back-end, não só no JS.

### 🔧 Limpeza menor — comentário enganoso

- Em `gerar_horarios_disponiveis`, o comentário dizia "(+30 mins pra
  segurança)", mas o código apenas oculta horários já passados (sem buffer de
  30 min). Comentário ajustado para refletir o comportamento real.

---

## 3. Testes de regressão adicionados

Arquivo: `Salao/gestao/tests.py` (+3 testes; total **23 → 26**).

| Teste | Cobre | Observação |
|---|---|---|
| `DashboardAdminTimezoneTests.test_agendamentos_hoje_usa_data_local` | Bug 1 | Usa `mock` de `timezone.now` para simular a virada de dia UTC×SP. **Verificado que falha no código antigo** (`0 != 1`) e passa no corrigido. |
| `CriarAgendamentoControllerTests.test_post_data_invalida_redireciona_com_erro` | Bug 2 | Garante que o `except ValueError` mais estrito **continua** tratando entrada malformada com mensagem amigável. |
| `AgendamentoServiceTests.test_agendamento_no_passado_bloqueado` | Bug 3 | Garante `ValidationError` ao tentar agendar ontem. |

---

## 4. Resultado final (verde)

```
manage.py test        → Ran 26 tests ... OK
simular_uso.py        → 35 verificações: 35 OK / 0 FALHA
manage.py check       → System check identified no issues
```

---

## 5. Itens observados e NÃO alterados (recomendações futuras)

Para manter o escopo focado em bugs reais, estes pontos ficam como sugestão:

1. **Reagendar pelo admin sem URL:** `editar_agendamento` existe e é testado,
   mas não há rota/controller que o exponha no painel. É uma *feature*
   faltante, não um bug.
2. **Normalização do celular:** `clean_celular` valida pelos dígitos, mas
   `save()` grava a string formatada (`(11) 99999-0000`). Convém padronizar o
   armazenamento (só dígitos) — atenção: `navegador_demo.py` remove o cliente
   por celular formatado, então a mudança exigiria ajuste lá.
3. **`except Exception` na API de horários** (`api_horarios_disponiveis`):
   mantido de propósito — é um *boundary* de API que **registra log**
   (`logger.exception`) e devolve 500 amigável; padrão aceitável.
4. **Dados antigos de `JornadaTrabalho` (1–7):** bancos pré-migration `0004`
   precisam reinserir as jornadas com 0–6 (ver `utils/constants.py`).
5. **`db.sqlite3` versionado:** está sob controle de versão apesar do
   `.gitignore`. Idealmente removê-lo do índice (`git rm --cached`) para evitar
   conflitos de binário entre máquinas.
