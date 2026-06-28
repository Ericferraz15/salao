# Como Rodar o Sistema

## Pré-requisitos
- Python 3.12+ (testado com 3.14). Django 6.0.

## Dev local (SQLite) — recomendado para desenvolvimento

```bash
cd salao
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

cd Salao
python manage.py migrate
python seed.py            # opcional: dados de exemplo

python manage.py runserver
# http://127.0.0.1:8000
```

Sem a variável `USE_POSTGRES=1`, o projeto usa SQLite automaticamente
(`db.sqlite3`), sem precisar de PostgreSQL.

### Credenciais de exemplo (após `seed.py`)
- **Admin:** usuário `admin` / senha `admin123`
- **Cliente:** usuário `cliente` / senha `cliente123`

## Testes e verificação

```bash
cd salao/Salao
. ../.venv/bin/activate

python manage.py test          # suíte unitária/integração (26 testes)
python simular_uso.py          # simulação ponta-a-ponta (35 verificações)
python manage.py check         # checagem do projeto
python manage.py makemigrations --check --dry-run   # detecta drift de migrations
```

## Produção / Docker (PostgreSQL)

```bash
cd salao
cp .env.example .env           # ajuste as credenciais e gere um SECRET_KEY
docker compose up --build
# entrypoint.sh roda migrate + collectstatic + gunicorn na porta 8000
```

Variáveis relevantes (`.env`): `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`,
`DJANGO_ALLOWED_HOSTS`, `USE_POSTGRES=1`, `POSTGRES_*`.

## Notas
- `db.sqlite3`, `.env`, `.env.local` e `staticfiles/` estão no `.gitignore`.
- O aviso `UserWarning: No directory at: .../staticfiles/` ao rodar testes é
  inofensivo (WhiteNoise; some após `collectstatic`).
- Para o `navegador_demo.py` (demo visual): `pip install playwright` e
  `playwright install chromium`.
