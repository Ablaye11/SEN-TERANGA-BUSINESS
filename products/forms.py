from django import forms
from .models import Product, ProductUnit


class ProductForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and not user.is_admin_user:
            if 'purchase_price' in self.fields:
                self.fields['purchase_price'].widget = forms.HiddenInput()
                self.fields['purchase_price'].required = False

    class Meta:
        model = Product
        fields = ['name', 'brand', 'category', 'description', 'purchase_price', 
                  'selling_price', 'alert_threshold', 'image', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ex: iPhone 15 Pro Max'}),
            'brand': forms.Select(attrs={'class': 'form-input'}),
            'category': forms.Select(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'purchase_price': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': '0'}),
            'selling_price': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': '0'}),
            'alert_threshold': forms.NumberInput(attrs={'class': 'form-input', 'min': 0}),
            'image': forms.FileInput(attrs={'class': 'form-input'}),
        }


class ProductUnitForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # warranty_months has a model default of 6, make it optional in form
        self.fields['warranty_months'].required = False
        self.fields['warranty_months'].initial = 6
        if user and not user.is_admin_user:
            if 'purchase_price' in self.fields:
                self.fields['purchase_price'].widget = forms.HiddenInput()
                self.fields['purchase_price'].required = False

    class Meta:
        model = ProductUnit
        fields = ['product', 'imei_serial', 'condition', 'color', 'storage',
                  'purchase_price', 'selling_price', 'warranty_months', 'notes']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-input'}),
            'imei_serial': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ex: 353456789012345'}),
            'condition': forms.Select(attrs={'class': 'form-input'}),
            'color': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ex: Noir Titane'}),
            'storage': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ex: 256 Go'}),
            'purchase_price': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Laisser vide = prix produit'}),
            'selling_price': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Laisser vide = prix produit'}),
            'warranty_months': forms.NumberInput(attrs={'class': 'form-input', 'min': 0}),
            'notes': forms.Textarea(attrs={'class': 'form-input', 'rows': 2}),
        }
