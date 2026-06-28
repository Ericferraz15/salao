# Contexto do Sistema — Salão Eduarda Ferraz (Studio de Beleza)

> Documento gerado para preservar o contexto do sistema antes da fase de
> verificação/correção. Resume o que o sistema é, como está organizado e
> como executá-lo.

## O que é

Aplicação **Django 6.0** de gestão para um estúdio de beleza / nail design.
Permite que clientes se cadastrem, façam login e agendem serviços com
profissionais, respeitando jornada de trabalho e evitando conflitos de
horário. A dona/admin gerencia serviços, profissionais e o ciclo de vida dos
agendamentos (confirmar, concluir → lança receita, cancelar, marcar falta),
além de ver métricas no painel.

## Stack

- **Backend:** Django 6.0 (Python). App principal: `gestao`.
- **Banco:** SQLite em dev local; PostgreSQL em Docker/produção (flag `USE_POSTGRES=1`).
- **Front:** Templates Django + CSS próprio + JavaScript vanilla (sem framework).
- **Servidor produção:** Gunicorn + WhiteNoise (estáticos). Docker/Docker Compose.
- **Usuário customizado:** `gestao.Usuario` (AbstractUser) com `email` único e `celular`.

## Estrutura de pastas (resumo)

```
salao/
├── docker-compose.yml, Dockerfile, entrypoint.sh, requirements.txt
├── .env.example, .gitignore, README.md
├── 1 - AGENDAR HORARIOS.txt        # documento de requisitos do cliente
└── Salao/                          # raiz do projeto Django (manage.py aqui)
    ├── manage.py
    ├── seed.py                     # popula dados de exemplo
    ├── simular_uso.py              # simulação ponta-a-ponta (HTTP + serviços)
    ├── navegador_demo.py           # demo visual com Playwright
    ├── Salao/                      # configuração do projeto
    │   ├── settings.py, urls.py, wsgi.py, asgi.py
    └── gestao/                     # app de domínio
        ├── models.py               # Usuario, ClienteProfile, Funcionario,
        │                           # Servico, Agendamento, JornadaTrabalho,
        │                           # Produto, TransacaoFinanceira
        ├── admin.py, apps.py, forms.py, tests.py, urls.py
        ├── Controller/             # camada de "views" (controllers)
        │   ├── homeController.py        # home, galeria
        │   ├── cadastroController.py    # registro de cliente
        │   ├── agendaController.py      # criar agendamento + API horários
        │   └── dashboardController.py   # dashboards cliente/admin + ações
        ├── services/              # regras de negócio
        │   ├── agendaServices.py       # disponibilidade, criar/editar/cancelar...
        │   └── cadastroService.py      # ClienteRegistrationForm
        ├── utils/constants.py     # STATUS_CHOICES, DIAS_SEMANA (0-6)
        ├── migrations/            # 0001..0005
        ├── templates/             # base + cliente + admin + registration
        └── static/               # CSS, JS, imagens
```

## Arquitetura em camadas

O projeto adota uma separação explícita (incomum para Django, que costuma usar
`views.py`), em três camadas:

1. **Controller/** — recebe o `request`, valida entrada superficial, chama o
   service e devolve `render`/`redirect`/`JsonResponse`. Equivale às *views*.
2. **services/** — concentra as regras de negócio (disponibilidade, criação de
   agendamento, transições de status, lançamento de receita). Lança
   `ValidationError` com mensagens amigáveis.
3. **models.py** — modelos de dados + pequenas `@property` de conveniência.

As URLs (`gestao/urls.py`) apontam diretamente para funções dos controllers.
