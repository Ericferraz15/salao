"""
forms.py — formulários da aplicação (login e painel admin).

Formulário em Django = validação + widgets (o HTML dos campos).
Os de cadastro de cliente moram em services/cadastroService.py;
aqui ficam o login e os formulários usados pelo painel da dona.
"""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import NON_FIELD_ERRORS
# pyrefly: ignore [missing-import]
from .models import JornadaTrabalho, Produto, Servico, Funcionario, TransacaoFinanceira

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
    """Cadastro/edição de serviço pelo painel da dona.

    A foto é opcional (o front tem placeholder), mas recomendada: é ela
    que aparece na vitrine e nos cards da tela de agendamento.
    """

    class Meta:
        model = Servico
        fields = ['nome', 'descricao', 'duracao_minutos', 'preco', 'foto']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do Serviço'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descrição'}),
            'duracao_minutos': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'placeholder': 'Duração em min.'}),
            'preco': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01', 'placeholder': '0.00'}),
            'foto': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
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
        fields = ['especializacao', 'foto', 'esta_ativo']
        widgets = {
            'especializacao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Cargo / Especialização'}),
            'foto': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'esta_ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_email(self):
        # Normaliza para minúsculas/sem espaços, igual ao cadastro de cliente,
        # para a checagem de e-mail duplicado no controller ser consistente
        # (evita "Joao@X.com" e "joao@x.com" como contas distintas).
        return self.cleaned_data['email'].lower().strip()


class TransacaoForm(forms.Form):
    """Lançamento manual no caixa (despesa ou entrada avulsa).

    É um Form "puro" (não ModelForm) de propósito: quem grava é o
    financeiroService.lancar_transacao — o form só desenha os campos e
    faz a primeira validação.
    """

    tipo = forms.ChoiceField(
        choices=TransacaoFinanceira.TIPO_CHOICES,
        initial='SAIDA',
        label='Tipo',
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    valor = forms.DecimalField(
        min_value=0.01,
        decimal_places=2,
        max_digits=10,
        label='Valor (R$)',
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'step': '0.01', 'min': '0.01',
            'placeholder': '0,00',
        }),
    )
    descricao = forms.CharField(
        label='Descrição',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex.: Aluguel de julho, venda de óleo de cutícula...',
        }),
    )


class ProdutoForm(forms.ModelForm):
    """Cadastro de produto do estoque (venda ou uso interno)."""

    class Meta:
        model = Produto
        fields = ['nome', 'descricao', 'preco', 'quantidade_estoque', 'estoque_minimo']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do produto'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Para que serve / observações'}),
            'preco': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01', 'placeholder': '0.00'}),
            'quantidade_estoque': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'placeholder': 'Qtd. atual'}),
            'estoque_minimo': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'placeholder': 'Alerta quando abaixo de...'}),
        }

    def clean_preco(self):
        # DecimalField do model aceita negativo; barramos aqui no form.
        preco = self.cleaned_data['preco']
        if preco < 0:
            raise forms.ValidationError('O preço não pode ser negativo.')
        return preco


class JornadaForm(forms.ModelForm):
    """Expediente semanal de uma profissional (necessário para agendar!).

    Sem jornada cadastrada, a profissional nunca aparece com horários
    disponíveis — por isso o painel dá destaque a este formulário.
    """

    class Meta:
        model = JornadaTrabalho
        fields = ['funcionario', 'dia_da_semana', 'hora_inicio', 'hora_fim']
        widgets = {
            'funcionario': forms.Select(attrs={'class': 'form-control'}),
            'dia_da_semana': forms.Select(attrs={'class': 'form-control'}),
            # type=time abre o seletor de hora nativo do navegador/celular
            'hora_inicio': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'hora_fim': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        }
        error_messages = {
            NON_FIELD_ERRORS: {
                'unique_together': 'Essa profissional já tem jornada nesse dia. '
                                   'Remova a existente para cadastrar outra.',
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Só profissionais ativas aparecem no select
        self.fields['funcionario'].queryset = (
            Funcionario.objects.filter(esta_ativo=True).select_related('usuario')
        )

    def clean(self):
        dados = super().clean()
        inicio, fim = dados.get('hora_inicio'), dados.get('hora_fim')
        if inicio and fim and fim <= inicio:
            raise forms.ValidationError(
                'O fim do expediente precisa ser depois do início.'
            )
        return dados
