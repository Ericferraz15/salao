from django.shortcuts import render
from ..models import *

def home(request):
    if request.method == 'GET':
        return render(request, 'templateCliente/home/home.html', context={})


