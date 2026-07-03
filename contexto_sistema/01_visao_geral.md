# Contexto do Sistema — Salão Eduarda Ferraz (Studio de Beleza)

> Resumo do que o sistema é, como está organizado e como executá-lo.
> Atualizado em 2026-07-03 (rodada de features + correções).

## O que é

Aplicação **Django 6.0** de gestão para um estúdio de beleza / nail design.
Clientes se cadastram (sem username — o e-mail é o login; senha simples de
6+), fazem login e agendam serviços escolhendo em **cards com foto** do
trabalho e da profissional. A dona/admin gerencia tudo em um painel
completo: agenda do dia (com botão de WhatsApp por cliente), financeiro
com meta mensal e gráfico, caixa (entradas/despesas), estoque com alerta
de reposição, jornadas de trabalho, cadastros com foto e o ciclo de vida
dos agendamentos (confirmar, concluir → lança receita, cancelar, falta).

## Stack

- **Backend:** Django 6.0 (Python 3.12+). App principal: `gestao`.
- **Banco:** SQLite em dev local; PostgreSQL em Docker/produção (`USE_POSTGRES=1`).
- **Front:** Templates Django + CSS próprio + JavaScript vanilla (sem framework).
- **Uploads:** Pillow + ImageField; arquivos em `media/` servidos pelo próprio Django.
- **Servidor produção:** Gunicorn + WhiteNoise (estáticos). Docker/Docker Compose.
- **Usuário customizado:** `gestao.Usuario` (AbstractUser), e-mail único;
  login por e-mail OU username (`gestao/backends.py`).

## Estrutura de pastas (resumo)

```
salao/
├── docker-compose.yml, Dockerfile, entrypoint.sh, .dockerignore
├── requirements.txt, .env.example, .gitignore, README.md
└── Salao/                          # raiz do projeto Django (manage.py aqui)
    ├── manage.py
    ├── seed.py                     # dados de exemplo (admin/admin123, cliente/cliente123)
    ├── simular_uso.py              # simulação ponta-a-ponta (35 verificações)
    ├── navegador_demo.py           # demo visual com Playwright
    ├── media/                      # uploads (fotos) — fora do git
    ├── Salao/                      # configuração do projeto
    │   ├── settings.py, urls.py (rota /media/), wsgi.py, asgi.py
    └── gestao/                     # app de domínio
        ├── models.py               # Usuario, ClienteProfile, Funcionario (foto),
        │                           # Servico (foto), Agendamento, JornadaTrabalho,
        │                           # Produto, TransacaoFinanceira
        ├── forms.py                # LoginForm, ServicoForm, FuncionarioForm,
        │                           # TransacaoForm, ProdutoForm, JornadaForm
        ├── backends.py             # login por e-mail ou username
        ├── admin.py, apps.py, tests.py (105 testes), urls.py
        ├── Controller/             # camada de "views"
        │   ├── homeController.py        # home (vitrine + equipe), galeria
        │   ├── cadastroController.py    # registro de cliente
        │   ├── agendaController.py      # agendar + API de horários
        │   └── dashboardController.py   # painéis cliente/admin + ações
        ├── services/               # REGRAS DE NEGÓCIO
        │   ├── agendaService.py         # disponibilidade, conflitos, status
        │   ├── cadastroService.py       # ClienteRegistrationForm
        │   ├── financeiroService.py     # resumo, meta, gráfico, lançamentos
        │   └── estoqueService.py        # ajuste de estoque com trava
        ├── utils/constants.py      # STATUS_CHOICES, DIAS_SEMANA (0-6), META
        ├── migrations/             # 0001..0007
        ├── templates/              # base + cliente + admin + registration
        └── static/                 # CSS, JS, imagens
```

## Arquitetura em camadas

1. **Controller/** — recebe o `request`, valida entrada superficial, chama o
   service e devolve `render`/`redirect`/`JsonResponse`. Equivale às *views*.
2. **services/** — concentra as regras de negócio. Lança `ValidationError`
   com mensagens amigáveis que o controller exibe.
3. **models.py** — modelos de dados + `@property` de conveniência
   (ex.: `Usuario.celular_digitos` para links de WhatsApp).

Regra de ouro do projeto: **controller fino, service gordo**.
