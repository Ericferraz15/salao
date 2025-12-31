from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

Usuario = get_user_model()

class RegistroClienteForm(UserCreationForm):
    celular = forms.CharField(max_length=15, required=True)
    
    class Meta:
        model = Usuario
        fields = ('email', 'first_name', 'last_name', 'celular', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remova o campo username do formulário se não quiser mostrá-lo
        if 'username' in self.fields:
            del self.fields['username']
    
    def save(self, commit=True):
        user = super().save(commit=False)
        # Se você não tem campo username no formulário, defina-o aqui
        user.username = self.cleaned_data['email']  # ou outra lógica
        if commit:
            user.save()
        return user