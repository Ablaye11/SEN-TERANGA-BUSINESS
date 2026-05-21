from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    path('pos/', views.pos_view, name='pos'),
    path('api/search-units/', views.search_units, name='search_units'),
    path('api/process/', views.process_sale, name='process_sale'),
    path('profit-report/', views.profit_report, name='profit_report'),
    path('', views.sale_list, name='list'),
    path('<int:pk>/', views.sale_detail, name='detail'),
    path('<int:pk>/invoice/', views.sale_invoice, name='invoice'),
    path('<int:pk>/payment/', views.add_payment, name='add_payment'),
    path('<int:pk>/cancel/', views.cancel_sale, name='cancel'),
    path('export/sales/', views.export_sales_csv, name='export_sales'),
    path('export/profits/', views.export_profit_csv, name='export_profits'),
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/<int:pk>/delete/', views.delete_expense, name='delete_expense'),
    path('cash-register/', views.cash_register_overview, name='cash_register_overview'),
    path('cash-register/open/', views.open_cash_register, name='open_cash_register'),
    path('cash-register/close/', views.close_cash_register, name='close_cash_register'),
    path('<int:pk>/receipt/', views.receipt, name='receipt'),
    path('stats/', views.advanced_stats, name='advanced_stats'),
]
