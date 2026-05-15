import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from products.models import Product, ProductUnit
from clients.models import Client
from sales.models import Sale, SaleItem, Payment
from sav.models import Repair
from audit.models import AuditLog
from stock.models import StockMovement, Supplier, StockEntry

def clear_all():
    print("--- ATTENTION : NETTOYAGE TOTAL EN COURS ---")
    
    # 1. Sales & Payments
    Payment.objects.all().delete()
    SaleItem.objects.all().delete()
    Sale.objects.all().delete()
    print("✓ Ventes et paiements supprimés.")

    # 2. SAV
    Repair.objects.all().delete()
    print("✓ Réparations SAV supprimées.")

    # 3. Stock Movements & Units
    StockMovement.objects.all().delete()
    ProductUnit.objects.all().delete()
    StockEntry.objects.all().delete()
    Supplier.objects.all().delete()
    print("✓ Mouvements de stock et unités supprimés.")

    # 4. Clients
    Client.objects.all().delete()
    print("✓ Clients supprimés.")

    # 5. Products Catalog
    Product.objects.all().delete()
    print("✓ Catalogue produits vidé.")

    # 6. Audit Logs
    AuditLog.objects.all().delete()
    print("✓ Journal d'activité nettoyé.")

    print("\n--- SYSTÈME PRÊT POUR LA PRODUCTION ---")

if __name__ == "__main__":
    confirm = input("Voulez-vous vraiment TOUT supprimer ? (oui/non) : ")
    if confirm.lower() == 'oui':
        clear_all()
    else:
        print("Opération annulée.")
