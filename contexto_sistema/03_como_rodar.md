# Como Rodar o Sistema

> Atualizado em 2026-07-03.

## Pré-requisitos
- Python 3.12+ (testado com 3.14). Django 6.0. Pillow (fotos) — tudo via
  `requirements.txt`.

## Dev local (SQLite) — recomendado para desenvolvimento

```bash
cd salao
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

cd Salao
python manage.py migrate
python seed.py            # dados de exemplo COM fotos (recomendado)

python manage.py runserver
# http://127.0.0.1:8000
```

Sem `USE_POSTGRES=1`, o projeto usa SQLite automaticamente (`db.sqlite3`).
As fotos enviadas vão para `Salao/media/` (fora do git) e são servidas
em `/media/...` pelo próprio Django.

### Credenciais de exemplo (após `seed.py`)
- **Dona/admin:** `admin` / `admin123` → `/admin-dashboard/`
- **Cliente:** `cliente` / `cliente123` → `/meus-agendamentos/`
- O login aceita e-mail OU username.

## Testes e verificação

```bash
cd salao/Salao
. ../.venv/bin/activate

python manage.py test          # suíte (105 testes)
python simular_uso.py          # ponta-a-ponta (35 verificações)
python manage.py check
python manage.py makemigrations --check --dry-run   # drift de migrations
```

## Produção / Docker (PostgreSQL)

```bash
cd salao
cp .env.example .env           # ajuste credenciais e gere um SECRET_KEY
docker compose up --build
# entrypoint.sh entra em /app/Salao e roda migrate + collectstatic + gunicorn :8000
```

Variáveis (`.env`): `DJANGO_SECRET_KEY`, `DJANGO_DEBUG` (use **False** em
produção), `DJANGO_ALLOWED_HOSTS`, `USE_POSTGRES=1`, `POSTGRES_*` e
**`DJANGO_HTTPS`**:

- `DJANGO_HTTPS=0` (padrão) — para acesso via `http://` (ex.: rede local
  do salão). Cookies funcionam normalmente.
- `DJANGO_HTTPS=1` — SÓ quando houver certificado HTTPS de verdade; liga
  cookies Secure, HSTS e redirect para https.

O `.dockerignore` mantém `.venv`, `db.sqlite3`, `media/` e afins fora da
imagem.

## Notas
- `db.sqlite3`, `.env`, `media/` e `staticfiles/` estão fora do git.
- Aviso `No directory at: .../staticfiles/` nos testes é inofensivo
  (some após `collectstatic`).
- Para `navegador_demo.py`: `pip install playwright && playwright install chromium`.
