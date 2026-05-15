from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import LoginForm, UserForm
from .models import User


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:index')
    
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Bienvenue, {user.get_full_name() or user.username} !')
            return redirect('dashboard:index')
        else:
            messages.error(request, "Identifiants incorrects.")
    else:
        form = LoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, 'Vous avez été déconnecté.')
    return redirect('accounts:login')


@login_required
def user_list(request):
    if not request.user.is_admin_user:
        messages.error(request, "Accès non autorisé.")
        return redirect('dashboard:index')
    users = User.objects.all().order_by('username')
    return render(request, 'accounts/user_list.html', {'users': users})


@login_required
def user_create(request):
    if not request.user.is_admin_user:
        messages.error(request, "Accès non autorisé.")
        return redirect('dashboard:index')
    
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            password = form.cleaned_data.get('password')
            if password:
                user.set_password(password)
            user.save()
            messages.success(request, f"Utilisateur {user.username} créé avec succès.")
            return redirect('accounts:user_list')
    else:
        form = UserForm()
    
    return render(request, 'accounts/user_form.html', {'form': form, 'title': 'Nouvel Utilisateur'})


@login_required
def user_edit(request, pk):
    if not request.user.is_admin_user:
        messages.error(request, "Accès non autorisé.")
        return redirect('dashboard:index')
    
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = UserForm(request.POST, instance=user)
        if form.is_valid():
            user = form.save(commit=False)
            password = form.cleaned_data.get('password')
            if password:
                user.set_password(password)
            user.save()
            messages.success(request, f"Utilisateur {user.username} modifié avec succès.")
            return redirect('accounts:user_list')
    else:
        form = UserForm(instance=user)
    
    return render(request, 'accounts/user_form.html', {'form': form, 'title': 'Modifier Utilisateur'})


@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html')
