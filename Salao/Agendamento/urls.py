#type: ignore
from django.urls import path
from django.contrib.auth import views as auth_views
# Importações dos seus Views
from .View.agendaController import criar_agendamento_View, listar_agendamentos_View, cancelar_agendamento_View
from .View.homeController import home
from .View.cadastroClienteController import cadastrar_Cliente_View

urlpatterns = [
    path('', home, name='home'),
    
    path('agendar/', criar_agendamento_View, 
        name='criar_agendamento_View'
    ),
    path('agendar/listar', listar_agendamentos_View, 
        name='listar_agendamentos_View'
    ),
    path('agendar/cancelar', cancelar_agendamento_View,
        name='cancelar_agendamentos_View'
    ),
    
    path('cadastro/', cadastrar_Cliente_View , name='cadastro_cliente'),
    
    path('login/',
        auth_views.LoginView.as_view(template_name='registration/login.html'),
        name='login_cliente'
    ),

    path('logout/', 
        auth_views.LogoutView.as_view(next_page='home'),
        name='logout'
    ),
]