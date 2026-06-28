# Relatório de Verificação e Correção de Bugs

**Projeto:** Salão Eduarda Ferraz (Django 6.0)
**Data:** 2026-06-28
**Escopo:** Ler o sistema, rodar, verificar, corrigir bugs (priorizando
legibilidade e boas práticas), testar tudo e versionar.

---

## 1. Metodologia

1. **Leitura completa** do código (settings, models, controllers, services,
   forms, admin, templates, JS, migrations, scripts, Docker).
2. **Ambiente isolado:** `venv` + `requirements.txt` (Django 6.0.6, SQLite).
3. **Checagens:** `manage.py check` (ok), `makemigrations --check` (sem drift),
   `check --deploy` (auditoria de produção).
4. **Testes:** suíte existente (23) + simulação ponta-a-ponta (35 verificações)
   + sondagem do servidor real (status HTTP de todas as rotas).
5. **Caça aprofundada** a casos de borda (timezone, limites de campo,
   autorização, fluxo de mensagens, financeiro) com **cobertura de testes
   ampliada de 23 → 54 testes**.

> O "caminho feliz" já funcionava (o código tinha passado por uma rodada
> anterior de correções). Os bugs abaixo são problemas **remanescentes/sutis**
> que os testes não cobriam. Para cada correção verifiquei, quando aplicável,
> que o novo teste **falha no código antigo** e passa no corrigido.

---

## 2. Bugs corrigidos

### 🐞 Bug 1 — Métricas do painel admin em UTC em vez do horário local *(funcional, médio/alto)*
- **Arquivo:** `Controller/dashboardController.py`
- **Causa:** usava `timezone.now().date()/.month/.year` (UTC). Em SP (UTC‑3), à
  noite e nas viradas de mês o "hoje"/"mês" já são o período seguinte em UTC.
  Como os lookups `__date`/`__month` extraem no fuso local no banco, os lados da
  comparação ficavam em fusos diferentes — a **receita do mês podia zerar** e a
  contagem de agendamentos do dia ficava errada à noite.
- **Correção:** `agora_local = timezone.localtime(timezone.now())` e derivar
  `date/year/month` dele (consistente com o resto do código).
- **Teste:** `DashboardAdminTimezoneTests` (mock de `now`); **verificado que
  falha no código antigo** (`0 != 1`).

### 🐞 Bug 2 — `except (ValueError, Exception)` mascara erros *(robustez/boas práticas)*
- **Arquivo:** `Controller/agendaController.py`
- **Causa:** captura redundante e ampla demais — qualquer erro virava "Formato
  de data/hora inválido.", escondendo falhas reais (sem log).
- **Correção:** `except ValueError` (o que `strptime` de fato lança).
- **Teste:** `CriarAgendamentoControllerTests.test_post_data_invalida...`.

### 🐞 Bug 3 — Agendamento no passado não era bloqueado no back-end *(funcional)*
- **Arquivo:** `services/agendaServices.py` (`verificar_disponibilidade`)
- **Causa:** só o front ocultava horários passados; página aberta há muito tempo
  ou POST forjado driblavam a regra.
- **Correção:** rejeita `hora_de_inicio <= timezone.now()` na camada de serviço
  (vale para criar **e** editar).
- **Teste:** `AgendamentoServiceTests.test_agendamento_no_passado_bloqueado`.

### 🐞 Bug 4 — `FuncionarioForm.email` sem `max_length` → 500 no PostgreSQL *(funcional, produção)*
- **Arquivo:** `forms.py`
- **Causa:** `email` é campo **declarado** que não pertence ao model
  `Funcionario`, então não há `ModelForm._post_clean` validando contra
  `Usuario.email` (`max_length=100`). Sem `max_length` no form, o `EmailField`
  aceita 254 caracteres; o admin cadastrando um profissional com e‑mail > 100
  passa na validação e **quebra o INSERT no PostgreSQL** ("value too long").
  No SQLite não aparece (ignora o tamanho).
- **Correção:** `max_length=100` no `EmailField` do `FuncionarioForm`.
- **Teste:** `FuncionarioFormTests` (102 chars inválido / válido dentro do
  limite); **verificado que falha no código antigo** (`True is not False`).

