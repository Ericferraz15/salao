# 💅 Salão Eduarda Ferraz — Sistema de Agendamento e Gestão

Aplicação **Django 6** para um estúdio de beleza: clientes se cadastram
e agendam horários com fotos dos serviços e das profissionais; a dona
gerencia agenda, financeiro (com meta mensal), estoque e equipe em um
painel completo.

## Como rodar (dev local, SQLite)

```bash
cd salao
python3 -m venv .venv
. .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cd Salao
python manage.py migrate
python seed.py                  # dados de exemplo (opcional, recomendado)
python manage.py runserver      # http://127.0.0.1:8000
```

**Credenciais do seed:**

| Perfil  | Login     | Senha        | Onde entra            |
|---------|-----------|--------------|-----------------------|
| Dona    | `admin`   | `admin123`   | `/admin-dashboard/`   |
| Cliente | `cliente` | `cliente123` | `/meus-agendamentos/` |

O login aceita **e-mail ou usuário**. Contas criadas pelo site usam o
e-mail como login (não existe mais campo "nome de usuário" no cadastro).

## Como o código é organizado (arquitetura em 3 camadas)

```
Salao/gestao/
├── Controller/     # recebe o request, devolve a resposta (as "views")
│   ├── homeController.py       # home e galeria (públicas)
│   ├── cadastroController.py   # /cadastro/
│   ├── agendaController.py     # /agendar/ + API de horários
│   └── dashboardController.py  # painel do cliente e da dona
├── services/       # REGRAS DE NEGÓCIO (o cérebro)
│   ├── agendaService.py        # disponibilidade, conflito, status
│   ├── cadastroService.py      # formulário/validações de cadastro
│   ├── financeiroService.py    # caixa, meta, gráfico de receita
│   └── estoqueService.py       # ajuste de estoque com trava
├── models.py       # as tabelas (Usuario, Agendamento, Servico...)
├── forms.py        # login e formulários do painel admin
├── backends.py     # login por e-mail OU username
└── templates/ + static/        # HTML, CSS e JS (sem framework)
```

Regra de ouro: **controller fino, service gordo**. O controller nunca
decide regra de negócio; ele pergunta ao service e mostra o resultado.

## Testes e verificação

```bash
cd salao/Salao
. ../.venv/bin/activate

python manage.py test           # suíte completa
python simular_uso.py           # simulação ponta-a-ponta (HTTP real)
python manage.py check          # sanidade da configuração
```

## Produção (Docker + PostgreSQL)

```bash
cd salao
cp .env.example .env            # ajuste senhas e gere um SECRET_KEY
docker compose up --build       # web na porta 8000
```

## Documentação de contexto

A pasta [`contexto_sistema/`](contexto_sistema/) guarda a visão geral,
os modelos/fluxos e o histórico de correções de bugs do projeto.
