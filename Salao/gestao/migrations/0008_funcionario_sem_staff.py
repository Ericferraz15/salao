"""Rebaixa profissionais que haviam sido criados como staff/admin.

Antes, cadastrar um funcionário pelo painel marcava is_staff=True, dando a
ele acesso TOTAL ao painel da dona. A regra mudou: profissional é
identificado pelo registro de Funcionario e usa o painel do profissional
(própria agenda + caixa). Esta migração alinha os dados já existentes:
tira is_staff de quem tem Funcionario e NÃO é superusuário (a dona, criada
com create_superuser, é preservada).
"""

from django.db import migrations


def rebaixar_funcionarios(apps, schema_editor):
    Usuario = apps.get_model('gestao', 'Usuario')
    (
        Usuario.objects
        .filter(is_staff=True, is_superuser=False, funcionario__isnull=False)
        .update(is_staff=False)
    )


def reverter(apps, schema_editor):
    # Sem volta automática: não dá para saber quais funcionários eram staff
    # "de propósito". Reverter é um no-op seguro.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('gestao', '0007_funcionario_foto_servico_foto'),
    ]

    operations = [
        migrations.RunPython(rebaixar_funcionarios, reverter),
    ]
