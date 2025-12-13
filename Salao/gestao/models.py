from django.db import models
from django.contrib.auth.models import AbstractUser
from .utils.constants import STATUS_CHOICES, DIAS_SEMANA


class Usuario(AbstractUser):
    groups = models.ManyToManyField(
        'auth.Group', 
        verbose_name='grupos',
        blank=True,
        help_text='Os grupos do usuário pertence.',
        related_name="gestao_usuario_set", 
        related_query_name="usuario",
    )

    first_name = models.CharField(
        max_length = 30,
        verbose_name = "nome"
    )
    last_name = models.CharField(
        max_length = 150,
        verbose_name = "sobrenome"
    )

    user_permissions = models.ManyToManyField(
        'auth.Permission', 
        verbose_name='permissões de usuário',
        blank=True,
        help_text='Permissões específicas deste usuário.',
        related_name="gestao_usuario_permissions",
        related_query_name="usuario_permission",
    )
    
    email = models.EmailField(
        max_length = 100
    )
    
    celular = models.CharField(
        max_length = 15,
        unique = True,
        verbose_name = "celular"
    )
    def __str__(self):
        return self.get_full_name()

class ClienteProfile(models.Model):
    usuario = models.OneToOneField(
        Usuario, 
        on_delete = models.CASCADE, 
        primary_key = True, # Define esta FK como a chave principal da tabela
        verbose_name = "Usuário de Login"
    )
    
    class Meta:
        verbose_name = "Perfil de Cliente"
        verbose_name_plural = "Perfis de Clientes"

    def __str__(self):
        return self.usuario.get_full_name() 

class Funcionario(models.Model):
    usuario = models.OneToOneField(
        Usuario, 
        on_delete = models.CASCADE, 
        verbose_name = "Usuário de Login"
    )
    
    especializacao = models.CharField(
        max_length = 100,
        verbose_name = "Cargo"
    )

    # campo para saber a comissao do funcionário

    estaAtivo = models.BooleanField(
        default = True,
        verbose_name = "Está Ativo"
    )
    
    class Meta:
        verbose_name = "Funcionário"
        verbose_name_plural = "Funcionários"

    def __str__(self):
        return self.usuario.get_full_name() 

class Servico(models.Model):
    nome = models.CharField(
        max_length = 100,
        verbose_name = "Nome do Servico"
    )
    
    descricao = models.TextField(
        verbose_name = "Descricao do Servico"
    )
    
    duracao_minutos = models.PositiveIntegerField(
        verbose_name = "Duracao (minutos)"
    )
    
    preco = models.DecimalField(
        max_digits = 10,
        decimal_places = 2,
        verbose_name = "Preco (R$)"
    )
    
    class Meta:
        verbose_name = "Servico"
        verbose_name_plural = "Servicos"

    def __str__(self):
        return self.nome

class Agendamento(models.Model):
    cliente = models.ForeignKey(
        ClienteProfile,
        on_delete = models.CASCADE,
        verbose_name = "Cliente"
    )
    
    profissional = models.ForeignKey(
        Funcionario,
        on_delete = models.CASCADE,
        verbose_name = "Profissional"
    )
    
    servico = models.ForeignKey(
        Servico,
        on_delete = models.PROTECT,
        verbose_name = "Servico"
    )

    data_hora_inicio = models.DateTimeField(
        verbose_name = "Início do Agendamento"
    )

    data_hora_fim = models.DateTimeField(
        verbose_name = "Fim do Agendamento"
    )

    valor_cobrado = models.DecimalField(
        max_digits = 10,
        decimal_places = 2,
        verbose_name = "Valor Cobrado (R$)",
    )

    status = models.CharField(
        max_length = 15,
        choices = STATUS_CHOICES,
        default= 'PENDENTE'
    )

    class Meta:
        verbose_name = "Agendamento"
        verbose_name_plural = "Agendamentos"

    def __str__(self):
        return f"Agendamento de {self.cliente} com {self.profissional} para {self.servico} em {self.data_hora_inicio}"

class JornadaTrabalho(models.Model):

    funcionario = models.ForeignKey(
        Funcionario,
        on_delete=models.CASCADE,
        verbose_name="Funcionário"
    )
    dia_da_semana = models.IntegerField(
        choices = DIAS_SEMANA,
        verbose_name = "Dia da Semana"
    )
    hora_inicio = models.TimeField(
        verbose_name = "Hora de Início do Expediente"
    )
    hora_fim = models.TimeField(
        verbose_name = "Hora de Fim do Expediente"
    )
    
    class Meta:
        unique_together = ('funcionario', 'dia_da_semana', 'hora_inicio') 
        verbose_name = "Jornada de Trabalho"
        verbose_name_plural = "Jornadas de Trabalho"

    def __str__(self):
        return f"{self.funcionario.usuario.get_full_name()} - {self.get_dia_da_semana_display()}"# type: ignore
    
class Produtos(models.Model):
    nome = models.CharField(
        max_length = 100,
        verbose_name = "Nome do Produto"
    )
    
    descricao = models.TextField(
        verbose_name = "Descrição do Produto"
    )
    
    preco = models.DecimalField(
        max_digits = 10,
        decimal_places = 2,
        verbose_name = "Preço (R$)"
    )
    
    quantidade_estoque = models.PositiveIntegerField(
        verbose_name = "Quantidade em Estoque"
    )

    estoque_minimo = models.PositiveIntegerField(
        verbose_name = "Estoque Mínimo"
    )

    class Meta:
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"

    def __str__(self):
        return self.nome
    
class TransicaoFinanceira(models.Model):
    tipo = models.CharField(
        max_length = 10,
        choices = [('ENTRADA', 'Entrada'), ('SAIDA', 'Saída')],
        verbose_name = "Tipo de Transição"
    )
    
    valor = models.DecimalField(
        max_digits = 10,
        decimal_places = 2,
        verbose_name = "Valor (R$)"
    )
    
    data_hora = models.DateTimeField(
        auto_now_add = True,
        verbose_name = "Data e Hora"
    )
    
    descricao = models.TextField(
        verbose_name = "Descrição"
    )

    class Meta:
        verbose_name = "Transição Financeira"
        verbose_name_plural = "Transições Financeiras"
    
    def __str__(self):
        return f"{self.tipo} - R$ {self.valor} em {self.data_hora}"