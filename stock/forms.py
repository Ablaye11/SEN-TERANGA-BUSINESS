from django import forms
from .models import Supplier, StockEntry


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'phone', 'email', 'address', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input'}),
            'phone': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'address': forms.Textarea(attrs={'class': 'form-input', 'rows': 2}),
            'notes': forms.Textarea(attrs={'class': 'form-input', 'rows': 2}),
        }


class StockEntryForm(forms.ModelForm):
    class Meta:
        model = StockEntry
        fields = ['reference', 'supplier', 'date', 'notes', 'total_cost']
        widgets = {
            'reference': forms.TextInput(attrs={'class': 'form-input'}),
            'supplier': forms.Select(attrs={'class': 'form-input'}),
            'date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-input', 'rows': 2}),
            'total_cost': forms.NumberInput(attrs={'class': 'form-input'}),
        }
