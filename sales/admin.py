from django.contrib import admin
from .models import Sale, SaleItem, Payment, Expense, CashRegisterSession

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'client', 'seller', 'date', 'total_amount', 'amount_paid', 'status')
    list_filter = ('status', 'payment_method', 'date')
    search_fields = ('invoice_number', 'client__name', 'notes')

@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ('sale', 'product', 'product_unit', 'unit_price', 'quantity')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('sale', 'amount', 'payment_method', 'date', 'received_by')
    list_filter = ('payment_method', 'date')

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('amount', 'category', 'date', 'created_by')
    list_filter = ('category', 'date')
    search_fields = ('description',)

@admin.register(CashRegisterSession)
class CashRegisterSessionAdmin(admin.ModelAdmin):
    list_display = ('opened_at', 'closed_at', 'opened_by', 'closed_by', 'initial_cash', 'expected_cash', 'actual_cash', 'status')
    list_filter = ('status', 'opened_at')

