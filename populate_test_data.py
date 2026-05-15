import os
import django
import random
from datetime import timedelta
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from products.models import Product, ProductUnit
from clients.models import Client
from sales.models import Sale, SaleItem, Payment
from sav.models import Repair
from accounts.models import User

def populate():
    print("Démarrage de l'injection de données COHÉRENTES...")
    
    # 1. Admin
    admin = User.objects.filter(role='admin').first()
    if not admin:
        admin = User.objects.create_superuser('admin', 'admin@example.com', 'admin123')

    # 2. Products & Units
    p1, _ = Product.objects.get_or_create(name='iPhone 15 Pro Max', brand='apple', category='smartphone', defaults={'purchase_price': 850000, 'selling_price': 950000})
    p2, _ = Product.objects.get_or_create(name='Galaxy S24 Ultra', brand='samsung', category='smartphone', defaults={'purchase_price': 700000, 'selling_price': 820000})
    
    # Ensure some units are in stock
    for i in range(20):
        ProductUnit.objects.get_or_create(
            imei_serial=f'SN-TEST-{i:03d}', 
            defaults={'product': random.choice([p1, p2]), 'condition': 'neuf', 'color': 'Default', 'status': 'in_stock'}
        )

    # 3. Clients
    clients = [
        Client.objects.get_or_create(name='Modou Fall', phone='771002030')[0],
        Client.objects.get_or_create(name='Fatou Diop', phone='785006070')[0],
        Client.objects.get_or_create(name='Ibou Ndiaye', phone='701112233')[0]
    ]

    # 4. Create Coherent Sales
    units = list(ProductUnit.objects.filter(status='in_stock'))
    for i in range(15):
        if not units: break
        
        unit = units.pop()
        client = random.choice(clients + [None])
        day = timezone.now() - timedelta(days=random.randint(0, 90))
        
        # Create Sale
        sale = Sale.objects.create(
            invoice_number=Sale.generate_invoice_number(),
            client=client,
            seller=admin,
            date=day,
            subtotal=unit.product.selling_price,
            discount=random.randint(0, 20000),
            total_amount=0, # Will update
            payment_method='cash',
            status='completed'
        )
        sale.total_amount = sale.subtotal - sale.discount
        sale.save()

        # Create Sale Item
        SaleItem.objects.create(
            sale=sale,
            product=unit.product,
            product_unit=unit,
            unit_price=unit.product.selling_price,
            quantity=1
        )
        
        # Mark unit as sold
        unit.status = 'sold'
        unit.sold_at = day
        unit.save()

        # Create Payment (Full or Partial)
        is_partial = random.random() < 0.2
        if is_partial:
            paid = sale.total_amount - random.randint(50000, 150000)
            sale.status = 'partial'
        else:
            paid = sale.total_amount
            sale.status = 'completed'
        
        sale.save()
        Payment.objects.create(
            sale=sale,
            amount=paid,
            payment_method='cash',
            date=day,
            received_by=admin
        )

    print("Données cohérentes injectées. Dashboard à jour !")

if __name__ == "__main__":
    populate()
