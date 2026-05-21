import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class Sale(models.Model):
    """Sale/Invoice model."""
    
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Espèces'),
        ('wave', 'Wave'),
        ('orange_money', 'Orange Money'),
        ('virement', 'Virement Bancaire'),
        ('cheque', 'Chèque'),
        ('echange', 'Échange / Reprise'),
        ('mixte', 'Paiement Mixte'),
    ]
    
    STATUS_CHOICES = [
        ('completed', 'Terminée'),
        ('partial', 'Partiellement Payée'),
        ('pending', 'En Attente'),
        ('cancelled', 'Annulée'),
    ]
    
    invoice_number = models.CharField(
        max_length=20, unique=True, verbose_name="N° Facture"
    )
    client = models.ForeignKey(
        'clients.Client', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='sales',
        verbose_name="Client"
    )
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='sales', verbose_name="Vendeur"
    )
    date = models.DateTimeField(default=timezone.now, verbose_name="Date")
    subtotal = models.DecimalField(
        max_digits=15, decimal_places=0, default=0,
        verbose_name="Sous-total (FCFA)"
    )
    discount = models.DecimalField(
        max_digits=12, decimal_places=0, default=0,
        verbose_name="Remise (FCFA)"
    )
    total_amount = models.DecimalField(
        max_digits=15, decimal_places=0, default=0,
        verbose_name="Total (FCFA)"
    )
    payment_method = models.CharField(
        max_length=15, choices=PAYMENT_METHOD_CHOICES,
        default='cash', verbose_name="Mode de paiement"
    )
    status = models.CharField(
        max_length=15, choices=STATUS_CHOICES,
        default='completed', verbose_name="Statut"
    )
    notes = models.TextField(blank=True, verbose_name="Notes")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Vente"
        verbose_name_plural = "Ventes"
        ordering = ['-date']
    
    def __str__(self):
        return f"Facture {self.invoice_number}"
    
    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = self.generate_invoice_number()
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_invoice_number():
        """Generate unique invoice number: STB-YYYYMMDD-XXXX"""
        today = timezone.now()
        prefix = f"STB-{today.strftime('%Y%m%d')}"
        last_sale = Sale.objects.filter(
            invoice_number__startswith=prefix
        ).order_by('-invoice_number').first()
        
        if last_sale:
            last_num = int(last_sale.invoice_number.split('-')[-1])
            new_num = last_num + 1
        else:
            new_num = 1
        
        return f"{prefix}-{new_num:04d}"
    
    @property
    def amount_paid(self):
        return self.payments.aggregate(
            total=models.Sum('amount')
        )['total'] or 0
    
    @property
    def amount_remaining(self):
        return self.total_amount - self.amount_paid
    
    @property
    def total_cost(self):
        """Total purchase cost for margin calculation."""
        total = 0
        for item in self.items.all():
            if item.product_unit:
                total += item.product_unit.effective_purchase_price
            else:
                total += item.unit_price  # fallback
        return total
    
    @property
    def profit(self):
        return self.total_amount - self.total_cost


class SaleItem(models.Model):
    """Individual item in a sale."""
    
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(
        'products.Product', on_delete=models.SET_NULL, null=True,
        verbose_name="Produit"
    )
    product_unit = models.ForeignKey(
        'products.ProductUnit', on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Unité (IMEI/Série)"
    )
    unit_price = models.DecimalField(
        max_digits=12, decimal_places=0,
        verbose_name="Prix unitaire (FCFA)"
    )
    quantity = models.PositiveIntegerField(default=1, verbose_name="Quantité")
    warranty_months = models.PositiveIntegerField(
        default=6, verbose_name="Garantie (mois)"
    )
    
    class Meta:
        verbose_name = "Article de Vente"
        verbose_name_plural = "Articles de Vente"
    
    def __str__(self):
        return f"{self.product} x{self.quantity}"
    
    @property
    def line_total(self):
        return self.unit_price * self.quantity
    
    @property
    def warranty_end_date(self):
        """Calculate warranty end date from sale date."""
        if self.sale and self.sale.date:
            return self.sale.date + timedelta(days=self.warranty_months * 30)
        return None


