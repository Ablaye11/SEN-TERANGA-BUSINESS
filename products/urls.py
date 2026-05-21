from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    path('', views.product_list, name='list'),
    path('create/', views.product_create, name='create'),
    path('<int:pk>/', views.product_detail, name='detail'),
    path('<int:pk>/edit/', views.product_edit, name='edit'),
    path('<int:pk>/delete/', views.product_delete, name='delete'),
    path('units/', views.unit_list, name='unit_list'),
    path('units/add/', views.unit_create, name='unit_create'),
    path('units/add/<int:product_pk>/', views.unit_create, name='unit_create_for_product'),
    path('units/<int:pk>/', views.unit_detail, name='unit_detail'),
    path('units/<int:pk>/edit/', views.unit_edit, name='unit_edit'),
    path('units/<int:pk>/delete/', views.unit_delete, name='unit_delete'),
    path('units/<int:pk>/print/', views.print_labels, name='print_labels'),
    path('trace/', views.trace_device, name='trace'),
]
