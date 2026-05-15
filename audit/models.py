from django.db import models
from django.conf import settings

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('create', 'Création'),
        ('update', 'Modification'),
        ('delete', 'Suppression'),
        ('login', 'Connexion'),
        ('sale', 'Vente'),
        ('stock', 'Stock'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=50, blank=True)
    object_id = models.CharField(max_length=50, blank=True)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Journal d'activité"
        verbose_name_plural = "Journaux d'activité"

    def __str__(self):
        user_str = self.user.username if self.user else "Système"
        return f"{user_str} - {self.action} - {self.created_at}"

def log_action(user, action, description, model_name="", object_id=""):
    AuditLog.objects.create(
        user=user,
        action=action,
        description=description,
        model_name=model_name,
        object_id=str(object_id)
    )
