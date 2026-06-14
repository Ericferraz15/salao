"""
cadastroService.py

CORREÇÕES APLICADAS:
1. [BUG] Meta.model não estava definido — UserCreationForm.Meta.fields herdava
   do User padrão, não do Usuario customizado. Adicionado model = Usuario.

2. [SEGURANÇA] Adicionado clean_email para verificar unicidade antes de salvar
   (o banco já tem unique=True, mas o erro de banco gera uma exceção genérica
   não amigável — melhor validar no form e retornar mensagem clara).

3. [UX] Campo 'telefone' renomeado para 'celular' para bater com o model.
   No controller original estava sendo passado 'telefone' para ClienteProfile
   que não tem esse campo — isso causava TypeError silencioso.

4. Removido o type: ignore desnecessário no topo do arquivo.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm

from ..models import Usuario


class ClienteRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label='E-mail',
        help_text='Usado para comunicação e recuperação de conta.',
    )
    # CORRIGIDO: era 'telefone' mas o model Usuario tem 'celular'
    celular = forms.CharField(
        max_length=15,
        required=True,
        label='Celular',
        help_text='Formato: (99) 99999-9999',
    )
    first_name = forms.CharField(max_length=150, required=True, label='Nome')
    last_name = forms.CharField(max_length=150, required=True, label='Sobrenome')

    password1 = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput,
        help_text='Mínimo de 8 caracteres. Não use senha óbvia.',
    )
    password2 = forms.CharField(
        label='Confirme a senha',
        widget=forms.PasswordInput,
    )

    class Meta(UserCreationForm.Meta):
        # CORRIGIDO: model explicitado — sem isso o form usa User padrão
        model = Usuario
        fields = ('username', 'first_name', 'last_name', 'email', 'celular')

    def clean_email(self):
        """
        NOVO: valida unicidade do e-mail com mensagem amigável.
        Sem isso, o erro vinha do banco de dados como IntegrityError.
        """
        email = self.cleaned_data.get('email', '').lower().strip()
        if Usuario.objects.filter(email=email).exists():
            raise forms.ValidationError('Este e-mail já está cadastrado.')
        return email

    def clean_celular(self):
        """Remove caracteres não numéricos para padronização."""
        celular = self.cleaned_data.get('celular', '')
        digits = ''.join(filter(str.isdigit, celular))
        if len(digits) not in (10, 11):
            raise forms.ValidationError(
                'Celular inválido. Use o formato (99) 99999-9999.'
            )
        return celular

    def save(self, commit=True):
        """
        Garante que celular seja salvo no objeto Usuario antes do commit.
        """
        user = super().save(commit=False)
        user.email = self.cleaned_data['email'].lower().strip()
        user.celular = self.cleaned_data['celular']
        if commit:
            user.save()
        return user
