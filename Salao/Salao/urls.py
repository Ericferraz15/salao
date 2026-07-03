"""
urls.py (projeto) — o "mapa" de rotas de mais alto nível.

Tudo que é do salão mora no app gestao (include abaixo); /admin/ é o
painel técnico interno do Django.
"""

from django.conf import settings
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve


def servir_media(request, path):
    """Serve as fotos enviadas (MEDIA) pelo próprio Django.

    Em um site grande isso ficaria a cargo de um nginx/CDN; aqui o deploy
    é só gunicorn no Docker, então servir pelo Django é simples e
    suficiente para o porte do salão. Ler settings.MEDIA_ROOT aqui dentro
    (e não na definição da rota) permite trocá-lo nos testes.
    """
    return serve(request, path, document_root=settings.MEDIA_ROOT)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('gestao.urls')),
    re_path(r'^media/(?P<path>.*)$', servir_media, name='media'),
]
