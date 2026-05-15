from django.db import models
from django.conf import settings


class Supplier(models.Model):
    """Supplier/Fournisseur model."""
    
    name = models.CharField(max_length=200, verbose_name="Nom du fournisseur")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Téléphone")
    email = models.EmailField(blank=True, verbose_name="Email")
    address = models.TextField(blank=True, verbose_name="Adresse")
    notes = models.TextField(blank=True, verbose_name="Notes")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Fournisseur"
        verbose_name_plural = "Fournisseurs"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class StockEntry(models.Model):
    """Stock entry - records a batch of products arriving."""
    
    reference = models.CharField(max_length=50, unique=True, verbose_name="Référence")
    supplier = models.ForeignKey(
        Supplier, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='entries', verbose_name="Fournisseur"
    )
    date = models.DateField(verbose_name="Date d'arrivage")
    notes = models.TextField(blank=True, verbose_name="Notes")
    total_cost = models.DecimalField(
        max_digits=15, decimal_places=0, default=0,
        verbose_name="Coût total (FCFA)"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        verbose_name="Créé par"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Entrée de Stock"
        verbose_name_plural = "Entrées de Stock"
        ordering = ['-date']
    
    def __str__(self):
        return f"Arrivage {self.reference} - {self.date}"


class StockMovement(models.Model):
    """Track all stock movements (in/out)."""
    
    TYPE_CHOICES = [
        ('in', 'Entrée'),
        ('out', 'Sortie'),
        ('return', 'Retour'),
        ('adjustment', 'Ajustement'),
    ]
    
    product_unit = models.ForeignKey(
        'products.ProductUnit', on_delete=models.CASCADE,
        related_name='movements', verbose_name="Unité"
    )
    movement_type = models.CharField(
        max_length=15, choices=TYPE_CHOICES,
        verbose_name="Type de mouvement"
    )
    stock_entry = models.ForeignKey(
        StockEntry, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='movements', verbose_name="Entrée de stock"
    )
    reason = models.CharField(max_length=200, blank=True, verbose_name="Motif")
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        verbose_name="Effectué par"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Mouvement de Stock"
        verbose_name_plural = "Mouvements de Stock"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.product_unit}"
