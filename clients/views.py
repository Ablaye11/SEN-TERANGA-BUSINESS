from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Client
from .forms import ClientForm


@login_required
def client_list(request):
    query = request.GET.get('q', '')
    clients = Client.objects.all()
    
    if query:
        clients = clients.filter(
            Q(name__icontains=query) | Q(phone__icontains=query)
        )
    
    return render(request, 'clients/client_list.html', {
        'clients': clients, 'query': query
    })


@login_required
def client_detail(request, pk):
    client = get_object_or_404(Client, pk=pk)
    sales = client.sales.all()[:20]
    repairs = client.repairs.all()[:20]
    return render(request, 'clients/client_detail.html', {
        'client': client,
        'sales': sales,
        'repairs': repairs,
        'total_debt': client.credit_balance,
    })


@login_required
def client_create(request):
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            client = form.save()
            messages.success(request, f'Client "{client.name}" ajouté.')
            # If from POS, redirect back
            next_url = request.GET.get('next', '')
            if next_url:
                return redirect(f'{next_url}?client_id={client.pk}')
            return redirect('clients:detail', pk=client.pk)
    else:
        form = ClientForm()
    
    return render(request, 'clients/client_form.html', {
        'form': form, 'title': 'Nouveau Client'
    })


@login_required
def client_edit(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == 'POST':
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, f'Client "{client.name}" modifié.')
            return redirect('clients:detail', pk=client.pk)
    else:
        form = ClientForm(instance=client)
    
    return render(request, 'clients/client_form.html', {
        'form': form, 'title': f'Modifier: {client.name}'
    })


@login_required
def debt_recovery(request):
    """View to list clients with outstanding debts."""
    clients = Client.objects.all()
    debtors = []
    total_debt = 0
    
    for client in clients:
        balance = client.credit_balance
        if balance > 0:
            debtors.append({
                'client': client,
                'balance': balance,
                'last_purchase': client.sales.order_by('-date').first()
            })
            total_debt += balance
            
    return render(request, 'clients/debt_recovery.html', {
        'debtors': debtors,
        'total_debt': total_debt
    })


@login_required
def client_delete(request, pk):
    if not request.user.is_admin_user:
        messages.error(request, "Accès refusé.")
        return redirect('clients:list')
    
    client = get_object_or_404(Client, pk=pk)
    if request.method == 'POST':
        name = client.name
        client.delete()
        messages.success(request, f'Client "{name}" supprimé.')
        return redirect('clients:list')
    return render(request, 'clients/client_confirm_delete.html', {'client': client})
