from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
import csv
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
import json

from .models import Sale, SaleItem, Payment
from products.models import Product, ProductUnit
from clients.models import Client


@login_required
def pos_view(request):
    """Point of Sale interface."""
    products = Product.objects.filter(is_active=True)
    clients = Client.objects.all().order_by('name')
    
    context = {
        'products': products,
        'clients': clients,
    }
    return render(request, 'sales/pos.html', context)


@login_required
def search_units(request):
    """AJAX: Search available product units."""
    query = request.GET.get('q', '')
    category = request.GET.get('category', '')
    product_id = request.GET.get('product_id', '')
    
    units = ProductUnit.objects.filter(status='in_stock').select_related('product')
    
    if query:
        units = units.filter(
            Q(imei_serial__icontains=query) |
            Q(product__name__icontains=query) |
            Q(product__brand__icontains=query)
        )
    
    if category:
        units = units.filter(product__category=category)
    
    if product_id:
        units = units.filter(product_id=product_id)
    
    data = []
    for unit in units[:50]:
        data.append({
            'id': unit.id,
            'product_id': unit.product.id,
            'product_name': str(unit.product),
            'imei_serial': unit.imei_serial,
            'condition': unit.get_condition_display(),
            'color': unit.color,
            'storage': unit.storage,
            'price': int(unit.effective_selling_price),
            'warranty_months': unit.warranty_months,
        })
    
    return JsonResponse({'units': data})


