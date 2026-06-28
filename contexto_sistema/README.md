# Contexto do Sistema — Salão Eduarda Ferraz

Pasta com a documentação de contexto do sistema (gerada para não se perder o
contexto) e o relatório da verificação/correção de bugs.

- [01_visao_geral.md](01_visao_geral.md) — o que é, stack e arquitetura em camadas.
- [02_modelos_e_fluxos.md](02_modelos_e_fluxos.md) — modelos de dados e fluxos principais.
- [03_como_rodar.md](03_como_rodar.md) — como rodar (dev/SQLite, Docker/Postgres) e testar.
- [RELATORIO_BUGS.md](RELATORIO_BUGS.md) — **relatório de bugs encontrados, correções e testes**.

## TL;DR da verificação (2026-06-28)

Sistema rodado e verificado: `manage.py check` ok, **26 testes** ok, simulação
ponta-a-ponta **35/35** ok, servidor respondendo. Foram corrigidos **3 bugs**
remanescentes (timezone no painel admin, `except` amplo demais, agendamento no
passado), cada um com teste de regressão. Detalhes em
[RELATORIO_BUGS.md](RELATORIO_BUGS.md).
