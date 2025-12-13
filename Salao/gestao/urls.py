#type: ignore
from django.urls import path
from django.contrib.auth import views as auth_views
# Importações dos seus Controllers
from .Controller.agendaController import criar_agendamento_Controller
from .Controller.homeController import home
from .Controller.cadastroController import cliente_registro_Controller

urlpatterns = [
    path('', home, name='home'),
    
    path('agendar/', criar_agendamento_Controller, 
        name='criar_agendamento_Controller'
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