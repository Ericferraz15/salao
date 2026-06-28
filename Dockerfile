# Django 6.0 exige Python >= 3.12 (não suporta 3.10/3.11). Com python:3.11 o
# pip install do django>=6.0 falha. 3.13 é a versão usada no desenvolvimento.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

RUN chmod +x /app/entrypoint.sh

WORKDIR /app

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]