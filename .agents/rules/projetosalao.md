---
trigger: always_on
---

# Construir Novo Robô

**Passo 1: Planejamento Visual**
Analise a estrutura do site alvo. Antes de gerar o código final, crie um plano e exiba como um *Artifact* (artefato visual gerado na interface pela inteligência artificial para acompanhamento) e aguarde aprovação.

**Passo 2: Estruturação**
Prepare as variáveis de ambiente e verifique se as bibliotecas de automação estão listadas nas dependências.

**Passo 3: Execução da Lógica**
Escreva a coleta de dados usando tratamento rigoroso de erros. Inclua registros de log claros para facilitar o rastreio via terminal.

**Passo 4: Integração no Sistema**
Transforme o roteiro em uma tarefa em segundo plano integrada ao Celery e garanta que os resultados sejam gravados no PostgreSQL.

# Adição de Interface React

**Passo 1:** Planeje a estrutura de componentes funcionais. Evite repassar propriedades em excesso.
**Passo 2:** Crie o código focando na comunicação limpa com as rotas do servidor, garantindo o envio correto do token JWT no cabeçalho.
**Passo 3:** Valide os tratamentos de erro caso o servidor falhe, apresentando mensagens claras e diretas na tela.


- Tarefas assíncronas no Celery precisam ser idempotentes e otimizadas.
- Para automação web com Playwright ou Selenium, é obrigatório o uso de esperas dinâmicas. O uso de pausas fixas está proibido.''