"""
forms.py — formulários da aplicação (login e painel admin).

Formulário em Django = validação + widgets (o HTML dos campos).
Os de cadastro de cliente moram em services/cadastroService.py;
aqui ficam o login e os formulários usados pelo painel da dona.
"""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
# pyrefly: ignore [missing-import]
from .models import Servico, Funcionario

Usuario = get_user_model()


class LoginForm(AuthenticationForm):
    """Tela de login com cara de "e-mail e senha".

    Por baixo continua sendo o AuthenticationForm do Django (o campo
    interno chama-se 'username'), mas como o cadastro usa o e-mail como
    login, ajustamos rótulos, placeholders e a mensagem de erro.
    """

    error_messages = {
        **AuthenticationForm.error_messages,
        'invalid_login': 'E-mail ou senha incorretos. Confira e tente novamente.',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'E-mail'
        self.fields['username'].widget.attrs.update({
            'placeholder': 'voce@exemplo.com', 'autocomplete': 'username',
        })
        self.fields['password'].label = 'Senha'
        self.fields['password'].widget.attrs.update({
            'placeholder': 'Sua senha', 'autocomplete': 'current-password',
        })


class ServicoForm(forms.ModelForm):
    class Meta:
        model = Servico
        fields = ['nome', 'descricao', 'duracao_minutos', 'preco']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do Serviço'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descrição'}),
            'duracao_minutos': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'placeholder': 'Duração em min.'}),
            'preco': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01', 'placeholder': '0.00'}),
        }

    def clean_duracao_minutos(self):
        # PositiveIntegerField aceita 0; duração 0 geraria slots degenerados na
        # agenda. Exige pelo menos 1 minuto (a checagem no servidor não depende
        # do atributo HTML 'min', que é só dica de UI).
        duracao = self.cleaned_data['duracao_minutos']
        if duracao < 1:
            raise forms.ValidationError('A duração deve ser de pelo menos 1 minuto.')
        return duracao

    def clean_preco(self):
        # DecimalField não impede negativos; um preço negativo geraria receita
        # negativa ao concluir o agendamento.
        preco = self.cleaned_data['preco']
        if preco < 0:
            raise forms.ValidationError('O preço não pode ser negativo.')
        return preco

class FuncionarioForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=30, required=True, label='Nome',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome'}),
    )
    last_name = forms.CharField(
        max_length=150, required=True, label='Sobrenome',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Sobrenome'}),
    )
    # max_length=100 espelha Usuario.email; sem isso o EmailField aceitaria 254
    # e o INSERT falharia no PostgreSQL com e-mail acima de 100 caracteres.
    email = forms.EmailField(
        max_length=100, required=True, label='E-mail',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'E-mail'}),
    )
    celular = forms.CharField(
        max_length=15, required=False, label='Celular',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Celular'}),
    )
    
    class Meta:
        model = Funcionario
        fields = ['especializacao', 'esta_ativo']
        widgets = {
            'especializacao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Cargo / Especialização'}),
            'esta_ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_email(self):
        # Normaliza para minúsculas/sem espaços, igual ao cadastro de cliente,
        # para a checagem de e-mail duplicado no controller ser consistente
        # (evita "Joao@X.com" e "joao@x.com" como contas distintas).
        return self.cleaned_data['email'].lower().strip()
