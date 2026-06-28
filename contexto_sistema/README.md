# Contexto do Sistema — Salão Eduarda Ferraz

Pasta com a documentação de contexto do sistema (gerada para não se perder o
contexto) e o relatório da verificação/correção de bugs.

- [01_visao_geral.md](01_visao_geral.md) — o que é, stack e arquitetura em camadas.
- [02_modelos_e_fluxos.md](02_modelos_e_fluxos.md) — modelos de dados e fluxos principais.
- [03_como_rodar.md](03_como_rodar.md) — como rodar (dev/SQLite, Docker/Postgres) e testar.
- [RELATORIO_BUGS.md](RELATORIO_BUGS.md) — **relatório de bugs encontrados, correções e testes**.

## TL;DR da verificação (2026-06-28)

Sistema rodado e verificado: `manage.py check` ok, **59 testes** ok (eram 23),
simulação ponta-a-ponta **35/35** ok, `check --deploy` sem avisos, servidor
respondendo, e **build do Docker validado**. Foram corrigidos **12 bugs**
remanescentes + hardening + cosmético:

1. Timezone (UTC×local) nas métricas do painel admin
2. `except` amplo demais mascarando erros
3. Agendamento no passado não bloqueado no back-end
4. `FuncionarioForm.email` sem `max_length` (500 no PostgreSQL)
5. e 6. Mensagens de sucesso (agendar/cadastrar) perdidas ao cair na home
7. Double booking sob concorrência (atomic + select_for_update)
8. Conclusão sem atomicidade entre status e receita
9. Histórico do cliente em ordem invertida
10. Serviço aceitava duração 0 / preço negativo
11. Dockerfile com Python 3.11 (incompatível com Django 6.0) — build quebrado
12. Criação de usuário não-atômica (cadastro/admin) — risco de usuário órfão
+ Hardening `SECURE_HSTS_PRELOAD`, e-mail do admin normalizado, formato monetário

Cada correção tem teste; nos casos aplicáveis, verifiquei que o teste falha no
código antigo. Detalhes em [RELATORIO_BUGS.md](RELATORIO_BUGS.md).
