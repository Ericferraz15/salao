"""
models.py — as TABELAS do sistema, descritas como classes Python.

Mapa mental de quem se relaciona com quem:

    Usuario (login) ──1:1── ClienteProfile ─┐
    Usuario (login) ──1:1── Funcionario ────┤
                             │              ├──> Agendamento <── Servico
    JornadaTrabalho ──N:1────┘              │         │
                                            │         └──> TransacaoFinanceira
    Produto (estoque, independente)         │               (receita lançada
                                            └───────────────na conclusão)

Cada classe vira uma tabela no banco (via migrations); cada atributo
vira uma coluna. Regras que envolvem VÁRIOS models ficam nos services —
aqui só entram os campos e pequenas conveniências (@property).
"""

from django.db import models
from django.contrib.auth.models import AbstractUser
# pyrefly: ignore [missing-import]
from .utils.constants import STATUS_CHOICES, DIAS_SEMANA


class Usuario(AbstractUser):
    """Usuário de login (clientes, profissionais e a dona).

    Herda de AbstractUser: username, senha (com hash), e-mail etc. vêm
    de graça. Definir AUTH_USER_MODEL desde o início do projeto é
    importante — trocar depois de ter dados é trabalhoso.

    - email é unique: é o identificador de contato (e o login das contas
      novas — o cadastro define username = e-mail).
    - celular é unique, mas opcional (blank/null): nem todo perfil
      administrativo precisa de telefone.
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

    @property
    def is_funcionario(self) -> bool:
        """True se o usuário é da EQUIPE (tem um registro de Funcionario).

        É o "crachá" de profissional, análogo ao ClienteProfile do cliente.
        Serve para separar papéis: a dona é identificada por
        is_staff/is_superuser; a profissional, por este vínculo. Usado nos
        templates ({% if user.is_funcionario %}) e nas checagens de acesso.
        """
        return Funcionario.objects.filter(usuario=self).exists()


class ClienteProfile(models.Model):
    """Marca um Usuario como CLIENTE do salão (padrão "profile").

    Por que não usar o Usuario direto? Porque nem todo usuário é cliente
    (a dona e as profissionais também têm login). O OneToOne funciona
    como um "crachá": quem tem ClienteProfile pode agendar.
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
    """Profissional que atende no salão (também é um Usuario, via 1:1).

    esta_ativo permite "desligar" uma profissional sem apagar o
    histórico dela: inativa some das opções de agendamento, mas os
    agendamentos antigos continuam íntegros.
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

    esta_ativo = models.BooleanField(default=True, verbose_name='está ativo')

    class Meta:
        verbose_name = 'Funcionário'
        verbose_name_plural = 'Funcionários'

    def __str__(self):
        return self.usuario.get_full_name()


class Servico(models.Model):
    """Serviço do catálogo (ex.: Esmaltação em Gel, 60 min, R$ 70).

    A duração alimenta a grade de horários (um serviço de 120 min ocupa
    4 slots de 30); o preço vira o valor_cobrado quando alguém agenda.
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
    """A reserva em si: quem, com quem, o quê e quando.

    - data_hora_inicio/fim são aware (UTC no banco, SP na exibição).
    - valor_cobrado congela o preço do serviço no momento da reserva.
    - status segue o ciclo de STATUS_CHOICES; as transições válidas são
      controladas pelo agendaService (não mude o status "na mão").
    - db_index nos campos mais filtrados acelera as consultas de
      conflito e das listagens.
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
    """Expediente semanal de uma profissional (uma linha por dia).

    Ex.: (Eduarda, dia 0=segunda, 09:00, 18:00). Sem jornada cadastrada
    a profissional NÃO aparece com horários para as clientes.
    ATENÇÃO: dia_da_semana usa 0-6 (0=segunda), o mesmo padrão de
    datetime.weekday() — usar 1-7 aqui já quebrou o sistema no passado.
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
    """Item de estoque (venda ou uso interno) com alerta de reposição.

    Quando quantidade_estoque < estoque_minimo, o painel mostra o aviso
    "repor!" (via @property abaixo_estoque_minimo).
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
    """Livro-caixa: cada linha é dinheiro que ENTROU ou SAIU.

    Entra de dois jeitos: automático (agendamento concluído) ou manual
    (dona lança venda/despesa pelo painel). A FK opcional `agendamento`
    diz de onde veio a receita — e permite a checagem de idempotência
    (não lançar duas vezes a receita do mesmo atendimento).
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
