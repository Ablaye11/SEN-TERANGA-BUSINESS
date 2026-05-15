from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import AuditLog

@login_required
def log_list(request):
    if request.user.role != 'admin':
        messages.error(request, "Accès refusé.")
        return redirect('dashboard:index')
    
    logs = AuditLog.objects.all()[:200] # Last 200 logs
    return render(request, 'audit/log_list.html', {'logs': logs})

@login_required
def system_maintenance(request):
    if not request.user.is_admin_user:
        messages.error(request, "Accès réservé à l'administrateur.")
        return redirect('dashboard:index')
    return render(request, 'audit/maintenance.html')

@login_required
def system_reset(request):
    if not request.user.is_admin_user:
        return JsonResponse({'success': False, 'message': 'Accès refusé'})
    
    if request.method == 'POST':
        from products.models import Product, ProductUnit
        from clients.models import Client
        from sales.models import Sale, SaleItem, Payment
        from sav.models import Repair
        from stock.models import StockMovement, Supplier, StockEntry
        from .models import AuditLog

        # Delete everything
        Payment.objects.all().delete()
        SaleItem.objects.all().delete()
        Sale.objects.all().delete()
        Repair.objects.all().delete()
        StockMovement.objects.all().delete()
        ProductUnit.objects.all().delete()
        StockEntry.objects.all().delete()
        Supplier.objects.all().delete()
        Client.objects.all().delete()
        Product.objects.all().delete()
        AuditLog.objects.all().delete()
        
        messages.success(request, "Le système a été entièrement réinitialisé.")
        return redirect('dashboard:index')
    
    return redirect('audit:maintenance')
