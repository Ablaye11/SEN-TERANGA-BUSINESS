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

from .models import Sale, SaleItem, Payment, Expense, CashRegisterSession
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
    trade_ins = data.get('trade_ins', [])
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
    
    # Calculate trade-in total value
    trade_in_total = sum(int(t.get('valeur', 0)) for t in trade_ins)
    
    # Total to pay is subtotal - discount
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
    
    # Process Trade-ins
    from stock.models import StockMovement
    for t_data in trade_ins:
        if t_data.get('product_id'):
            t_product = get_object_or_404(Product, pk=t_data['product_id'])
        else:
            t_name = t_data.get('new_name', 'Téléphone Repris')
            t_brand = t_data.get('new_brand', 'autre')
            # Create a new product on the fly
            t_product = Product.objects.create(
                name=t_name,
                brand=t_brand,
                category='smartphone',
                purchase_price=0,
                selling_price=0,
                is_active=True
            )
            
        t_valeur = int(t_data.get('valeur', 0))
        t_imei = t_data.get('imei_serial', f"REPRISE-{timezone.now().strftime('%Y%m%d%H%M%S')}")
        
        new_unit = ProductUnit.objects.create(
            product=t_product,
            imei_serial=t_imei,
            condition='occasion',
            status='in_stock',
            purchase_price=t_valeur,
            selling_price=t_valeur + (t_valeur * 0.2), # Default 20% margin
            notes=f"Reprise sur facture {sale.invoice_number}"
        )
        
        StockMovement.objects.create(
            product_unit=new_unit,
            movement_type='in',
            reason=f'Reprise client - Facture {sale.invoice_number}',
            performed_by=request.user,
        )
        
        # Add payment for trade-in
        Payment.objects.create(
            sale=sale,
            amount=t_valeur,
            payment_method='echange',
            reference=t_imei,
            received_by=request.user,
        )
    
    # Create sale items and update stock
    for item_data in items:
        unit = get_object_or_404(ProductUnit, pk=item_data['unit_id'])
        
        # Enforce 1 month warranty for smartphones
        warranty_months = 1 if unit.product.category == 'smartphone' else unit.warranty_months
        
        SaleItem.objects.create(
            sale=sale,
            product=unit.product,
            product_unit=unit,
            unit_price=item_data['price'],
            warranty_months=warranty_months,
        )
        
        # Mark unit as sold
        unit.status = 'sold'
        unit.sold_at = timezone.now()
        # Set warranty end date
        unit.warranty_end = (timezone.now() + timedelta(days=warranty_months * 30)).date()
        unit.save()
        
        StockMovement.objects.create(
            product_unit=unit,
            movement_type='out',
            reason=f'Vente - Facture {sale.invoice_number}',
            performed_by=request.user,
        )
    
    # Create payment (cash/wave/etc.)
    if payment_amount > 0:
        Payment.objects.create(
            sale=sale,
            amount=payment_amount,
            payment_method=payment_method,
            received_by=request.user,
        )
    
    # Determine sale status
    total_paid = sale.amount_paid
    if total_paid >= total:
        sale.status = 'completed'
    elif total_paid > 0:
        sale.status = 'partial'
    else:
        sale.status = 'pending'
    
    if trade_in_total > 0 and payment_amount > 0:
        sale.payment_method = 'mixte'
    elif trade_in_total > 0 and payment_amount == 0:
        sale.payment_method = 'echange'
        
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
    if not request.user.is_admin_user:
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

        # Exclude cancelled sales from profit report
        sales_in_month = Sale.objects.filter(
            date__range=(month_start, month_end),
            status__in=['completed', 'partial']
        )
        items_in_month = SaleItem.objects.filter(sale__in=sales_in_month)
        
        revenue = sales_in_month.aggregate(total=Sum('total_amount'))['total'] or 0
        
        profit = 0
        for item in items_in_month:
            if item.product_unit:
                profit += (item.unit_price - item.product_unit.effective_purchase_price)
        
        discounts = sales_in_month.aggregate(total=Sum('discount'))['total'] or 0
        gross_profit = profit - discounts

        # Get monthly expenses
        month_expenses = Expense.objects.filter(
            date__range=(month_start, month_end)
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        real_net_profit = gross_profit - month_expenses

        months_data.append({
            'month': month_start.strftime('%B %Y'),
            'revenue': revenue,
            'gross_profit': gross_profit,
            'expenses': month_expenses,
            'profit': real_net_profit,
            'margin': (real_net_profit / revenue * 100) if revenue > 0 else 0
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
    
    sales = Sale.objects.exclude(status='cancelled').order_by('-date')
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


@login_required
def expense_list(request):
    """List and create expenses."""
    from django.db.models import Sum
    
    # Check if form submitted to add a new expense
    if request.method == 'POST':
        amount = request.POST.get('amount')
        category = request.POST.get('category', 'other')
        description = request.POST.get('description', '')
        date_str = request.POST.get('date')
        
        if amount:
            expense = Expense(
                amount=int(amount),
                category=category,
                description=description,
                created_by=request.user
            )
            if date_str:
                expense.date = date_str
            expense.save()
            
            # Log the action
            from audit.models import log_action
            log_action(
                user=request.user,
                action='expense',
                description=f"Dépense ajoutée: {expense.amount} FCFA - Catégorie: {expense.get_category_display()}",
                model_name='Expense',
                object_id=expense.pk
            )
            
            messages.success(request, "La dépense a été enregistrée avec succès.")
            return redirect('sales:expense_list')
        else:
            messages.error(request, "Le montant de la dépense est requis.")

    # List all expenses
    expenses = Expense.objects.select_related('created_by').all().order_by('-date')
    
    # Filter by date or category
    category_filter = request.GET.get('category', '')
    if category_filter:
        expenses = expenses.filter(category=category_filter)
        
    date_filter = request.GET.get('date', '')
    if date_filter:
        expenses = expenses.filter(date__date=date_filter)

    # Aggregates
    today = timezone.now()
    month_start = today.replace(day=1, hour=0, minute=0, second=0)
    month_expenses_total = Expense.objects.filter(date__gte=month_start).aggregate(total=Sum('amount'))['total'] or 0
    today_expenses_total = Expense.objects.filter(date__date=today.date()).aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'expenses': expenses[:100],
        'category_filter': category_filter,
        'date_filter': date_filter,
        'month_expenses_total': month_expenses_total,
        'today_expenses_total': today_expenses_total,
        'categories': Expense.CATEGORY_CHOICES,
    }
    return render(request, 'sales/expense_list.html', context)


@login_required
def delete_expense(request, pk):
    """Delete an expense."""
    if not request.user.is_admin_user:
        messages.error(request, "Accès refusé. Seul un administrateur peut supprimer une dépense.")
        return redirect('sales:expense_list')
        
    expense = get_object_or_404(Expense, pk=pk)
    amount = expense.amount
    cat = expense.get_category_display()
    expense.delete()
    
    # Log the action
    from audit.models import log_action
    log_action(
        user=request.user,
        action='expense_delete',
        description=f"Dépense supprimée: {amount} FCFA - Catégorie: {cat}",
        model_name='Expense',
        object_id=pk
    )
    
    messages.success(request, "La dépense a été supprimée.")
    return redirect('sales:expense_list')


@login_required
def cash_register_overview(request):
    """Overview of the cash register sessions."""
    from django.db.models import Sum
    
    # Get active session
    active_session = CashRegisterSession.objects.filter(status='open').first()
    
    # If there is an active session, compute real-time expected cash
    if active_session:
        cash_sales = Payment.objects.filter(
            payment_method='cash',
            date__gte=active_session.opened_at
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        expenses_paid = Expense.objects.filter(
            date__gte=active_session.opened_at
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        active_session.cash_sales = cash_sales
        active_session.expenses_paid = expenses_paid
        active_session.expected_cash = active_session.initial_cash + cash_sales - expenses_paid
        active_session.save()
    
    # Get last closed session to pre-fill opening cash
    last_closed = CashRegisterSession.objects.filter(status='closed').order_by('-closed_at').first()
    suggested_initial = last_closed.actual_cash if last_closed else 0
    
    # History of sessions
    sessions = CashRegisterSession.objects.select_related('opened_by', 'closed_by').all().order_by('-opened_at')
    
    context = {
        'active_session': active_session,
        'suggested_initial': suggested_initial,
        'sessions': sessions[:50],
    }
    return render(request, 'sales/cash_register_overview.html', context)


@login_required
def open_cash_register(request):
    """Open a new cash register session."""
    if request.method == 'POST':
        # Check if a session is already open
        active_session = CashRegisterSession.objects.filter(status='open').first()
        if active_session:
            messages.warning(request, "Une session de caisse est déjà ouverte.")
            return redirect('sales:cash_register_overview')
            
        initial_cash = request.POST.get('initial_cash', 0)
        try:
            initial_cash = int(initial_cash)
        except ValueError:
            initial_cash = 0
            
        session = CashRegisterSession.objects.create(
            opened_by=request.user,
            initial_cash=initial_cash,
            expected_cash=initial_cash,
            status='open'
        )
        
        # Log action
        from audit.models import log_action
        log_action(
            user=request.user,
            action='cash_open',
            description=f"Ouverture de caisse - Fond initial: {initial_cash} FCFA",
            model_name='CashRegisterSession',
            object_id=session.pk
        )
        
        messages.success(request, f"La caisse a été ouverte avec un fond de {initial_cash:,} FCFA.")
        
    return redirect('sales:cash_register_overview')


@login_required
def close_cash_register(request):
    """Close the active cash register session."""
    from django.db.models import Sum
    
    active_session = CashRegisterSession.objects.filter(status='open').first()
    if not active_session:
        messages.error(request, "Aucune session de caisse ouverte à clôturer.")
        return redirect('sales:cash_register_overview')
        
    # Calculate totals
    cash_sales = Payment.objects.filter(
        payment_method='cash',
        date__gte=active_session.opened_at
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    expenses_paid = Expense.objects.filter(
        date__gte=active_session.opened_at
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    expected_cash = active_session.initial_cash + cash_sales - expenses_paid
    
    if request.method == 'POST':
        actual_cash = request.POST.get('actual_cash')
        notes = request.POST.get('notes', '')
        
        try:
            actual_cash = int(actual_cash)
        except (ValueError, TypeError):
            messages.error(request, "Veuillez entrer un montant réel valide.")
            return render(request, 'sales/cash_register_close.html', {
                'session': active_session,
                'cash_sales': cash_sales,
                'expenses_paid': expenses_paid,
                'expected_cash': expected_cash,
            })
            
        active_session.closed_at = timezone.now()
        active_session.closed_by = request.user
        active_session.cash_sales = cash_sales
        active_session.expenses_paid = expenses_paid
        active_session.expected_cash = expected_cash
        active_session.actual_cash = actual_cash
        active_session.status = 'closed'
        active_session.notes = notes
        active_session.save()
        
        discrepancy = actual_cash - expected_cash
        discrepancy_str = f"Écart: {discrepancy:,} FCFA" if discrepancy != 0 else "Caisse juste"
        
        # Log action
        from audit.models import log_action
        log_action(
            user=request.user,
            action='cash_close',
            description=f"Clôture de caisse - Attendu: {expected_cash} FCFA, Réel: {actual_cash} FCFA ({discrepancy_str})",
            model_name='CashRegisterSession',
            object_id=active_session.pk
        )
        
        messages.success(request, f"La caisse a été clôturée avec succès. {discrepancy_str}.")
        return redirect('sales:cash_register_overview')
        
    return render(request, 'sales/cash_register_close.html', {
        'session': active_session,
        'cash_sales': cash_sales,
        'expenses_paid': expenses_paid,
        'expected_cash': expected_cash,
    })


@login_required
def receipt(request, pk):
    """Ticket de caisse thermique 80mm."""
    sale = get_object_or_404(Sale, pk=pk)
    items = sale.items.select_related('product', 'product_unit').all()
    return render(request, 'sales/receipt.html', {
        'sale': sale,
        'items': items,
    })


@login_required
def advanced_stats(request):
    """Statistiques avancées avec graphiques."""
    from django.db.models import Sum, Count
    from django.db.models.functions import TruncMonth, ExtractMonth
    from datetime import datetime, timedelta
    from products.models import Product, ProductUnit
    from sales.models import Expense
    
    today = datetime.today()
    year = int(request.GET.get('year', today.year))
    
    # --- Chiffre d'Affaires par mois (Neufs vs Occasions) ---
    monthly_sales = []
    for month in range(1, 13):
        sales_month = Sale.objects.filter(
            date__year=year, date__month=month
        ).exclude(status='cancelled')
        
        total_neuf = 0
        total_occasion = 0
        total_all = 0
        
        for s in sales_month:
            for item in s.items.select_related('product_unit').all():
                price = item.unit_price
                if item.product_unit and item.product_unit.condition in ('occasion', 'reconditionne'):
                    total_occasion += price
                else:
                    total_neuf += price
                total_all += price
        
        monthly_sales.append({
            'month': month,
            'neuf': int(total_neuf),
            'occasion': int(total_occasion),
            'total': int(total_all),
        })
    
    # --- Top Marques vendues ---
    brand_stats = (
        SaleItem.objects.filter(sale__date__year=year)
        .exclude(sale__status='cancelled')
        .values('product__brand')
        .annotate(count=Count('id'), revenue=Sum('unit_price'))
        .order_by('-count')[:8]
    )
    
    # --- Classement vendeurs ---
    seller_stats = (
        Sale.objects.filter(date__year=year)
        .exclude(status='cancelled')
        .values('seller__username', 'seller__first_name', 'seller__last_name')
        .annotate(
            nb_ventes=Count('id'),
            ca_total=Sum('total_amount')
        )
        .order_by('-ca_total')
    )
    
    # --- Bénéfice net par mois (pour admin) ---
    monthly_profit = []
    if request.user.is_admin_user:
        for month in range(1, 13):
            sales_month = Sale.objects.filter(
                date__year=year, date__month=month
            ).exclude(status='cancelled')
            
            marge = sum(s.profit for s in sales_month)
            
            expenses = Expense.objects.filter(
                date__year=year, date__month=month
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            monthly_profit.append({
                'month': month,
                'marge': int(marge),
                'charges': int(expenses),
                'net': int(marge - expenses),
            })
    
    # --- Dettes totales ---
    from clients.models import Client
    total_debts = sum(c.credit_balance for c in Client.objects.all())
    
    context = {
        'monthly_sales': monthly_sales,
        'brand_stats': list(brand_stats),
        'seller_stats': list(seller_stats),
        'monthly_profit': monthly_profit,
        'total_debts': int(total_debts),
        'year': year,
        'years': list(range(2024, today.year + 1)),
    }
    return render(request, 'sales/advanced_stats.html', context)
