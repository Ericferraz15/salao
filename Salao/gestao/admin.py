"""
admin.py — configura o Django Admin (/admin/), o painel TÉCNICO.

Não confundir com o /admin-dashboard/ (o painel bonito da dona): o
Django Admin é a ferramenta interna de manutenção, que dá acesso cru a
todas as tabelas. Cada classe abaixo diz como um model aparece lá
(colunas da listagem, filtros laterais, campo de busca).
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    Agendamento,
    ClienteProfile,
    Funcionario,
    JornadaTrabalho,
    Produto,
    Servico,
    TransacaoFinanceira,
    Usuario,
)


@admin.register(Usuario)
class CustomUserAdmin(UserAdmin):
    list_display = ('first_name', 'last_name', 'email', 'celular', 'is_staff', 'is_active')
    ordering = ('first_name',)
    search_fields = ('first_name', 'last_name', 'email', 'celular')
    # Adiciona o campo celular nos fieldsets de criação e edição.
    # Sem isso, o campo fica invisível no formulário do admin.
    fieldsets = UserAdmin.fieldsets + (
        ('Dados de Contato', {'fields': ('celular',)}),
    )
    # O formulário de CRIAÇÃO padrão do UserAdmin só pede username/senha —
    # mas aqui nome, sobrenome e e-mail são obrigatórios (e o e-mail é
    # unique). Sem estes campos, criar usuário pelo /admin/ gerava
    # registro incompleto, com e-mail vazio.
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Dados Pessoais', {'fields': ('first_name', 'last_name', 'email')}),
        ('Dados de Contato', {'fields': ('celular',)}),
    )


@admin.register(ClienteProfile)
class ClienteProfileAdmin(admin.ModelAdmin):
    list_display = ('__str__',)
    search_fields = ('usuario__first_name', 'usuario__last_name', 'usuario__email')


@admin.register(Funcionario)
class FuncionarioAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'especializacao', 'esta_ativo')
    list_filter = ('esta_ativo',)
    search_fields = ('usuario__first_name', 'usuario__last_name')


@admin.register(Servico)
class ServicoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'duracao_minutos', 'preco')
    search_fields = ('nome',)


@admin.register(Agendamento)
class AgendamentoAdmin(admin.ModelAdmin):
    list_display = ('data_hora_inicio', 'cliente', 'profissional', 'servico', 'status', 'valor_cobrado')
    list_filter = ('status', 'profissional', 'servico', 'data_hora_inicio')
    search_fields = ('cliente__usuario__email', 'servico__nome')
    date_hierarchy = 'data_hora_inicio'


@admin.register(JornadaTrabalho)
class JornadaTrabalhoAdmin(admin.ModelAdmin):
    list_display = ('funcionario', 'dia_da_semana', 'hora_inicio', 'hora_fim')
    list_filter = ('funcionario', 'dia_da_semana')
    search_fields = (
        'funcionario__usuario__email',
        'funcionario__usuario__first_name',
    )


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'preco', 'quantidade_estoque', 'estoque_minimo', 'abaixo_estoque_minimo')
    search_fields = ('nome',)


@admin.register(TransacaoFinanceira)
class TransacaoFinanceiraAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'valor', 'data_hora', 'descricao')
    list_filter = ('tipo',)
    date_hierarchy = 'data_hora'
