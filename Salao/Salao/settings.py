"""
Django settings for Salao project.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR.parent / '.env.local', override=True)
load_dotenv(BASE_DIR.parent / '.env', override=False)

# ─── SEGURANÇA ────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'chave-insegura-apenas-para-desenvolvimento-TROQUE-EM-PRODUCAO'
)

DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost').split(',')

# ─── APLICAÇÕES ───────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'gestao',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'Salao.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'Salao.wsgi.application'

# ─── BANCO DE DADOS ───────────────────────────────────────────────────────────
# USE_POSTGRES=1 ativa PostgreSQL (Docker/produção).
# Sem essa flag, o Django usa SQLite para dev local sem precisar de psycopg2.
if os.environ.get('USE_POSTGRES', '') == '1':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ['POSTGRES_DB'],
            'USER': os.environ['POSTGRES_USER'],
            'PASSWORD': os.environ['POSTGRES_PASSWORD'],
            'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
            'PORT': os.environ.get('POSTGRES_PORT', '5432'),
            'OPTIONS': {
                'connect_timeout': 5,
            },
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ─── VALIDAÇÃO DE SENHAS ──────────────────────────────────────────────────────
# Regra única e amigável: pelo menos 6 caracteres.
#
# Os validadores extras do Django (senha parecida com o nome, senha comum,
# senha só de números) barravam senhas que o público do salão realmente usa
# e tornavam o cadastro frustrante. Para contas de agendamento o risco é
# baixo; se um dia o sistema guardar dados sensíveis, basta reativá-los aqui.
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 6},
    },
]

# ─── INTERNACIONALIZAÇÃO ──────────────────────────────────────────────────────
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

# ─── ARQUIVOS ESTÁTICOS ───────────────────────────────────────────────────────
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# ─── ARQUIVOS DE MÍDIA (uploads) ──────────────────────────────────────────────
# Estáticos = arquivos DO projeto (CSS, JS, imagens fixas).
# Mídia = arquivos ENVIADOS pelo uso (fotos de serviços e profissionais).
# O upload vai parar em MEDIA_ROOT e é servido na URL MEDIA_URL
# (rota registrada em Salao/urls.py).
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

if not DEBUG:
    STORAGES = {
        'staticfiles': {
            'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
        },
    }

# ─── AUTENTICAÇÃO ─────────────────────────────────────────────────────────────
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'gestao.Usuario'

# Login aceita e-mail OU username (ver gestao/backends.py). Contas novas
# usam o e-mail como login; as antigas ('admin' do seed) seguem funcionando.
AUTHENTICATION_BACKENDS = ['gestao.backends.EmailOuUsernameBackend']

LOGIN_URL = 'login_cliente'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'home'

# ─── SEGURANÇA HTTPS (opcional) ───────────────────────────────────────────────
# Ligue com DJANGO_HTTPS=1 SOMENTE quando o site estiver atrás de HTTPS de
# verdade (domínio com certificado). Antes isso era automático com
# DEBUG=False, o que QUEBRAVA o deploy em rede local via http:// — os
# cookies "Secure" impedem o login e SECURE_SSL_REDIRECT manda todo mundo
# para um https que não existe.
if os.environ.get('DJANGO_HTTPS', '') == '1':
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    # Completa o HSTS (max-age de 1 ano + includeSubDomains); permite
    # inscrição na preload list e silencia o aviso security.W021.
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = True

# ─── LOGGING ──────────────────────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'padrao': {
            'format': '[{asctime}] {levelname} {name}: {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'padrao',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'gestao': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
