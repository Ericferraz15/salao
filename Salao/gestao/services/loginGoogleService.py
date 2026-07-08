"""
loginGoogleService.py — regras de negócio do "Entrar com o Google".

Papel na arquitetura
--------------------
O controller (loginGoogleController) só recebe o POST com a credencial;
quem sabe COMO conferir se ela é legítima e COMO transformar a conta
Google em um Usuario do sistema é este módulo.

Como funciona o login com Google (em 3 passos)
----------------------------------------------
1. O botão "Entrar com o Google" (script oficial do Google, incluído em
   registration/_google_login.html) abre a janelinha de escolha de
   conta. Quando a cliente escolhe, o Google devolve para a página uma
   CREDENCIAL: um token assinado dizendo "eu, Google, garanto que quem
   está aqui é a dona de fulana@gmail.com".
2. A página envia essa credencial para /login/google/ e aqui conferimos
   a assinatura com a biblioteca oficial google-auth: validade, emissor
   e se o token foi emitido para o NOSSO client_id — uma credencial
   gerada para outro site não serve neste.
3. Com o e-mail confirmado, buscamos o Usuario correspondente — ou
   criamos um na hora. Para quem é novo, é cadastro e login em um
   clique só (o objetivo do botão).

Contas criadas pelo Google não têm senha local (set_unusable_password):
a pessoa sempre entra pelo botão. E quem JÁ tinha conta com senha pode
usar o botão também — o e-mail é o mesmo, então cai na mesma conta.
"""

import logging

from django.conf import settings
from django.db import transaction

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from ..models import ClienteProfile, Usuario

logger = logging.getLogger(__name__)


class CredencialGoogleInvalida(Exception):
    """Credencial recusada. A mensagem é amigável: vai direto para a tela."""


def validar_credencial_google(credential: str) -> dict:
    """Confere a credencial junto ao Google e devolve os dados dela.

    A verificação é local (assinatura criptográfica, validade, client_id);
    a biblioteca só usa a internet para baixar as chaves públicas do
    Google, que ficam em cache entre uma chamada e outra.
    """
    if not settings.GOOGLE_OAUTH_CLIENT_ID:
        # Sem client_id o botão nem aparece na tela; se um POST chegou
        # aqui mesmo assim, foi montado à mão.
        raise CredencialGoogleInvalida('O login com Google não está configurado.')

    try:
        dados = id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            settings.GOOGLE_OAUTH_CLIENT_ID,
            clock_skew_in_seconds=10,  # tolera relógio do servidor levemente fora
        )
    except Exception:
        logger.warning('Credencial Google recusada na verificação.', exc_info=True)
        raise CredencialGoogleInvalida(
            'Não conseguimos confirmar sua conta Google. Tente de novo.'
        )

    # Só aceitamos e-mail que o Google confirma como verificado — sem isso,
    # alguém poderia registrar uma conta Google com o e-mail de outra pessoa
    # (sem nunca provar que a caixa de entrada é dela) e entrar aqui como ela.
    if not dados.get('email') or not dados.get('email_verified'):
        raise CredencialGoogleInvalida(
            'Sua conta Google não tem e-mail verificado. Use o cadastro comum.'
        )

    return dados


def obter_ou_criar_usuario(dados: dict) -> tuple[Usuario, bool]:
    """Localiza o Usuario pelo e-mail do Google — ou cria um cliente novo.

    Devolve (usuario, foi_criado). O e-mail é normalizado para minúsculas,
    igual ao cadastro comum, para maiúsculas não duplicarem conta.
    """
    email = dados['email'].lower().strip()

    # Procura por e-mail e também por username: contas antigas podem ter
    # username diferente do e-mail (ex.: 'admin' do seed).
    usuario = (
        Usuario.objects.filter(email__iexact=email).first()
        or Usuario.objects.filter(username__iexact=email).first()
    )
    if usuario is not None:
        return usuario, False

    # Mesma receita do cadastro comum (cadastroController): usuário + perfil
    # na mesma transação, para não ficar conta órfã se algo falhar no meio.
    with transaction.atomic():
        usuario = Usuario(
            username=email,
            email=email,
            # O corte no tamanho espelha as colunas do model — o Google não
            # tem limite de nome, o nosso banco tem.
            first_name=(dados.get('given_name') or 'Cliente')[:30],
            last_name=(dados.get('family_name') or '')[:150],
        )
        usuario.set_unusable_password()
        usuario.save()
        ClienteProfile.objects.create(usuario=usuario)

    logger.info('Conta de cliente criada via Google: %s', email)
    return usuario, True