### 🐞 Bug 5 — Confirmação de agendamento se perdia *(UX)*
- **Arquivo:** `Controller/agendaController.py`
- **Causa:** após agendar, redirecionava para `home`, que **não renderiza
  mensagens** → o "Agendamento criado com sucesso" sumia.
- **Correção:** redireciona para `dashboard_cliente` ("Meus Agendamentos"), que
  exibe a confirmação e mostra o agendamento recém-criado.
- **Teste:** `CriarAgendamentoSucessoControllerTests`.

### 🐞 Bug 6 — Saudação de cadastro se perdia *(UX)*
- **Arquivo:** `Controller/cadastroController.py`
- **Causa:** mesmo problema do Bug 5 (redirect para `home`).
- **Correção:** redireciona para `dashboard_cliente` (mostra saudação +
  onboarding com CTA de agendar).
- **Teste:** `CadastroSucessoControllerTests`.

### 🔧 Hardening — `SECURE_HSTS_PRELOAD` *(boas práticas)*
- **Arquivo:** `Salao/settings.py`. Em produção já havia HSTS de 1 ano +
  `includeSubDomains`; faltava `SECURE_HSTS_PRELOAD = True` (aviso
  `security.W021`). Com isso, `check --deploy` (DEBUG=False + SECRET_KEY forte)
  fica **sem nenhum aviso**.

### 🐞 Bug 7 — Double booking sob concorrência *(funcional, produção)*
- **Arquivo:** `services/agendaServices.py` (`criar_agendamento`, `editar_agendamento`)
- **Causa:** `verificar_disponibilidade` + `create` não eram atômicos; dois POSTs
  simultâneos para o mesmo profissional podiam passar os dois no check e criar
  agendamentos sobrepostos.
- **Correção:** `transaction.atomic()` + `select_for_update()` na linha do
  profissional, serializando reservas concorrentes. No SQLite o lock é no-op
  (a escrita já é serializada); no PostgreSQL passa a impedir a corrida.

### 🐞 Bug 8 — Conclusão sem atomicidade entre status e receita *(robustez)*
- **Arquivo:** `services/agendaServices.py` (`concluir_agendamento`)
- **Causa:** o status virava CONCLUIDO e a `TransacaoFinanceira` era criada em
  operações separadas; uma falha no meio deixaria agendamento concluído sem a
  receita correspondente.
- **Correção:** ambas as gravações dentro de `transaction.atomic()`.

### 🐞 Bug 9 — Histórico do cliente em ordem cronológica invertida *(UX)*
- **Arquivo:** `Controller/dashboardController.py`
- **Causa:** o histórico era listado do mais antigo para o mais recente.
- **Correção:** `order_by('-data_hora_inicio')` (mais recente primeiro).
- **Teste:** `DashboardClienteHistoricoTests` (verificado que falha no código antigo).

### 🐞 Bug 10 — Serviço aceitava duração 0 e preço negativo *(validação)*
- **Arquivo:** `forms.py` (`ServicoForm`)
- **Causa:** `PositiveIntegerField` aceita 0 (slots degenerados) e `DecimalField`
  aceita negativo (receita negativa); o form não validava.
- **Correção:** `clean_duracao_minutos` (≥ 1) e `clean_preco` (≥ 0) + `min` no widget.
- **Teste:** `ServicoFormTests`.

### 🐞 Bug 11 — Dockerfile com Python incompatível: build de produção quebrado *(infra, alto)*
- **Arquivo:** `Dockerfile`
- **Causa:** `FROM python:3.11-slim`, mas `requirements.txt` pede `django>=6.0`
  e **Django 6.0 exige Python ≥ 3.12** (`Requires-Python: >=3.12`). Em 3.11 o
  `pip install` não encontra o Django 6.0 e o **build do Docker falha** — a
  imagem de produção não sobe.
- **Correção:** `FROM python:3.13-slim` (versão usada no desenvolvimento — os
  `.pyc` são cpython-313).
