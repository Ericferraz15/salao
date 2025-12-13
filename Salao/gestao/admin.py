from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User, Group
from .models import *

@admin.register(Usuario)
class CustomUserAdmin(UserAdmin):
    list_display = ( 'first_name', 'last_name', 'email', 'celular','is_staff', 'is_active')
    ordering = ('first_name',)

    
admin.site.register(ClienteProfile)
admin.site.register(Funcionario)
admin.site.register(Servico)

@admin.register(Agendamento)
class AgendamentoAdmin(admin.ModelAdmin):
    list_display = ('data_hora_inicio', 'cliente', 'profissional', 'servico', 'status', 'valor_cobrado')
    list_filter = ('status', 'profissional', 'servico', 'data_hora_inicio')
    search_fields = ('cliente__usuario__email', 'servico__nome')
    
@admin.register(JornadaTrabalho)
class JornadaTrabalhoAdmin(admin.ModelAdmin):
    list_display = ('funcionario', 'dia_da_semana', 'hora_inicio', 'hora_fim')
    list_filter = ('funcionario', 'dia_da_semana')
    search_fields = (
        'funcionario__usuario__email', 
        'funcionario__usuario__first_name',
    )
admin.site.register(TransicaoFinanceira)