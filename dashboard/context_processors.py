from products.models import Product


def global_context(request):
    """Add global context variables to all templates."""
    context = {
        'app_name': 'SEN TERANGA BUSINESS',
    }
    
    if request.user.is_authenticated:
        # Count low stock alerts for the badge
        low_stock_count = 0
        for p in Product.objects.filter(is_active=True):
            if p.stock_count <= p.alert_threshold:
                low_stock_count += 1
        
        # Count pending repairs
        from sav.models import Repair
        pending_repairs = Repair.objects.filter(status__in=['pending', 'repairing']).count()
        
        context['low_stock_count'] = low_stock_count
        context['pending_repairs_count'] = pending_repairs
        context['total_alerts_count'] = low_stock_count + pending_repairs
    
    return context
