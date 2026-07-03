"""
homeController.py — páginas públicas: home (vitrine) e galeria.

São as únicas telas que não exigem login: qualquer visitante vê os
serviços, os trabalhos e o contato do salão.
"""

from django.shortcuts import render
# pyrefly: ignore [missing-import]
from ..models import Funcionario, Servico


def home(request):
    """Landing page: hero, sobre, vitrine, equipe, galeria e contato."""
    servicos = Servico.objects.all()
    equipe = (
        Funcionario.objects
        .filter(esta_ativo=True)
        .select_related('usuario')
    )
    return render(request, 'templateCliente/home/home.html', {
        'servicos': servicos,
        'equipe': equipe,
    })


# Categorias do catálogo (slug -> rótulo exibido nos filtros).
CATEGORIAS_GALERIA = [
    ('todos', 'Todos'),
    ('gel', 'Esmaltação em Gel'),
    ('along', 'Alongamento'),
    ('art', 'Nail Art'),
    ('pe', 'Pés'),
]

# Catálogo curado de trabalhos. Cada item aponta para um arquivo em
# static/images/galeria/. Para adicionar um novo trabalho, basta soltar a
# foto naquela pasta e incluir uma linha aqui (arquivo, categoria, título).
TRABALHOS_GALERIA = [
    ('along-francesa-ouro.jpeg', 'along', 'Francesa com Folha de Ouro'),
    ('gel-azul-strass.jpeg', 'gel', 'Azul Royal com Strass'),
    ('art-stiletto-olho-grego.jpeg', 'art', 'Stiletto Azul com Olho Grego'),
    ('along-francesinha.jpeg', 'along', 'Francesinha Clássica'),
    ('gel-branco-glitter.jpeg', 'gel', 'Branco Leitoso com Glitter'),
    ('art-joaninha.jpeg', 'art', 'Vermelho com Joaninhas'),
    ('along-amendoa-preta.jpeg', 'along', 'Amêndoa Francesa Preta'),
    ('gel-azul-marinho.jpeg', 'gel', 'Azul Marinho Decorado'),
    ('along-marrom-marmore.jpeg', 'along', 'Marrom Marmorizado com Ouro'),
    ('gel-glitter-prata.jpeg', 'gel', 'Glitter Prata'),
    ('art-halloween.jpeg', 'art', 'Nail Art Temática'),
    ('gel-preto-nude-coracoes.jpeg', 'gel', 'Nude e Preto com Corações'),
    ('pe-francesinha.jpeg', 'pe', 'Pedicure Francesinha'),
    ('gel-preto-prata.jpeg', 'gel', 'Preto com Detalhe Prata'),
    ('gel-preto-branco-glitter.jpeg', 'gel', 'Mix Preto, Branco e Glitter'),
]


def galeria(request):
    """
    Catálogo de trabalhos. As fotos são servidas como arquivos estáticos
    (static/images/galeria/) e o filtro por categoria é feito no front com JS.
    """
    rotulos = dict(CATEGORIAS_GALERIA)
    trabalhos = [
        {
            'imagem': f'images/galeria/{arquivo}',
            'categoria': categoria,
            'categoria_label': rotulos.get(categoria, categoria),
            'titulo': titulo,
        }
        for arquivo, categoria, titulo in TRABALHOS_GALERIA
    ]
    return render(request, 'templateCliente/galeria/galeria.html', {
        'categorias': CATEGORIAS_GALERIA,
        'trabalhos': trabalhos,
    })
