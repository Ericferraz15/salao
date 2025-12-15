#type: ignore
from django.urls import path
from django.contrib.auth import views as auth_views
# Importações dos seus Controllers
from .Controller.agendaController import criar_agendamento_Controller, listar_agendamentos_controller, cancelar_agendamento_controller
from .Controller.homeController import home
from .Controller.cadastroController import cliente_registro_Controller

urlpatterns = [
    path('', home, name='home'),
    
    path('agendar/', criar_agendamento_Controller, 
        name='criar_agendamento_Controller'
    ),
    path('agendar/listar', listar_agendamentos_controller, 
        name='listar_agendamentos_controller'
    ),
    path('agendar/cancelar', cancelar_agendamento_controller,
        name='cancelar_agendamentos_controller'
    ),
    
    path('cadastro/', cliente_registro_Controller, name='cadastro_cliente'),
    
    path('login/',
        auth_views.LoginView.as_view(template_name='registration/login.html'),
        name='login_cliente'
    ),

    path('logout/', 
        auth_views.LogoutView.as_view(next_page='home'),
        name='logout'
    ),
]