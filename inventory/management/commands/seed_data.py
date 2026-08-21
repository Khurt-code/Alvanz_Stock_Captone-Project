from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User
from inventory.models import Category, Product, StockTransaction
from pos.models import Sale, SaleItem, record_sale


class Command(BaseCommand):
    help = "Seed the database with demo data for Alvanz Hardware."

    def handle(self, *args, **options):
        if not User.objects.filter(username="admin").exists():
            admin = User.objects.create_superuser("admin", password="admin123", role=User.Role.MANAGER)
            admin.first_name = "Admin"
            admin.last_name = "User"
            admin.save()
            self.stdout.write("Created admin / admin123")
        if not User.objects.filter(username="cashier").exists():
            cashier = User.objects.create_user(
                "cashier", password="cashier123", role=User.Role.CASHIER, first_name="Maria", last_name="Santos"
            )
            self.stdout.write("Created cashier / cashier123")
        if not User.objects.filter(username="staff").exists():
            staff = User.objects.create_user(
                "staff", password="staff123", role=User.Role.STAFF, first_name="Juan", last_name="Dela Cruz"
            )
            self.stdout.write("Created staff / staff123")

        if Category.objects.exists():
            self.stdout.write("Demo data already present, skipping.")
            return

        categories = {
            "Cement & Binders": "Cement, plaster, and binding materials.",
            "Lumber & Plywood": "Wood and engineered timber products.",
            "Paints & Coatings": "Paint, primer, and finishing supplies.",
            "Pipes & Fittings": "PVC, GI pipes, and plumbing fittings.",
            "Tools & Hardware": "Hand tools and general hardware.",
            "Electrical": "Wires, switches, and electrical supplies.",
        }
        objs = {name: Category.objects.create(name=name, description=desc) for name, desc in categories.items()}

        products = [
            ("Portland Cement 40kg", "CEM-40KG", "Cement & Binders", "bag", 220, 260, 40, 15),
            ("Cement 50kg", "CEM-50KG", "Cement & Binders", "bag", 265, 315, 25, 10),
            ("Lumber 2x2x8", "LBR-0202", "Lumber & Plywood", "pcs", 85, 120, 60, 20),
            ("Plywood 4x8 1/2in", "PLY-4805", "Lumber & Plywood", "pcs", 780, 950, 18, 5),
            ("Latex Paint 4L", "PNT-LTX4", "Paints & Coatings", "gal", 620, 780, 12, 6),
            ("Enamel Paint 1L", "PNT-ENM1", "Paints & Coatings", "gal", 280, 380, 8, 5),
            ("PVC Pipe 4in x 3m", "PVC-0403", "Pipes & Fittings", "pcs", 165, 220, 30, 10),
            ("PVC Elbow 4in", "PVC-EB4", "Pipes & Fittings", "pcs", 45, 65, 45, 15),
            ("Ball Peen Hammer 12oz", "TL-HMR12", "Tools & Hardware", "pcs", 150, 210, 14, 6),
            ("Cutter Knife", "TL-CTRKN", "Tools & Hardware", "pcs", 35, 55, 10, 4),
            ("Duplex Wire #14 (25m)", "ELC-DPX14", "Electrical", "roll", 420, 520, 9, 5),
            ("Switch w/ Outlet", "ELC-SWO", "Electrical", "pcs", 75, 110, 20, 8),
        ]
        product_objs = {}
        for name, sku, cat, unit, cost, price, qty, min_stock in products:
            product_objs[name] = Product.objects.create(
                name=name, sku=sku, category=objs[cat], unit=unit,
                cost_price=cost, sell_price=price, quantity=0, min_stock_level=min_stock,
            )
            StockTransaction.objects.create(
                product=product_objs[name],
                transaction_type=StockTransaction.Type.STOCK_IN,
                quantity=qty,
                reference="INITIAL",
                notes="Initial stock setup",
                user=User.objects.get(username="admin"),
            )

        manager = User.objects.get(username="admin")
        cashier = User.objects.get(username="cashier")
        import random

        for i in range(12):
            day = timezone.now() - timedelta(days=i)
            if i > 0:
                for name in random.sample(list(product_objs.keys()), k=5):
                    StockTransaction.objects.create(
                        product=product_objs[name],
                        transaction_type=StockTransaction.Type.STOCK_IN,
                        quantity=random.randint(10, 40),
                        reference=f"SUP-{day.strftime('%m%d')}",
                        notes="Supplier delivery",
                        user=manager,
                    )
            cart = []
            names = random.sample(list(product_objs.keys()), k=random.randint(2, 5))
            for name in names:
                cart.append((product_objs[name], random.randint(1, 3)))
            sale = record_sale(cart, cashier, cash_tendered=10000, discount=random.choice([0, 0, 25, 50]))
            Sale.objects.filter(pk=sale.pk).update(created_at=day)
            self.stdout.write(f"Seeded sale {sale.receipt_no} on {day.date()}")

        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully."))