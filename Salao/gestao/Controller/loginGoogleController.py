"""
loginGoogleController.py — rota /login/google/ (destino do botão do Google).

O botão fica em registration/_google_login.html (telas de login e
cadastro): quando a cliente escolhe a conta na janelinha do Google, um
JS mínimo preenche um formulário escondido com a credencial e o envia
para cá — um POST normal, com CSRF token do Django, como qualquer outro
formulário do site.

Fluxo: valida a credencial -> acha ou cria o Usuario (ambos no
services/loginGoogleService.py) -> abre a sessão -> redireciona.
"""

from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from ..services.loginGoogleService import (
    CredencialGoogleInvalida,
    obter_ou_criar_usuario,
    validar_credencial_google,
)


@require_POST
def login_google_controller(request):
    try:
        dados = validar_credencial_google(request.POST.get('credential', ''))
    except CredencialGoogleInvalida as erro:
        messages.error(request, str(erro))
        return redirect('login_cliente')

    usuario, foi_criado = obter_ou_criar_usuario(dados)

    if not usuario.is_active:
        # Conta desativada pela dona continua barrada, mesmo vindo do Google
        # (no login comum quem faz essa checagem é o backend de autenticação).
        messages.error(request, 'Esta conta está desativada. Fale com o salão.')
        return redirect('login_cliente')

    # O backend explícito dispensa o authenticate(): a credencial já foi
    # validada pelo Google, não existe senha para conferir.
    login(request, usuario, backend='gestao.backends.EmailOuUsernameBackend')

    if foi_criado:
        # Mesmo destino do cadastro comum: "Meus Agendamentos" faz o
        # onboarding com o CTA de agendar (e renderiza a saudação).
        messages.success(
            request,
            f'Bem-vindo(a), {usuario.first_name}! Sua conta foi criada com o Google.'
        )
        return redirect('dashboard_cliente')

    # Login de quem já tinha conta: respeita o ?next= (ex.: tentou agendar
    # deslogada), mas só para URLs do próprio site — um next externo seria
    # um convite a redirecionar a cliente para um site malicioso.
    destino = request.POST.get('next', '')
    if destino and url_has_allowed_host_and_scheme(
        destino,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(destino)
    return redirect('home')
