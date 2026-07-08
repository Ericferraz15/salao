"""
urls.py (app gestao) — cada URL do site apontando para seu controller.

O `name=` de cada rota é como os templates a referenciam
({% url 'criar_agendamento' %}) — assim dá para mudar o endereço sem
caçar links espalhados pelo HTML.
"""

from django.urls import path
from django.contrib.auth import views as auth_views
# pyrefly: ignore [missing-import]
from .Controller.agendaController import criar_agendamento_controller, api_horarios_disponiveis
# pyrefly: ignore [missing-import]
from .Controller.homeController import home, galeria, termos, privacidade
# pyrefly: ignore [missing-import]
from .Controller.cadastroController import cliente_registro_controller
# pyrefly: ignore [missing-import]
from .Controller.loginGoogleController import login_google_controller
# pyrefly: ignore [missing-import]
from .Controller.dashboardController import (
    dashboard_cliente_controller,
    cancelar_agendamento_controller,
    dashboard_admin_controller,
    gerenciar_agendamento_controller,
    ajustar_estoque_controller,
    remover_jornada_controller,
    dashboard_funcionario_controller,
    gerenciar_meu_agendamento_controller,
)
# pyrefly: ignore [missing-import]
from .forms import LoginForm

urlpatterns = [
    path('', home, name='home'),
    path('galeria/', galeria, name='galeria'),
    path('termos/', termos, name='termos'),
    path('privacidade/', privacidade, name='privacidade'),
    path('admin-dashboard/', dashboard_admin_controller, name='dashboard_admin'),
    path('admin-dashboard/agendamento/<int:agendamento_id>/', gerenciar_agendamento_controller, name='gerenciar_agendamento'),
    path('admin-dashboard/produto/<int:produto_id>/estoque/', ajustar_estoque_controller, name='ajustar_estoque'),
    path('admin-dashboard/jornada/<int:jornada_id>/remover/', remover_jornada_controller, name='remover_jornada'),
    path('agendar/', criar_agendamento_controller, name='criar_agendamento'),
    path('api/horarios-disponiveis/', api_horarios_disponiveis, name='api_horarios_disponiveis'),
    path('cadastro/', cliente_registro_controller, name='cadastro_cliente'),
    path('painel/', dashboard_funcionario_controller, name='dashboard_funcionario'),
    path('painel/agendamento/<int:agendamento_id>/', gerenciar_meu_agendamento_controller, name='gerenciar_meu_agendamento'),
    path('meus-agendamentos/', dashboard_cliente_controller, name='dashboard_cliente'),
    path('cancelar-agendamento/<int:agendamento_id>/', cancelar_agendamento_controller, name='cancelar_agendamento'),
    path('login/', auth_views.LoginView.as_view(
        template_name='registration/login.html',
        authentication_form=LoginForm,
    ), name='login_cliente'),
    path('login/google/', login_google_controller, name='login_google'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
]