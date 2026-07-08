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

### Entrar com o Google

As telas de login e cadastro têm o botão **"Continuar com o Google"**:
um clique cria a conta (ou entra, se o e-mail já existir) — sem senha e
sem formulário. Para ativar, preencha `GOOGLE_OAUTH_CLIENT_ID` no `.env`
(o passo a passo de como criar o client_id está no `.env.example`).
Sem essa variável o botão não aparece e nada muda no site.

Quem entra pelo Google não cadastra celular — o painel da dona já lida
com isso (o atalho de WhatsApp só aparece para quem tem número).

## Como o código é organizado (arquitetura em 3 camadas)

```
Salao/gestao/
├── Controller/     # recebe o request, devolve a resposta (as "views")
│   ├── homeController.py       # home e galeria (públicas)
│   ├── cadastroController.py   # /cadastro/
│   ├── loginGoogleController.py # /login/google/ (botão do Google)
│   ├── agendaController.py     # /agendar/ + API de horários
│   └── dashboardController.py  # painel do cliente e da dona
├── services/       # REGRAS DE NEGÓCIO (o cérebro)
│   ├── agendaService.py        # disponibilidade, conflito, status
│   ├── cadastroService.py      # formulário/validações de cadastro
│   ├── loginGoogleService.py   # valida credencial Google, cria a conta
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

Para testar a stack de produção localmente (sem HTTPS):

```bash
cd salao
cp .env.example .env            # ajuste senhas e gere um SECRET_KEY
docker compose up --build       # web na porta 8000
```

## Subindo para a internet (VPS + Docker + Caddy)

A stack `docker-compose.prod.yml` coloca um **Caddy** na frente do
gunicorn: ele obtém e renova o certificado HTTPS sozinho (Let's Encrypt)
e redireciona http→https. Roteiro completo em um VPS Ubuntu:

```bash
# 0. Antes de tudo: aponte o DNS do domínio (registro A) para o IP do VPS.

# 1. No VPS: instalar Docker
curl -fsSL https://get.docker.com | sh

# 2. Clonar o projeto e configurar
git clone <url-do-repo> salao && cd salao
cp .env.example .env
nano .env    # preencher TUDO (checklist abaixo)

# 3. Subir
docker compose -f docker-compose.prod.yml up -d --build

# 4. Criar a conta real da dona (e NÃO rodar o seed em produção)
docker compose -f docker-compose.prod.yml exec web \
    python Salao/manage.py createsuperuser
```

**Checklist do `.env` de produção:**

| Variável | Valor |
|----------|-------|
| `DJANGO_SECRET_KEY` | chave nova e forte (comando no .env.example) |
| `DJANGO_DEBUG` | `False` |
| `DJANGO_ALLOWED_HOSTS` | `seu-dominio.com.br` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://seu-dominio.com.br` |
| `DJANGO_HTTPS` | `1` (o Caddy cuida do certificado) |
| `DOMINIO` | `seu-dominio.com.br` (usado pelo Caddy) |
| `USE_POSTGRES` / `POSTGRES_*` | senha forte; `POSTGRES_HOST=db` |
| `GOOGLE_OAUTH_CLIENT_ID` | o client_id — e adicione `https://seu-dominio.com.br` nas origens autorizadas do Google Cloud |

**Depois do primeiro deploy:**

- **Backup diário** (crontab): `docker compose -f docker-compose.prod.yml exec -T db pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup.sql` + cópia do volume `media_files`.
- **Atualizar o site**: `git pull && docker compose -f docker-compose.prod.yml up -d --build` (o entrypoint roda migrate/collectstatic sozinho).
- **Monitorar**: UptimeRobot (grátis) apontando para a home; logs com `docker compose -f docker-compose.prod.yml logs -f web`.

## Documentação de contexto

A pasta [`contexto_sistema/`](contexto_sistema/) guarda a visão geral,
os modelos/fluxos e o histórico de correções de bugs do projeto.
