from django.urls import path
from . import views

app_name = 'stock'

urlpatterns = [
    path('', views.stock_overview, name='overview'),
    path('entries/', views.stock_entry_list, name='entry_list'),
    path('entries/create/', views.stock_entry_create, name='entry_create'),
    path('entries/<int:pk>/', views.stock_entry_detail, name='entry_detail'),
    path('movements/', views.movement_list, name='movement_list'),
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/create/', views.supplier_create, name='supplier_create'),
    path('suppliers/<int:pk>/edit/', views.supplier_edit, name='supplier_edit'),
]
