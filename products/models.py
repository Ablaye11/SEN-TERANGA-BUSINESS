from django.db import models
from django.core.validators import MinValueValidator


class Product(models.Model):
    """Product model - represents a product type (e.g., iPhone 15 Pro Max 256GB)."""
    
    CATEGORY_CHOICES = [
        ('smartphone', 'Smartphone'),
        ('tablette', 'Tablette'),
        ('laptop', 'Laptop'),
        ('desktop', 'Ordinateur de Bureau'),
        ('montre', 'Montre Connectée'),
        ('ecouteur', 'Écouteurs / AirPods'),
        ('accessoire', 'Accessoire'),
        ('autre', 'Autre'),
    ]
    
    BRAND_CHOICES = [
        ('apple', 'Apple'),
        ('samsung', 'Samsung'),
        ('huawei', 'Huawei'),
        ('xiaomi', 'Xiaomi'),
        ('oppo', 'OPPO'),
        ('tecno', 'Tecno'),
        ('infinix', 'Infinix'),
        ('itel', 'Itel'),
        ('google', 'Google'),
        ('hp', 'HP'),
        ('dell', 'Dell'),
        ('lenovo', 'Lenovo'),
        ('asus', 'ASUS'),
        ('autre', 'Autre'),
    ]
    
    name = models.CharField(max_length=200, verbose_name="Nom du produit")
    brand = models.CharField(max_length=20, choices=BRAND_CHOICES, verbose_name="Marque")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name="Catégorie")
    description = models.TextField(blank=True, verbose_name="Description")
    purchase_price = models.DecimalField(
        max_digits=12, decimal_places=0,
        validators=[MinValueValidator(0)],
        verbose_name="Prix d'achat (FCFA)"
    )
    selling_price = models.DecimalField(
        max_digits=12, decimal_places=0,
        validators=[MinValueValidator(0)],
        verbose_name="Prix de vente (FCFA)"
    )
    alert_threshold = models.PositiveIntegerField(
        default=2,
        verbose_name="Seuil d'alerte stock"
    )
    image = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name="Image")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    
    class Meta:
        verbose_name = "Produit"
        verbose_name_plural = "Produits"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_brand_display()} {self.name}"
    
    @property
    def margin(self):
        """Calculate profit margin."""
        return self.selling_price - self.purchase_price
    
    @property
    def margin_percentage(self):
        """Calculate margin percentage."""
        if self.purchase_price > 0:
            return round((self.margin / self.purchase_price) * 100, 1)
        return 0
    
    @property
    def stock_count(self):
        """Count available units in stock."""
        return self.units.filter(status='in_stock').count()
    
    @property
    def is_low_stock(self):
        """Check if stock is below alert threshold."""
        return self.stock_count <= self.alert_threshold


class ProductUnit(models.Model):
    """Individual product unit with unique IMEI/Serial number."""
    
    CONDITION_CHOICES = [
        ('neuf', 'Neuf'),
        ('reconditionne', 'Reconditionné'),
        ('occasion', 'Occasion'),
    ]
    
    STATUS_CHOICES = [
        ('in_stock', 'En Stock'),
        ('sold', 'Vendu'),
        ('reserved', 'Réservé'),
        ('returned', 'Retourné'),
        ('defective', 'Défectueux'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='units')
    imei_serial = models.CharField(
        max_length=50, unique=True,
        verbose_name="IMEI / N° de Série"
    )
    condition = models.CharField(
        max_length=15, choices=CONDITION_CHOICES, default='neuf',
        verbose_name="État"
    )
    status = models.CharField(
        max_length=15, choices=STATUS_CHOICES, default='in_stock',
        verbose_name="Statut"
    )
    color = models.CharField(max_length=50, blank=True, verbose_name="Couleur")
    storage = models.CharField(max_length=20, blank=True, verbose_name="Stockage")
    purchase_price = models.DecimalField(
        max_digits=12, decimal_places=0, null=True, blank=True,
        verbose_name="Prix d'achat unitaire (FCFA)"
    )
    selling_price = models.DecimalField(
        max_digits=12, decimal_places=0, null=True, blank=True,
        verbose_name="Prix de vente unitaire (FCFA)"
    )
    warranty_months = models.PositiveIntegerField(
        default=6, verbose_name="Garantie (mois)"
    )
    warranty_end = models.DateField(null=True, blank=True, verbose_name="Fin de garantie")
    notes = models.TextField(blank=True, verbose_name="Notes")
    added_at = models.DateTimeField(auto_now_add=True)
    sold_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Unité Produit"
        verbose_name_plural = "Unités Produit"
        ordering = ['-added_at']
    
    def __str__(self):
        return f"{self.product.name} - {self.imei_serial}"
    
    @property
    def effective_selling_price(self):
        """Return unit-specific price or fall back to product price."""
        return self.selling_price or self.product.selling_price
    
    @property
    def effective_purchase_price(self):
        """Return unit-specific price or fall back to product price."""
        return self.purchase_price or self.product.purchase_price