class Payment(models.Model):
    """Payment records for a sale (supports partial payments)."""
    
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Espèces'),
        ('wave', 'Wave'),
        ('orange_money', 'Orange Money'),
        ('virement', 'Virement Bancaire'),
        ('cheque', 'Chèque'),
        ('echange', 'Échange / Reprise'),
    ]
    
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(
        max_digits=12, decimal_places=0,
        verbose_name="Montant (FCFA)"
    )
    payment_method = models.CharField(
        max_length=15, choices=PAYMENT_METHOD_CHOICES,
        default='cash', verbose_name="Mode de paiement"
    )
    reference = models.CharField(
        max_length=100, blank=True,
        verbose_name="Référence (N° transaction)"
    )
    date = models.DateTimeField(default=timezone.now, verbose_name="Date")
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        verbose_name="Reçu par"
    )
    
    class Meta:
        verbose_name = "Paiement"
        verbose_name_plural = "Paiements"
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.amount} FCFA - {self.get_payment_method_display()}"


class Expense(models.Model):
    """Expense/Charges model."""
    
    CATEGORY_CHOICES = [
        ('rent', 'Loyer'),
        ('transport', 'Transport'),
        ('salary', 'Salaire'),
        ('bills', 'Factures (Électricité, Internet, etc.)'),
        ('other', 'Autre charge'),
    ]
    
    amount = models.DecimalField(
        max_digits=12, decimal_places=0,
        verbose_name="Montant (FCFA)"
    )
    category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES,
        default='other', verbose_name="Catégorie"
    )
    description = models.TextField(blank=True, verbose_name="Description")
    date = models.DateTimeField(default=timezone.now, verbose_name="Date")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Enregistré par"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Dépense"
        verbose_name_plural = "Dépenses"
        ordering = ['-date']
        
    def __str__(self):
        return f"{self.amount} FCFA - {self.get_category_display()}"


class CashRegisterSession(models.Model):
    """Session of cash register opening/closure."""
    
    STATUS_CHOICES = [
        ('open', 'Ouverte'),
        ('closed', 'Fermée'),
    ]
    
    opened_at = models.DateTimeField(default=timezone.now, verbose_name="Date d'ouverture")
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name="Date de fermeture")
    opened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='opened_sessions', verbose_name="Ouvert par"
    )
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='closed_sessions', verbose_name="Fermé par"
    )
    initial_cash = models.DecimalField(
        max_digits=12, decimal_places=0, default=0,
        verbose_name="Fond de caisse initial (FCFA)"
    )
    cash_sales = models.DecimalField(
        max_digits=12, decimal_places=0, default=0,
        verbose_name="Ventes en espèces (FCFA)"
    )
    expenses_paid = models.DecimalField(
        max_digits=12, decimal_places=0, default=0,
        verbose_name="Dépenses en espèces (FCFA)"
    )
    expected_cash = models.DecimalField(
        max_digits=12, decimal_places=0, default=0,
        verbose_name="Espèces attendues (FCFA)"
    )
    actual_cash = models.DecimalField(
        max_digits=12, decimal_places=0, null=True, blank=True,
        verbose_name="Espèces réelles déclarées (FCFA)"
    )
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES,
        default='open', verbose_name="Statut"
    )
    notes = models.TextField(blank=True, verbose_name="Notes / Remarques")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Session de Caisse"
        verbose_name_plural = "Sessions de Caisse"
        ordering = ['-opened_at']
        
    def __str__(self):
        status_disp = "Ouverte" if self.status == 'open' else f"Fermée le {self.closed_at.strftime('%d/%m/%Y') if self.closed_at else ''}"
        return f"Caisse du {self.opened_at.strftime('%d/%m/%Y')} ({status_disp})"
        
    @property
    def discrepancy(self):
        if self.actual_cash is not None:
            return self.actual_cash - self.expected_cash
        return 0
