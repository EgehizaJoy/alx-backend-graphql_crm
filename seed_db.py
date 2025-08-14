import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "graphql_crm.settings")  # or alx_backend_graphql_crm.settings
django.setup()

from crm.models import Customer, Product

def run():
    Customer.objects.get_or_create(name="Demo User", email="demo@example.com", phone="+1234567890")
    Product.objects.get_or_create(name="Laptop", price="999.99", stock=10)
    Product.objects.get_or_create(name="Mouse", price="19.99", stock=100)
    print("Seeded customers and products.")

if __name__ == "__main__":
    run()
