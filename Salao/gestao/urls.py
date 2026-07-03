from django.urls import path
from django.contrib.auth import views as auth_views
# pyrefly: ignore [missing-import]
from .Controller.agendaController import criar_agendamento_controller, api_horarios_disponiveis
# pyrefly: ignore [missing-import]
from .Controller.homeController import home, galeria
# pyrefly: ignore [missing-import]
from .Controller.cadastroController import cliente_registro_controller
# pyrefly: ignore [missing-import]
from .Controller.dashboardController import (
    dashboard_cliente_controller,
    cancelar_agendamento_controller,
    dashboard_admin_controller,
    gerenciar_agendamento_controller,
)
# pyrefly: ignore [missing-import]
from .forms import LoginForm

urlpatterns = [
    path('', home, name='home'),
    path('galeria/', galeria, name='galeria'),
    path('admin-dashboard/', dashboard_admin_controller, name='dashboard_admin'),
    path('admin-dashboard/agendamento/<int:agendamento_id>/', gerenciar_agendamento_controller, name='gerenciar_agendamento'),
    path('agendar/', criar_agendamento_controller, name='criar_agendamento'),
    path('api/horarios-disponiveis/', api_horarios_disponiveis, name='api_horarios_disponiveis'),
    path('cadastro/', cliente_registro_controller, name='cadastro_cliente'),
    path('meus-agendamentos/', dashboard_cliente_controller, name='dashboard_cliente'),
    path('cancelar-agendamento/<int:agendamento_id>/', cancelar_agendamento_controller, name='cancelar_agendamento'),
    path('login/', auth_views.LoginView.as_view(
        template_name='registration/login.html',
        authentication_form=LoginForm,
    ), name='login_cliente'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
]