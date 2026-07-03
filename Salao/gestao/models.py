from django.db import models
from django.contrib.auth.models import AbstractUser
# pyrefly: ignore [missing-import]
from .utils.constants import STATUS_CHOICES, DIAS_SEMANA


class Usuario(AbstractUser):
    """
    Modelo de usuário customizado. Sempre defina AUTH_USER_MODEL no início
    do projeto — mudar depois é trabalhoso.

    CORRIGIDO:
    - email marcado como unique=True (estava sem essa constraint, permitindo
      dois usuários com o mesmo e-mail — falha de integridade grave).
    - celular continua unique, mas agora blank=True para permitir cadastros
      sem telefone caso necessário (ajuste conforme a regra de negócio).
    """

    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='grupos',
        blank=True,
        help_text='Grupos aos quais o usuário pertence.',
        related_name='gestao_usuario_set',
        related_query_name='usuario',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='permissões de usuário',
        blank=True,
        help_text='Permissões específicas deste usuário.',
        related_name='gestao_usuario_permissions',
        related_query_name='usuario_permission',
    )

    first_name = models.CharField(max_length=30, verbose_name='nome')
    last_name = models.CharField(max_length=150, verbose_name='sobrenome')

    # CORRIGIDO: unique=True — e-mail é usado como identificador de contato,
    # dois clientes com o mesmo e-mail causam confusão nos agendamentos.
    email = models.EmailField(max_length=100, unique=True)

    celular = models.CharField(max_length=15, unique=True, null=True, blank=True, verbose_name='celular')

    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'

    def __str__(self):
        return self.get_full_name()

    @property
    def celular_digitos(self) -> str:
        """Celular só com números — pronto para montar link de WhatsApp.

        Cadastros novos já gravam só dígitos, mas contas antigas podem ter
        '(11) 99999-0000'; esta property normaliza na leitura.
        """
        return ''.join(filter(str.isdigit, self.celular or ''))


class ClienteProfile(models.Model):
    """
    Perfil estendido do cliente. Padrão OneToOne é correto aqui.
    """
    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE,
        primary_key=True,
        verbose_name='usuário de login',
    )

    class Meta:
        verbose_name = 'Perfil de Cliente'
        verbose_name_plural = 'Perfis de Clientes'

    def __str__(self):
        return self.usuario.get_full_name()


class Funcionario(models.Model):
    """
    CORRIGIDO: campo renomeado de 'estaAtivo' para 'esta_ativo'
    seguindo o padrão snake_case do Python/Django.
    """
    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE,
        verbose_name='usuário de login',
    )
    especializacao = models.CharField(max_length=100, verbose_name='cargo')

    # Foto do profissional, exibida na hora de agendar para a cliente
    # reconhecer com quem vai marcar. ImageField exige a biblioteca Pillow;
    # o arquivo vai para MEDIA_ROOT/equipe/ e o banco guarda só o caminho.
    foto = models.ImageField(
        upload_to='equipe/',
        null=True,
        blank=True,
        verbose_name='foto do profissional',
    )

    # CORRIGIDO: snake_case (era camelCase 'estaAtivo' — inconsistente com Django)
    esta_ativo = models.BooleanField(default=True, verbose_name='está ativo')

    class Meta:
        verbose_name = 'Funcionário'
        verbose_name_plural = 'Funcionários'

    def __str__(self):
        return self.usuario.get_full_name()


class Servico(models.Model):
    """
    Serviços oferecidos pelo salão.
    CORRIGIDO: verbose_name com acento (era 'Descricao do Servico').
    """
    nome = models.CharField(max_length=100, verbose_name='nome do serviço')
    descricao = models.TextField(verbose_name='descrição do serviço')
    duracao_minutos = models.PositiveIntegerField(verbose_name='duração (minutos)')
    preco = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='preço (R$)'
    )

    # Foto de um trabalho real deste serviço — aparece na vitrine da home e
    # nos cards da tela de agendamento, para a cliente ver o que está
    # escolhendo. Opcional: sem foto, o front mostra um placeholder elegante.
    foto = models.ImageField(
        upload_to='servicos/',
        null=True,
        blank=True,
        verbose_name='foto do serviço',
    )

    class Meta:
        verbose_name = 'Serviço'
        verbose_name_plural = 'Serviços'
        # Defesa em profundidade no banco (além da validação do ServicoForm):
        # garante preço não-negativo e duração positiva mesmo em criações diretas
        # (seed, shell, admin).
        constraints = [
            models.CheckConstraint(
                condition=models.Q(preco__gte=0),
                name='servico_preco_nao_negativo',
            ),
            models.CheckConstraint(
                condition=models.Q(duracao_minutos__gte=1),
                name='servico_duracao_positiva',
            ),
        ]

    def __str__(self):
        return self.nome


