from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user model with role support."""
    
    ROLE_CHOICES = [
        ('admin', 'Administrateur'),
        ('vendeur', 'Vendeur'),
    ]
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='vendeur')
    phone = models.CharField(max_length=20, blank=True, verbose_name="Téléphone")
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    
    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
    
    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"
    
    @property
    def is_admin_user(self):
        return self.role == 'admin' or self.is_superuser
    
    @property
    def is_vendeur(self):
        return self.role == 'vendeur'
