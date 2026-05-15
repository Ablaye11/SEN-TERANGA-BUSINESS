from django.db import models
from django.conf import settings

class Repair(models.Model):
    STATUS_CHOICES = [
        ('pending', 'En Attente'),
        ('diagnostic', 'Diagnostic en cours'),
        ('repairing', 'Réparation en cours'),
        ('ready', 'Prêt / Terminé'),
        ('delivered', 'Livré au client'),
        ('cancelled', 'Annulé'),
    ]

    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE, related_name='repairs', verbose_name="Client")
    device_name = models.CharField(max_length=200, verbose_name="Appareil (ex: iPhone 13)")
    imei_serial = models.CharField(max_length=100, blank=True, verbose_name="IMEI / N° de Série")
    problem_description = models.TextField(verbose_name="Problème signalé")
    technician_notes = models.TextField(blank=True, verbose_name="Notes du technicien")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Statut")
    
    estimated_cost = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name="Coût estimé (FCFA)")
    actual_cost = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name="Coût réel (FCFA)")
    
    technician = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Technicien")
    
    created_at = models.DateTimeField(auto_now_add=True)
    expected_delivery = models.DateField(null=True, blank=True, verbose_name="Date de livraison prévue")
    delivered_at = models.DateTimeField(null=True, blank=True, verbose_name="Date de livraison réelle")

    class Meta:
        verbose_name = "Réparation"
        verbose_name_plural = "Réparations"
        ordering = ['-created_at']

    def __str__(self):
        return f"Réparation {self.id} - {self.device_name} ({self.client.name})"
