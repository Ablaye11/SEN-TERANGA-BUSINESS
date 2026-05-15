from django import forms
from .models import Client


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['name', 'phone', 'email', 'address', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Nom complet'}),
            'phone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '77 123 45 67'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'email@example.com'}),
            'address': forms.Textarea(attrs={'class': 'form-input', 'rows': 2, 'placeholder': 'Adresse'}),
            'notes': forms.Textarea(attrs={'class': 'form-input', 'rows': 2}),
        }
