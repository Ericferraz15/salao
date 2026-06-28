from django import forms
from django.contrib.auth import get_user_model
# pyrefly: ignore [missing-import]
from .models import Servico, Funcionario

Usuario = get_user_model()

class ServicoForm(forms.ModelForm):
    class Meta:
        model = Servico
        fields = ['nome', 'descricao', 'duracao_minutos', 'preco']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do Serviço'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descrição'}),
            'duracao_minutos': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Duração em min.'}),
            'preco': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
        }

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
