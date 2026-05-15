from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Supplier, StockEntry, StockMovement
from .forms import SupplierForm, StockEntryForm
from products.models import Product, ProductUnit


@login_required
def stock_overview(request):
    """Stock overview with alerts and valuation."""
    from django.db.models import Sum, F
    
    products = Product.objects.filter(is_active=True)
    product_stock = []
    total_purchase_value = 0
    low_stock_count = 0
    
    for p in products:
        count = p.stock_count
        product_stock.append({
            'product': p,
            'count': count
        })
        # Value = count * average purchase price (using product base purchase price for simplicity)
        total_purchase_value += (count * p.purchase_price)
        if count <= p.alert_threshold:
            low_stock_count += 1
    
    context = {
        'product_stock': product_stock,
        'total_purchase_value': total_purchase_value,
        'low_stock_count': low_stock_count,
        'total_units': ProductUnit.objects.filter(status='in_stock').count(),
    }
    return render(request, 'stock/overview.html', context)


@login_required
def stock_entry_list(request):
    entries = StockEntry.objects.select_related('supplier', 'created_by').all()
    return render(request, 'stock/entry_list.html', {'entries': entries})


@login_required
def stock_entry_create(request):
    if request.method == 'POST':
        form = StockEntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.created_by = request.user
            entry.save()
            messages.success(request, f'Arrivage {entry.reference} enregistré.')
            return redirect('stock:entry_list')
    else:
        form = StockEntryForm(initial={
            'date': timezone.now().date(),
            'reference': f"ARR-{timezone.now().strftime('%Y%m%d-%H%M')}"
        })
    
    return render(request, 'stock/entry_form.html', {
        'form': form, 'title': 'Nouvel Arrivage'
    })


@login_required
def stock_entry_detail(request, pk):
    entry = get_object_or_404(StockEntry, pk=pk)
    movements = entry.movements.select_related('product_unit', 'product_unit__product').all()
    return render(request, 'stock/entry_detail.html', {
        'entry': entry, 'movements': movements
    })


@login_required
def movement_list(request):
    movements = StockMovement.objects.select_related(
        'product_unit', 'product_unit__product', 'performed_by'
    ).all()[:100]
    return render(request, 'stock/movement_list.html', {'movements': movements})


# ---- Supplier views ----

@login_required
def supplier_list(request):
    suppliers = Supplier.objects.all()
    return render(request, 'stock/supplier_list.html', {'suppliers': suppliers})


@login_required
def supplier_create(request):
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Fournisseur ajouté.')
            return redirect('stock:supplier_list')
    else:
        form = SupplierForm()
    return render(request, 'stock/supplier_form.html', {
        'form': form, 'title': 'Nouveau Fournisseur'
    })


@login_required
def supplier_edit(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            messages.success(request, 'Fournisseur modifié.')
            return redirect('stock:supplier_list')
    else:
        form = SupplierForm(instance=supplier)
    return render(request, 'stock/supplier_form.html', {
        'form': form, 'title': f'Modifier: {supplier.name}'
    })
