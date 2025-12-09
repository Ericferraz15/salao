from django.shortcuts import render, redirect
from django.contrib.auth import login
from .models import Agendamento, Servico, Funcionario
from datetime import timedelta

