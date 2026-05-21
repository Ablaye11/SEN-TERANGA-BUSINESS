from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from sales.models import Sale, SaleItem, Expense
from products.models import Product, ProductUnit
from clients.models import Client


@login_required
def dashboard_view(request):
    """Main dashboard with KPIs and statistics."""
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_start = today.replace(day=1)
    
    # Today's sales
    today_sales = Sale.objects.filter(
        date__date=today, status__in=['completed', 'partial']
    )
    today_revenue = today_sales.aggregate(total=Sum('total_amount'))['total'] or 0
    today_count = today_sales.count()
    
    # This week's sales
    week_sales = Sale.objects.filter(
        date__date__gte=week_ago, status__in=['completed', 'partial']
    )
    week_revenue = week_sales.aggregate(total=Sum('total_amount'))['total'] or 0
    
    # This month's sales
    month_sales = Sale.objects.filter(
        date__date__gte=month_start, status__in=['completed', 'partial']
    )
    month_revenue = month_sales.aggregate(total=Sum('total_amount'))['total'] or 0
    month_count = month_sales.count()
    
    # Split revenue into Neuf and Occasion
    month_sales_items = SaleItem.objects.filter(sale__in=month_sales).select_related('product_unit')
    month_revenue_neuf = 0
    month_revenue_occasion = 0
    
    for item in month_sales_items:
        if item.product_unit and item.product_unit.condition in ['occasion', 'reconditionne']:
            month_revenue_occasion += item.line_total
        else:
            month_revenue_neuf += item.line_total
    
    # Monthly profit and expenses (admin only)
    month_profit = 0
    month_expenses = 0
    month_net_profit = 0
    
    if request.user.is_admin_user:
        month_expenses = Expense.objects.filter(
            date__gte=month_start
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        for sale in month_sales:
            month_profit += sale.profit
            
        month_net_profit = month_profit - month_expenses
    
    # Stock stats
    total_in_stock = ProductUnit.objects.filter(status='in_stock').count()
    total_products = Product.objects.filter(is_active=True).count()
    
    # Low stock alerts
    low_stock = []
    for p in Product.objects.filter(is_active=True):
        count = p.stock_count
        if count <= p.alert_threshold:
            low_stock.append({'product': p, 'count': count})
    
    # Top selling products this month
    top_products = SaleItem.objects.filter(
        sale__date__date__gte=month_start,
        sale__status__in=['completed', 'partial']
    ).values(
        'product__name', 'product__brand'
    ).annotate(
        total_sold=Count('id'),
        total_revenue=Sum('unit_price')
    ).order_by('-total_sold')[:5]
    
    # Recent sales
    recent_sales = Sale.objects.select_related('client', 'seller').all()[:10]
    
    # Pending payments
    pending_sales = Sale.objects.filter(
        status__in=['partial', 'pending']
    ).select_related('client')[:10]
    
    # Daily sales for chart (last 7 days)
    daily_data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_sales = Sale.objects.filter(
            date__date=day, status__in=['completed', 'partial']
        )
        day_total = day_sales.aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Calculate profit for this day
        day_profit = 0
        for sale in day_sales:
            day_profit += sale.profit
            
        daily_data.append({
            'date': day.strftime('%d/%m'),
            'total': int(day_total),
            'profit': int(day_profit),
        })
    
    # SAV stats
    from sav.models import Repair
    pending_repairs = Repair.objects.filter(status__in=['pending', 'repairing']).count()
    ready_repairs = Repair.objects.filter(status='ready').count()
    
    # Debt stats
    total_debt = 0
    debtors_count = 0
    for client in Client.objects.all():
        balance = client.credit_balance
        if balance > 0:
            total_debt += balance
            debtors_count += 1

    context = {
        'today_revenue': today_revenue,
        'today_count': today_count,
        'week_revenue': week_revenue,
        'month_revenue': month_revenue,
        'month_revenue_neuf': month_revenue_neuf,
        'month_revenue_occasion': month_revenue_occasion,
        'month_count': month_count,
        'month_profit': month_profit,
        'month_expenses': month_expenses,
        'month_net_profit': month_net_profit,
        'total_in_stock': total_in_stock,
        'total_products': total_products,
        'low_stock': low_stock,
        'top_products': top_products,
        'recent_sales': recent_sales,
        'pending_sales': pending_sales,
        'daily_data': daily_data,
        'total_clients': Client.objects.count(),
        'pending_repairs': pending_repairs,
        'ready_repairs': ready_repairs,
        'total_debt': total_debt,
        'debtors_count': debtors_count,
    }
    return render(request, 'dashboard/index.html', context)


def error_404(request, exception):
    return render(request, '404.html', status=404)


def error_500(request):
    return render(request, '500.html', status=500)