@login_required
def process_sale(request):
    """Process a sale from POS."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    items = data.get('items', [])
    client_id = data.get('client_id')
    discount = int(data.get('discount', 0))
    payment_method = data.get('payment_method', 'cash')
    payment_amount = int(data.get('payment_amount', 0))
    notes = data.get('notes', '')
    
    if not items:
        return JsonResponse({'error': 'Aucun article sélectionné'}, status=400)
    
    # Create sale
    client = None
    if client_id:
        client = Client.objects.filter(pk=client_id).first()
    
    subtotal = sum(item['price'] for item in items)
    total = subtotal - discount
    
    sale = Sale.objects.create(
        client=client,
        seller=request.user,
        subtotal=subtotal,
        discount=discount,
        total_amount=total,
        payment_method=payment_method,
        notes=notes,
    )
    
    # Create sale items and update stock
    for item_data in items:
        unit = get_object_or_404(ProductUnit, pk=item_data['unit_id'])
        
        SaleItem.objects.create(
            sale=sale,
            product=unit.product,
            product_unit=unit,
            unit_price=item_data['price'],
            warranty_months=unit.warranty_months,
        )
        
        # Mark unit as sold
        unit.status = 'sold'
        unit.sold_at = timezone.now()
        # Set warranty end date
        unit.warranty_end = (timezone.now() + timedelta(days=unit.warranty_months * 30)).date()
        unit.save()
        
        # Create stock movement
        from stock.models import StockMovement
        StockMovement.objects.create(
            product_unit=unit,
            movement_type='out',
            reason=f'Vente - Facture {sale.invoice_number}',
            performed_by=request.user,
        )
    
    # Create payment
    if payment_amount > 0:
        Payment.objects.create(
            sale=sale,
            amount=payment_amount,
            payment_method=payment_method,
            received_by=request.user,
        )
    
    # Determine sale status
    if payment_amount >= total:
        sale.status = 'completed'
    elif payment_amount > 0:
        sale.status = 'partial'
    else:
        sale.status = 'pending'
    sale.save()
    
    # Log the action
    from audit.models import log_action
    log_action(
        user=request.user,
        action='sale',
        description=f"Vente effectuée: {sale.invoice_number} - Total: {sale.total_amount} FCFA",
        model_name='Sale',
        object_id=sale.pk
    )
    
    return JsonResponse({
        'success': True,
        'sale_id': sale.pk,
        'invoice_number': sale.invoice_number
    })


@login_required
def sale_list(request):
    """List all sales."""
    sales = Sale.objects.select_related('client', 'seller').all()
    
    # Filter by date
    date_filter = request.GET.get('date', '')
    if date_filter:
        sales = sales.filter(date__date=date_filter)
    
    status_filter = request.GET.get('status', '')
    if status_filter:
        sales = sales.filter(status=status_filter)
    
    return render(request, 'sales/sale_list.html', {
        'sales': sales[:100],
        'date_filter': date_filter,
        'status_filter': status_filter,
    })


@login_required
def sale_detail(request, pk):
    """Sale detail / Invoice view."""
    sale = get_object_or_404(Sale, pk=pk)
    items = sale.items.select_related('product', 'product_unit').all()
    payments = sale.payments.all()
    
    return render(request, 'sales/sale_detail.html', {
        'sale': sale,
        'items': items,
        'payments': payments,
    })


@login_required
def profit_report(request):
    if request.user.role != 'admin':
        messages.error(request, "Accès réservé aux administrateurs.")
        return redirect('dashboard:index')

    from django.db.models import Sum, F
    from django.utils import timezone
    import datetime

    # Last 6 months
    today = timezone.now()
    months_data = []
    for i in range(6):
        month_start = (today - datetime.timedelta(days=i*30)).replace(day=1, hour=0, minute=0, second=0)
        if i == 0:
            month_end = today
        else:
            # Last day of month
            next_month = month_start + datetime.timedelta(days=32)
            month_end = next_month.replace(day=1) - datetime.timedelta(seconds=1)

        sales_in_month = Sale.objects.filter(date__range=(month_start, month_end))
        items_in_month = SaleItem.objects.filter(sale__in=sales_in_month)
        
        revenue = sales_in_month.aggregate(total=Sum('total_amount'))['total'] or 0
        # Profit = Sum(ItemPrice - UnitPurchasePrice)
        # We need to handle cases where product_unit might be null (though unlikely in our logic)
        profit = 0
        for item in items_in_month:
            if item.product_unit:
                profit += (item.unit_price - item.product_unit.effective_purchase_price)
        
        # Subtract discounts from profit? Yes, because total_amount already accounts for it.
        # Actually, total_amount = subtotal - discount. 
        # So profit = (Sum of margins) - (Total discounts)
        discounts = sales_in_month.aggregate(total=Sum('discount'))['total'] or 0
        net_profit = profit - discounts

        months_data.append({
            'month': month_start.strftime('%B %Y'),
            'revenue': revenue,
            'profit': net_profit,
            'margin': (net_profit / revenue * 100) if revenue > 0 else 0
        })

    return render(request, 'sales/profit_report.html', {'months_data': months_data})


@login_required
def export_sales_csv(request):
    """Export all sales to CSV."""
    if not request.user.is_admin_user:
        return HttpResponse("Non autorisé", status=403)
        
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="ventes_sen_global.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Facture', 'Date', 'Client', 'Total', 'Remise', 'Net Payé', 'Statut'])
    
    sales = Sale.objects.all().order_by('-date')
    for s in sales:
        writer.writerow([
            s.invoice_number,
            s.date.strftime('%d/%m/%Y %H:%M'),
            s.client.name if s.client else 'Passager',
            s.total_amount,
            s.discount,
            s.amount_paid,
            s.get_status_display()
        ])
    return response


@login_required
def export_profit_csv(request):
    """Export profit details to CSV."""
    if not request.user.is_admin_user:
        return HttpResponse("Non autorisé", status=403)
        
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="rapport_profits_sen_global.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Date', 'Facture', 'Total Vente', 'Coût Achat', 'Marge Net'])
    
    sales = Sale.objects.all().order_by('-date')
    for s in sales:
        writer.writerow([
            s.date.strftime('%d/%m/%Y'),
            s.invoice_number,
            s.total_amount,
            s.total_cost,
            s.profit
        ])
    return response


@login_required
def sale_invoice(request, pk):
    """Printable invoice view."""
    sale = get_object_or_404(Sale, pk=pk)
    items = sale.items.select_related('product', 'product_unit').all()
    
    return render(request, 'sales/invoice.html', {
        'sale': sale,
        'items': items,
    })


@login_required
def add_payment(request, pk):
    """Add a payment to an existing sale."""
    sale = get_object_or_404(Sale, pk=pk)
    
    if request.method == 'POST':
        amount = int(request.POST.get('amount', 0))
        method = request.POST.get('payment_method', 'cash')
        reference = request.POST.get('reference', '')
        
        if amount > 0:
            Payment.objects.create(
                sale=sale,
                amount=amount,
                payment_method=method,
                reference=reference,
                received_by=request.user,
            )
            
            # Update sale status
            if sale.amount_remaining <= 0:
                sale.status = 'completed'
            else:
                sale.status = 'partial'
            sale.save()
            
            messages.success(request, f'Paiement de {amount:,} FCFA enregistré.')
        else:
            messages.error(request, 'Montant invalide.')
    
    return redirect('sales:detail', pk=pk)


@login_required
def cancel_sale(request, pk):
    """Cancel a sale and return items to stock."""
    if not request.user.is_admin_user:
        messages.error(request, "Seul l'administrateur peut annuler une vente.")
        return redirect('sales:detail', pk=pk)
    
    sale = get_object_or_404(Sale, pk=pk)
    
    if request.method == 'POST':
        # Return all units to stock
        for item in sale.items.all():
            if item.product_unit:
                item.product_unit.status = 'in_stock'
                item.product_unit.sold_at = None
                item.product_unit.warranty_end = None
                item.product_unit.save()
                
                from stock.models import StockMovement
                StockMovement.objects.create(
                    product_unit=item.product_unit,
                    movement_type='return',
                    reason=f'Annulation vente {sale.invoice_number}',
                    performed_by=request.user,
                )
        
        sale.status = 'cancelled'
        sale.save()
        messages.success(request, f'Vente {sale.invoice_number} annulée. Articles retournés au stock.')
    
    return redirect('sales:detail', pk=pk)