- **Validação empírica (docker disponível no ambiente):**
  - Com 3.13: `docker build` **conclui com sucesso** (Django 6.0.6 + psycopg2
    cp313 instalados, imagem exportada).
  - Com 3.11: `pip install 'django>=6.0'` **falha** (sem versão compatível).

### 🐞 Bug 12 — Criação de usuário não-atômica (cadastro e admin) *(robustez/integridade)*
- **Arquivos:** `Controller/cadastroController.py`, `Controller/dashboardController.py`
- **Causa:** o cadastro criava `Usuario` e depois `ClienteProfile` em passos
  separados; o painel criava `Usuario` e depois `Funcionario`. Se o segundo
  passo falhasse, sobrava um usuário órfão — sem perfil/registro e com
  e‑mail/celular "presos" pela constraint `unique`, bloqueando nova tentativa.
- **Correção:** ambos os pares de criação agora em `transaction.atomic()`
  (tudo ou nada).
- **Teste:** `...test_cadastro_e_atomico_rollback_se_perfil_falha` (mock força
  falha na criação do perfil e confirma que o usuário **não** persiste).

### 🔧 Cosmético — formato monetário e normalização de e-mail
- `receita_mes` vazia aparecia como "R$ 0.0"; com `|floatformat:2` (locale
  pt-br) passa a "R$ 0,00".
- `FuncionarioForm.clean_email` passa a normalizar para minúsculas/sem espaços
  (igual ao cadastro de cliente), tornando a checagem de duplicidade consistente.
- **Código morto removido:** `criar_agendamento_controller` montava um
  `jornadas_json` (query + loop a cada GET) que nenhum template usava — a UI
  carrega horários pela API. Removido junto com os imports órfãos (`json`,
  `JornadaTrabalho`).

---

## 3. Falso-positivo investigado (NÃO era bug)
- Em `ClienteRegistrationForm`, `first_name`/`email` declaravam `max_length`
  maior que o model. Parecia o mesmo Bug 4, **mas** esses campos estão em
  `Meta.fields`, então `ModelForm._post_clean()` já valida contra o model — o
  valor longo é barrado. Mesmo assim, alinhei os `max_length` do form ao schema
  (defensivo/legível) e documentei com teste. Diferente do `FuncionarioForm`,
  onde o `email` não é campo do model e por isso o bug era real.

---

## 4. Resultado final (verde)

```
manage.py test        → Ran 63 tests ... OK        (eram 23)
simular_uso.py        → 35 verificações: 35 OK / 0 FALHA
manage.py check       → no issues
check --deploy        → no issues (DEBUG=False + SECRET_KEY forte)
makemigrations --check→ No changes detected
pyflakes (app+scripts)→ sem avisos (imports/variáveis órfãos removidos)
docker build          → conclui (python:3.13-slim)
```

Cobertura adicionada: transições de status, **lançamento de receita +
idempotência**, edição/conflito, geração de horários, ações de admin via HTTP,
autorização (cliente não cancela agendamento de outro; não-admin bloqueado),
cadastros pelo painel e fluxos de sucesso de agendar/cadastrar.

---

## 5. Recomendações futuras (fora do escopo de "bug")
1. **`editar_agendamento` sem rota:** existe e é testado, mas não há
   URL/controller que o exponha (reagendar pelo painel).
2. **Normalização de celular:** validado por dígitos, mas gravado formatado —
   "11999990000" e "(11) 99999-0000" passariam pela constraint `unique`.
   (O e-mail do `FuncionarioForm` agora normaliza para minúsculas; o celular
   poderia seguir o mesmo caminho.)
3. **`db.sqlite3` versionado** apesar do `.gitignore`: idealmente
   `git rm --cached`.
4. **Autorização:** todo `Funcionario` recebe `is_staff=True` e acessa o painel
   completo (receita, cadastros). Avaliar separar papéis dona × profissional.
5. **Criação de usuário pelo Django admin:** `add_fieldsets` não inclui
   email/first_name/last_name (obrigatórios); criar usuário por `/admin/` gera
   registro incompleto. Fluxos primários (cadastro, painel) não são afetados.
