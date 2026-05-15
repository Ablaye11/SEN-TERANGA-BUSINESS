from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from .models import Product, ProductUnit
from .forms import ProductForm, ProductUnitForm


@login_required
def product_list(request):
    query = request.GET.get('q', '')
    category = request.GET.get('category', '')
    brand = request.GET.get('brand', '')
    
    products = Product.objects.filter(is_active=True)
    
    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(brand__icontains=query)
        )
    if category:
        products = products.filter(category=category)
    if brand:
        products = products.filter(brand=brand)
    
    products = products.annotate(
        total_units=Count('units', filter=Q(units__status='in_stock'))
    )
    
    context = {
        'products': products,
        'categories': Product.CATEGORY_CHOICES,
        'brands': Product.BRAND_CHOICES,
        'query': query,
        'selected_category': category,
        'selected_brand': brand,
    }
    return render(request, 'products/product_list.html', context)


@login_required
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    units = product.units.all()
    context = {
        'product': product,
        'units': units,
        'in_stock': units.filter(status='in_stock').count(),
        'sold': units.filter(status='sold').count(),
    }
    return render(request, 'products/product_detail.html', context)


@login_required
def product_create(request):
    if not request.user.is_admin_user:
        messages.error(request, "Accès refusé.")
        return redirect('dashboard:index')
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            product = form.save()
            from audit.models import log_action
            log_action(request.user, 'create', f"Nouveau produit catalogue: {product}", 'Product', product.pk)
            messages.success(request, f'Produit "{product}" créé avec succès.')
            return redirect('products:detail', pk=product.pk)
    else:
        form = ProductForm(user=request.user)
    
    return render(request, 'products/product_form.html', {
        'form': form, 'title': 'Nouveau Produit'
    })


@login_required
def product_edit(request, pk):
    if not request.user.is_admin_user:
        messages.error(request, "Seul l'administrateur peut modifier les produits.")
        return redirect('products:list')
    
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f'Produit "{product}" modifié avec succès.')
            return redirect('products:detail', pk=product.pk)
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'products/product_form.html', {
        'form': form, 'title': f'Modifier: {product}'
    })


@login_required
def product_delete(request, pk):
    if not request.user.is_admin_user:
        messages.error(request, "Seul l'administrateur peut supprimer des produits.")
        return redirect('products:list')
    
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.is_active = False
        product.save()
        messages.success(request, f'Produit "{product}" supprimé.')
        return redirect('products:list')
    
    return render(request, 'products/product_confirm_delete.html', {'product': product})


@login_required
def unit_create(request, product_pk=None):
    initial = {}
    if product_pk:
        initial['product'] = product_pk
    
    if request.method == 'POST':
        form = ProductUnitForm(request.POST, user=request.user)
        if form.is_valid():
            unit = form.save()
            # Create stock movement
            from stock.models import StockMovement
            StockMovement.objects.create(
                product_unit=unit,
                movement_type='in',
                reason='Ajout initial',
                performed_by=request.user,
            )
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'id': unit.id})
                
            messages.success(request, f'Unité {unit.imei_serial} ajoutée au stock.')
            return redirect('products:detail', pk=unit.product.pk)
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = ProductUnitForm(user=request.user, initial=initial)
    
    return render(request, 'products/unit_form.html', {
        'form': form, 'title': 'Ajouter une Unité'
    })


@login_required
def unit_list(request):
    """List all product units (IMEI/Serial)."""
    units = ProductUnit.objects.select_related('product').all().order_by('-created_at')
    return render(request, 'products/unit_list.html', {'units': units})


@login_required
def unit_detail(request, pk):
    unit = get_object_or_404(ProductUnit, pk=pk)
    movements = unit.movements.all()[:20]
    return render(request, 'products/unit_detail.html', {
        'unit': unit, 'movements': movements
    })


@login_required
def product_delete(request, pk):
    if not request.user.is_admin_user:
        messages.error(request, "Accès refusé.")
        return redirect('products:list')
    
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        name = product.name
        product.delete()
        messages.success(request, f'Produit "{name}" supprimé.')
        return redirect('products:list')
    return render(request, 'products/product_confirm_delete.html', {'product': product})


@login_required
def trace_device(request):
    query = request.GET.get('q', '').strip()
    unit = None
    movements = []
    sale_item = None
    repairs = []
    
    if query:
        from .models import ProductUnit
        from sales.models import SaleItem
        from sav.models import Repair
        from stock.models import StockMovement
        
        unit = ProductUnit.objects.filter(Q(imei_serial__iexact=query)).first()
        if unit:
            movements = StockMovement.objects.filter(product_unit=unit).order_by('created_at')
            sale_item = SaleItem.objects.filter(product_unit=unit).first()
            repairs = Repair.objects.filter(imei_serial__iexact=query)
        else:
            messages.warning(request, f"Aucun appareil trouvé avec l'IMEI/Série : {query}")

    return render(request, 'products/traceability.html', {
        'unit': unit,
        'movements': movements,
        'sale_item': sale_item,
        'repairs': repairs,
        'query': query
    })

@login_required
def unit_edit(request, pk):
    unit = get_object_or_404(ProductUnit, pk=pk)
    if not request.user.is_admin_user:
        messages.error(request, "Seul l'administrateur peut modifier les unités.")
        return redirect('products:detail', pk=unit.product.pk)
    
    if request.method == 'POST':
        form = ProductUnitForm(request.POST, instance=unit)
        if form.is_valid():
            form.save()
            from audit.models import log_action
            log_action(request.user, 'edit', f"Modification appareil: {unit.product} (IMEI: {unit.imei_serial})", 'ProductUnit', unit.pk)
            messages.success(request, f'Unité {unit.imei_serial} modifiée.')
            return redirect('products:detail', pk=unit.product.pk)
    else:
        form = ProductUnitForm(instance=unit)
    
    return render(request, 'products/unit_form.html', {
        'form': form, 'title': f'Modifier Unité: {unit.imei_serial}'
    })

@login_required
def unit_delete(request, pk):
    unit = get_object_or_404(ProductUnit, pk=pk)
    if not request.user.is_admin_user:
        messages.error(request, "Seul l'administrateur peut supprimer des unités.")
        return redirect('products:detail', pk=unit.product.pk)
    
    product_pk = unit.product.pk
    unit.delete()
    messages.success(request, "Unité supprimée du stock.")
    return redirect('products:detail', pk=product_pk)
