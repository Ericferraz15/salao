"""
backends.py — como o Django confere usuário e senha no login.

O backend padrão (ModelBackend) só procura pelo campo username.
Este backend estende esse comportamento: se não achar um usuário com
aquele username, tenta pelo e-mail. Assim funcionam os dois mundos:

- contas novas: username == e-mail (o cadastro define assim);
- contas antigas (ex.: 'admin' do seed): continuam entrando pelo apelido,
  e também conseguem entrar digitando o e-mail.

Registrado em settings.AUTHENTICATION_BACKENDS.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

Usuario = get_user_model()


class EmailOuUsernameBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None

        # 1ª tentativa: comportamento normal (por username).
        usuario = super().authenticate(request, username=username, password=password, **kwargs)
        if usuario is not None:
            return usuario

        # 2ª tentativa: procura pelo e-mail (case-insensitive).
        try:
            candidato = Usuario.objects.get(email__iexact=username.strip())
        except (Usuario.DoesNotExist, Usuario.MultipleObjectsReturned):
            # Mesmo custo de tempo do caminho feliz (evita revelar, pela
            # rapidez da resposta, se um e-mail existe ou não na base).
            Usuario().set_password(password)
            return None

        if candidato.check_password(password) and self.user_can_authenticate(candidato):
            return candidato
        return None