class Agendamento(models.Model):
    """
    CORRIGIDO:
    - Campos renomeados de hora_de_inicio/hora_de_fim para data_hora_inicio/data_hora_fim
      (estava inconsistente: o model usava data_hora_*, mas os services
      usavam hora_de_inicio/hora_de_fim — causando AttributeError em runtime).
    - Adicionado db_index=True nos campos mais consultados.
    - valor_cobrado pode ser nulo até confirmação (blank=True, null=True).
    """
    cliente = models.ForeignKey(
        ClienteProfile,
        on_delete=models.CASCADE,
        verbose_name='cliente',
        db_index=True,
    )
    profissional = models.ForeignKey(
        Funcionario,
        on_delete=models.CASCADE,
        verbose_name='profissional',
        db_index=True,
    )
    servico = models.ForeignKey(
        Servico,
        on_delete=models.PROTECT,
        verbose_name='serviço',
    )

    # CORRIGIDO: nomenclatura consistente com o restante do modelo
    data_hora_inicio = models.DateTimeField(
        verbose_name='início do agendamento',
        db_index=True,
    )
    data_hora_fim = models.DateTimeField(verbose_name='fim do agendamento')

    valor_cobrado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='valor cobrado (R$)',
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='PENDENTE',
        db_index=True,
    )

    class Meta:
        verbose_name = 'Agendamento'
        verbose_name_plural = 'Agendamentos'
        # Índice composto para a consulta de conflito (a mais frequente)
        indexes = [
            models.Index(
                fields=['profissional', 'data_hora_inicio', 'data_hora_fim'],
                name='idx_agendamento_conflito',
            )
        ]
        # Garante no banco que o intervalo é válido (fim depois do início),
        # independentemente de quem cria o registro.
        constraints = [
            models.CheckConstraint(
                condition=models.Q(data_hora_fim__gt=models.F('data_hora_inicio')),
                name='agendamento_fim_depois_inicio',
            ),
        ]

    def __str__(self):
        return (
            f'Agendamento de {self.cliente} com {self.profissional} '
            f'para {self.servico} em {self.data_hora_inicio}'
        )


class JornadaTrabalho(models.Model):
    """
    CORRIGIDO: DIAS_SEMANA agora começa em 0 (Monday=0) para alinhar
    com datetime.weekday() — o código original usava 1-7 mas weekday()
    retorna 0-6, o que causava nunca encontrar a jornada correta na verificação.
    """
    funcionario = models.ForeignKey(
        Funcionario,
        on_delete=models.CASCADE,
        verbose_name='funcionário',
    )
    dia_da_semana = models.IntegerField(choices=DIAS_SEMANA, verbose_name='dia da semana')
    hora_inicio = models.TimeField(verbose_name='hora de início do expediente')
    hora_fim = models.TimeField(verbose_name='hora de fim do expediente')

    class Meta:
        # Garante que o funcionário só tenha uma jornada por dia
        unique_together = ('funcionario', 'dia_da_semana')
        verbose_name = 'Jornada de Trabalho'
        verbose_name_plural = 'Jornadas de Trabalho'

    def __str__(self):
        return f'{self.funcionario.usuario.get_full_name()} - {self.get_dia_da_semana_display()}'


class Produto(models.Model):
    """
    CORRIGIDO: nome da classe no singular (era 'Produtos' — viola a
    convenção Django de usar singular para nomes de modelo).
    """
    nome = models.CharField(max_length=100, verbose_name='nome do produto')
    descricao = models.TextField(verbose_name='descrição do produto')
    preco = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='preço (R$)'
    )
    quantidade_estoque = models.PositiveIntegerField(verbose_name='quantidade em estoque')
    estoque_minimo = models.PositiveIntegerField(verbose_name='estoque mínimo')

    class Meta:
        verbose_name = 'Produto'
        verbose_name_plural = 'Produtos'

    def __str__(self):
        return self.nome

    @property
    def abaixo_estoque_minimo(self) -> bool:
        """Facilita alertas no admin e em relatórios."""
        return self.quantidade_estoque < self.estoque_minimo


class TransacaoFinanceira(models.Model):
    """
    CORRIGIDO:
    - Renomeado de 'TransicaoFinanceira' para 'TransacaoFinanceira'
      ('transição' = mudança de estado; 'transação' = operação financeira).
    - Adicionado agendamento FK opcional para rastrear origem da receita.
    """
    TIPO_CHOICES = [
        ('ENTRADA', 'Entrada'),
        ('SAIDA', 'Saída'),
    ]

    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, verbose_name='tipo')
    valor = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='valor (R$)'
    )
    data_hora = models.DateTimeField(auto_now_add=True, verbose_name='data e hora')
    descricao = models.TextField(verbose_name='descrição')

    # Relacionamento opcional — permite rastrear receita por agendamento
    agendamento = models.ForeignKey(
        Agendamento,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transacoes',
        verbose_name='agendamento de origem',
    )

    class Meta:
        verbose_name = 'Transação Financeira'
        verbose_name_plural = 'Transações Financeiras'

    def __str__(self):
        return f'{self.tipo} - R$ {self.valor} em {self.data_hora}'
