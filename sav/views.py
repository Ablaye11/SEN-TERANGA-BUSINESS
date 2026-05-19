from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Repair
from clients.models import Client

@login_required
def repair_list(request):
    repairs = Repair.objects.all()
    status_filter = request.GET.get('status')
    if status_filter:
        repairs = repairs.filter(status=status_filter)

    from django.utils import timezone
    month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    return render(request, 'sav/repair_list.html', {
        'repairs': repairs,
        'status_filter': status_filter,
        'pending_repairs_count': Repair.objects.filter(status__in=['pending', 'diagnostic', 'repairing']).count(),
        'ready_repairs_count': Repair.objects.filter(status='ready').count(),
        'delivered_this_month': Repair.objects.filter(status='delivered', delivered_at__gte=month_start).count(),
    })

@login_required
def repair_create(request):
    clients = Client.objects.all()
    if request.method == 'POST':
        client_id = request.POST.get('client')
        device = request.POST.get('device_name')
        imei = request.POST.get('imei_serial')
        problem = request.POST.get('problem_description')
        cost = request.POST.get('estimated_cost', 0)
        
        repair = Repair.objects.create(
            client_id=client_id,
            device_name=device,
            imei_serial=imei,
            problem_description=problem,
            estimated_cost=cost,
            technician=request.user
        )
        messages.success(request, f"Fiche SAV #{repair.id} créée pour {device}.")
        return redirect('sav:repair_print', pk=repair.id) # Redirect to print page after creation
    
    return render(request, 'sav/repair_form.html', {'clients': clients, 'title': 'Nouvelle Réparation'})

@login_required
def repair_detail(request, pk):
    repair = get_object_or_404(Repair, pk=pk)
    if request.method == 'POST':
        repair.status = request.POST.get('status')
        repair.technician_notes = request.POST.get('technician_notes')
        repair.actual_cost = request.POST.get('actual_cost', 0)
        if repair.status == 'delivered':
            from django.utils import timezone
            repair.delivered_at = timezone.now()
        repair.save()
        messages.success(request, "Statut de réparation mis à jour.")
        return redirect('sav:repair_detail', pk=pk)
    
    return render(request, 'sav/repair_detail.html', {'repair': repair})

@login_required
def repair_print(request, pk):
    repair = get_object_or_404(Repair, pk=pk)
    return render(request, 'sav/repair_print.html', {'repair': repair})
