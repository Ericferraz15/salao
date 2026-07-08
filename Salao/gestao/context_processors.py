"""
context_processors.py — variáveis extras disponíveis em TODOS os templates.

Um "context processor" é uma função que o Django chama a cada render e
cujo retorno (um dicionário) entra no contexto de qualquer template.
Registrado em settings.TEMPLATES['OPTIONS']['context_processors'].
"""

from django.conf import settings


def google_client_id(request):
    """Expõe o client_id do Google para o botão "Entrar com o Google".

    As telas de login e cadastro usam {% if GOOGLE_OAUTH_CLIENT_ID %}
    para decidir se mostram o botão: sem a variável de ambiente
    configurada, o valor fica vazio e o botão simplesmente não aparece.
    """
    return {'GOOGLE_OAUTH_CLIENT_ID': settings.GOOGLE_OAUTH_CLIENT_ID}
