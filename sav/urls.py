from django.urls import path
from . import views

app_name = 'sav'

urlpatterns = [
    path('', views.repair_list, name='repair_list'),
    path('create/', views.repair_create, name='repair_create'),
    path('<int:pk>/', views.repair_detail, name='repair_detail'),
    path('<int:pk>/print/', views.repair_print, name='repair_print'),
]
