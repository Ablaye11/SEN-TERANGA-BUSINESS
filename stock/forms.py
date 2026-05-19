from django import forms
from .models import Supplier, StockEntry, StockMovement
from products.models import ProductUnit


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


class StockAdjustmentForm(forms.ModelForm):
    """Form to adjust an individual product unit's status/condition."""
    reason = forms.CharField(
        required=False,
        max_length=200,
        label="Motif de l'ajustement",
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ex: Retour client, défaut constaté...'})
    )

    class Meta:
        model = ProductUnit
        fields = ['status', 'condition', 'purchase_price', 'selling_price', 'warranty_months', 'notes']
        widgets = {
            'status':         forms.Select(attrs={'class': 'form-input'}),
            'condition':      forms.Select(attrs={'class': 'form-input'}),
            'purchase_price': forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
            'selling_price':  forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
            'warranty_months':forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
            'notes':          forms.Textarea(attrs={'class': 'form-input', 'rows': 2}),
        }
        labels = {
            'status':         'Nouveau statut',
            'condition':      'État',
            'purchase_price': "Prix d'achat unitaire (FCFA)",
            'selling_price':  "Prix de vente unitaire (FCFA)",
            'warranty_months':'Garantie (mois)',
            'notes':          'Notes',
        }
