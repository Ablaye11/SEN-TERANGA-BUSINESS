from products.models import Product
from sav.models import Repair

def global_alerts(request):
    if not request.user.is_authenticated:
        return {}
    
    # Count low stock
    low_stock_count = 0
    for p in Product.objects.filter(is_active=True):
        if p.stock_count <= p.alert_threshold:
            low_stock_count += 1
            
    # Count pending repairs
    pending_repairs = Repair.objects.filter(status__in=['pending', 'repairing']).count()
    
    return {
        'GLOBAL_LOW_STOCK': low_stock_count,
        'GLOBAL_PENDING_REPAIRS': pending_repairs,
        'TOTAL_ALERTS': low_stock_count + pending_repairs
    }
