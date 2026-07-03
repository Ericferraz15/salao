#!/bin/bash
set -e

# O projeto Django (manage.py) fica em /app/Salao — o COPY do Dockerfile
# leva o repositório inteiro para /app. Sem este cd, migrate/collectstatic
# falhavam com "can't open file 'manage.py'" e o container não subia.
cd /app/Salao

echo "[entrypoint] Aplicando migrações do banco de dados..."
python manage.py migrate --noinput

echo "[entrypoint] Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

echo "[entrypoint] Iniciando Gunicorn..."
exec gunicorn Salao.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
