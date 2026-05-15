from django.urls import path
from . import views

app_name = 'audit'

urlpatterns = [
    path('logs/', views.log_list, name='log_list'),
    path('maintenance/', views.system_maintenance, name='maintenance'),
    path('maintenance/reset/', views.system_reset, name='reset'),
]
