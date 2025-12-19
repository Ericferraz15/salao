#type: ignore
from django.urls import path
from django.contrib.auth import views as auth_views
# Importações dos seus Views
from .View.agendaView import criar_agendamento_View, listar_agendamentos_View, cancelar_agendamento_View
from .View.homeView import home
from .View.cadastroView import cliente_registro_View

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
    
    path('cadastro/', cliente_registro_View, name='cadastro_cliente'),
    
    path('login/',
        auth_views.LoginView.as_view(template_name='registration/login.html'),
        name='login_cliente'
    ),

    path('logout/', 
        auth_views.LogoutView.as_view(next_page='home'),
        name='logout'
    ),
]