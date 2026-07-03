"""
cadastroService.py — regras de negócio do CADASTRO de clientes.

Papel na arquitetura
--------------------
O controller (cadastroController) só recebe a requisição e devolve a
resposta; quem sabe COMO validar e criar um cliente é este módulo.

O formulário abaixo herda de UserCreationForm, que já resolve o mais
delicado (senha digitada 2x, hash seguro via set_password). Nós apenas:

1. Escondemos o campo "username": a cliente não precisa inventar um
   apelido — o e-mail vira o login automaticamente (menos atrito).
2. Adicionamos os campos que o salão precisa (nome, sobrenome, celular).
3. Validamos com mensagens amigáveis em português.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm

from ..models import Usuario


class ClienteRegistrationForm(UserCreationForm):
    """Formulário de criação de conta do cliente (usado em /cadastro/).

    Detalhe importante: os max_length espelham as colunas do model Usuario.
    Se o form aceitar mais que o banco, a validação passa mas o INSERT
    quebra no PostgreSQL ("value too long"). O SQLite não reclama, então
    o erro só apareceria em produção.
    """

    first_name = forms.CharField(
        max_length=30,
        required=True,
        label='Nome',
        widget=forms.TextInput(attrs={
            'placeholder': 'Maria', 'autocomplete': 'given-name',
        }),
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        label='Sobrenome',
        widget=forms.TextInput(attrs={
            'placeholder': 'Silva', 'autocomplete': 'family-name',
        }),
    )
    email = forms.EmailField(
        max_length=100,
        required=True,
        label='E-mail',
        help_text='Será o seu login para entrar no site.',
        widget=forms.EmailInput(attrs={
            'placeholder': 'voce@exemplo.com', 'autocomplete': 'email',
        }),
    )
    celular = forms.CharField(
        max_length=15,
        required=True,
        label='Celular (WhatsApp)',
        widget=forms.TextInput(attrs={
            'placeholder': '(11) 99999-9999', 'autocomplete': 'tel',
            'inputmode': 'tel',
        }),
    )
    password1 = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Crie uma senha', 'autocomplete': 'new-password',
        }),
        help_text='Só precisa ter 6 caracteres ou mais. Pode ser simples!',
    )
    password2 = forms.CharField(
        label='Confirme a senha',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Repita a senha', 'autocomplete': 'new-password',
        }),
    )

    class Meta(UserCreationForm.Meta):
        model = Usuario
        # Sem 'username' aqui: o campo some do formulário e é preenchido
        # automaticamente com o e-mail no save() abaixo.
        fields = ('first_name', 'last_name', 'email', 'celular')

    def clean_email(self):
        """Normaliza (minúsculas, sem espaços) e garante que é único.

        O banco já tem unique=True, mas sem esta checagem o erro chegaria
        como IntegrityError genérico — aqui viramos uma mensagem amigável.
        Também checamos username porque o e-mail vira o login.
        """
        email = self.cleaned_data.get('email', '').lower().strip()
        if Usuario.objects.filter(email=email).exists() \
                or Usuario.objects.filter(username=email).exists():
            raise forms.ValidationError('Este e-mail já está cadastrado. Tente fazer login.')
        return email

    def clean_celular(self):
        """Aceita qualquer formatação, mas exige 10 ou 11 dígitos (DDD + número).

        Guardamos SÓ os dígitos: assim "(11) 99999-0000" e "11999990000"
        são o mesmo celular para a constraint unique do banco.
        """
        celular = self.cleaned_data.get('celular', '')
        digitos = ''.join(filter(str.isdigit, celular))
        if len(digitos) not in (10, 11):
            raise forms.ValidationError(
                'Celular inválido. Use DDD + número, ex.: (11) 99999-9999.'
            )
        if Usuario.objects.filter(celular=digitos).exists():
            raise forms.ValidationError('Este celular já está cadastrado. Tente fazer login.')
        return digitos

    def save(self, commit=True):
        """Preenche o que não veio do formulário antes de gravar.

        super().save(commit=False) monta o objeto Usuario com a senha já
        criptografada, mas ainda sem tocar no banco — aí definimos
        username = e-mail e só então gravamos.
        """
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.username = self.cleaned_data['email']
        user.celular = self.cleaned_data['celular']
        if commit:
            user.save()
        return user
