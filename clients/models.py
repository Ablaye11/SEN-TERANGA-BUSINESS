from django.db import models
from django.conf import settings


class Client(models.Model):
    """Client model with credit tracking."""
    
    name = models.CharField(max_length=200, verbose_name="Nom complet")
    phone = models.CharField(max_length=20, verbose_name="Téléphone")
    email = models.EmailField(blank=True, verbose_name="Email")
    address = models.TextField(blank=True, verbose_name="Adresse")
    notes = models.TextField(blank=True, verbose_name="Notes")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Client"
        verbose_name_plural = "Clients"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} - {self.phone}"
    
    @property
    def total_purchases(self):
        """Total amount of all purchases."""
        return self.sales.exclude(status='cancelled').aggregate(
            total=models.Sum('total_amount')
        )['total'] or 0
    
    @property
    def total_paid(self):
        """Total amount paid across all sales."""
        from sales.models import Payment
        return Payment.objects.filter(
            sale__client=self
        ).exclude(sale__status='cancelled').aggregate(total=models.Sum('amount'))['total'] or 0
    
    @property
    def credit_balance(self):
        """Outstanding credit balance."""
        return self.total_purchases - self.total_paid
    
    @property
    def purchase_count(self):
        return self.sales.exclude(status='cancelled').count()
    @property
    def is_vip(self):
        """Returns True if client has more than 5 purchases."""
        return self.purchase_count >= 5
