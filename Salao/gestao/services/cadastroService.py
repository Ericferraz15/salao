#type: ignore
from django import forms
from django.contrib.auth.forms import UserCreationForm
from ..models import ClienteProfile

class ClienteRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, label='Email (para contato)')
    telefone = forms.CharField(max_length=15, required=False, label='Telefone')
    first_name = forms.CharField(max_length=150, required=True, label='Nome')
    last_name = forms.CharField(max_length=150, required=True, label='Sobrenome')
    password1 = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput,
        help_text='A senha deve ter pelo menos 8 caracteres.'
    )
    class Meta(UserCreationForm.Meta):
        fields = UserCreationForm.Meta.fields + ('first_name', 'last_name', 'email', 'telefone')