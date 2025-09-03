import re
from decimal import Decimal

import graphene
from graphene import Field, List
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from django.db import transaction, IntegrityError
from django.utils import timezone
from datetime import datetime
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import Customer, Product, Order
from .filters import CustomerFilter, ProductFilter, OrderFilter
from crm.models import Product"

# ------------------------
# GraphQL Types
# ------------------------
class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer
        fields = ("id", "name", "email", "phone")

class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        fields = ("id", "name", "price", "stock")

class OrderType(DjangoObjectType):
    class Meta:
        model = Order
        fields = ("id", "customer", "products", "total_amount", "order_date")


# ------------------------
# Inputs
# ------------------------
class CreateCustomerInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String(required=False)

class CreateProductInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    price = graphene.Decimal(required=True)
    stock = graphene.Int(required=False)

class CreateOrderInput(graphene.InputObjectType):
    customer_id = graphene.ID(required=True)
    product_ids = graphene.List(graphene.ID, required=True)
    order_date = graphene.DateTime(required=False)


# ------------------------
# Validators / Utilities
# ------------------------
PHONE_RE = re.compile(r"^(\+\d{7,15}|\d{3}-\d{3}-\d{4})$")

def validate_phone(phone: str) -> bool:
    if phone in (None, "",):
        return True
    return bool(PHONE_RE.match(phone))

def decimal_from(value):
    # Accept str/float/Decimal and normalize to Decimal with 2dp
    d = Decimal(str(value))
    return d.quantize(Decimal("0.01"))

# ------------------------
# Mutations
# ------------------------
class CreateCustomer(graphene.Mutation):
    class Arguments:
        input = CreateCustomerInput(required=True)

    customer = Field(CustomerType)
    message = graphene.String()
    errors = List(graphene.String)

    @staticmethod
    def mutate(root, info, input):
        errors = []

        # Email uniqueness
        if Customer.objects.filter(email__iexact=input.email).exists():
            errors.append("Email already exists")

        # Phone format
        if not validate_phone(getattr(input, "phone", None)):
            errors.append("Invalid phone format. Use +1234567890 or 123-456-7890")

        if errors:
            return CreateCustomer(customer=None, message=None, errors=errors)

        cust = Customer.objects.create(
            name=input.name.strip(),
            email=input.email.strip(),
            phone=(input.phone or "").strip() or None,
        )
        return CreateCustomer(customer=cust, message="Customer created successfully", errors=[])


class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        input = List(CreateCustomerInput, required=True)

    customers = List(CustomerType)
    errors = List(graphene.String)

    @staticmethod
    def mutate(root, info, input):
        created = []
        errors = []

        # Use a top-level transaction with per-item savepoints to allow partial success.
        with transaction.atomic():
            for idx, item in enumerate(input, start=1):
                item_errs = []

                if Customer.objects.filter(email__iexact=item.email).exists():
                    item_errs.append(f"[{idx}] Email already exists: {item.email}")

                if not validate_phone(getattr(item, "phone", None)):
                    item_errs.append(f"[{idx}] Invalid phone format: {item.phone}")

                if item_errs:
                    errors.extend(item_errs)
                    continue

                sid = transaction.savepoint()
                try:
                    cust = Customer.objects.create(
                        name=item.name.strip(),
                        email=item.email.strip(),
                        phone=(item.phone or "").strip() or None,
                    )
                    created.append(cust)
                    transaction.savepoint_commit(sid)
                except IntegrityError as e:
                    transaction.savepoint_rollback(sid)
                    errors.append(f"[{idx}] Failed to create customer: {str(e)}")

        return BulkCreateCustomers(customers=created, errors=errors)


class CreateProduct(graphene.Mutation):
    class Arguments:
        input = CreateProductInput(required=True)

    product = Field(ProductType)
    errors = List(graphene.String)

    @staticmethod
    def mutate(root, info, input):
        errs = []

        try:
            price = decimal_from(input.price)
            if price <= Decimal("0"):
                errs.append("Price must be positive")
        except Exception:
            errs.append("Invalid price format")

        stock = getattr(input, "stock", 0)
        if stock is None:
            stock = 0
        if stock < 0:
            errs.append("Stock cannot be negative")

        if errs:
            return CreateProduct(product=None, errors=errs)

        p = Product.objects.create(
            name=input.name.strip(),
            price=price,
            stock=stock,
        )
        return CreateProduct(product=p, errors=[])


class CreateOrder(graphene.Mutation):
    class Arguments:
        input = CreateOrderInput(required=True)

    order = Field(OrderType)
    errors = List(graphene.String)

    @staticmethod
    def mutate(root, info, input):
        errs = []

        # Validate customer
        try:
            customer = Customer.objects.get(pk=input.customer_id)
        except Customer.DoesNotExist:
            errs.append("Invalid customer ID")
            customer = None

        # Validate products
        product_ids = list(input.product_ids or [])
        if not product_ids:
            errs.append("At least one product must be selected")
        products = []
        if product_ids:
            existing = list(Product.objects.filter(id__in=product_ids))
            found_ids = {str(p.id) for p in existing}
            missing = [pid for pid in map(str, product_ids) if pid not in found_ids]
            if missing:
                errs.append(f"Invalid product ID(s): {', '.join(missing)}")
            products = existing

        if errs:
            return CreateOrder(order=None, errors=errs)

        with transaction.atomic():
            order_date = getattr(input, "order_date", None) or timezone.now()
            order = Order.objects.create(customer=customer, order_date=order_date)

            # Associate products
            order.products.add(*products)

            # Compute accurate total_amount from DB values
            total = sum((p.price for p in products), Decimal("0.00"))
            order.total_amount = total.quantize(Decimal("0.01"))
            order.save(update_fields=["total_amount"])

        return CreateOrder(order=order, errors=[])


# ------------------------
# Public Mutation & Query
# ------------------------
class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()

# Keep your earlier hello field so queries still pass checkpoints
class Query(graphene.ObjectType):
    hello = graphene.String(default_value="Hello, GraphQL!")
class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer
class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer

class ProductType(DjangoObjectType):
    class Meta:
        model = Product

class OrderType(DjangoObjectType):
    class Meta:
        model = Order
class CustomerInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String()

class ProductInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    price = graphene.Float(required=True)
    stock = graphene.Int(default_value=0)

class OrderInput(graphene.InputObjectType):
    customer_id = graphene.ID(required=True)
    product_ids = graphene.List(graphene.ID, required=True)
    order_date = graphene.DateTime()
class CreateCustomer(graphene.Mutation):
    class Arguments:
        input = CustomerInput(required=True)

    customer = graphene.Field(CustomerType)
    message = graphene.String()

    def mutate(self, info, input):
        if Customer.objects.filter(email=input.email).exists():
            raise Exception("Email already exists")

        if input.phone and not re.match(r'^(\+\d{10,15}|\d{3}-\d{3}-\d{4})$', input.phone):
            raise Exception("Invalid phone format")

        customer = Customer.objects.create(
            name=input.name,
            email=input.email,
            phone=input.phone
        )
        return CreateCustomer(customer=customer, message="Customer created successfully")
class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        input = graphene.List(CustomerInput, required=True)

    customers = graphene.List(CustomerType)
    errors = graphene.List(graphene.String)

    @transaction.atomic
    def mutate(self, info, input):
        customers = []
        errors = []

        for data in input:
            try:
                if Customer.objects.filter(email=data.email).exists():
                    raise Exception(f"Email already exists: {data.email}")
                if data.phone and not re.match(r'^(\+\d{10,15}|\d{3}-\d{3}-\d{4})$', data.phone):
                    raise Exception(f"Invalid phone format: {data.phone}")

                customers.append(Customer(
                    name=data.name,
                    email=data.email,
                    phone=data.phone
                ))
            except Exception as e:
                errors.append(str(e))

        created_customers = Customer.objects.bulk_create(customers)
        return BulkCreateCustomers(customers=created_customers, errors=errors)
class CreateProduct(graphene.Mutation):
    class Arguments:
        input = ProductInput(required=True)

    product = graphene.Field(ProductType)

    def mutate(self, info, input):
        if input.price <= 0:
            raise Exception("Price must be positive")
        if input.stock < 0:
            raise Exception("Stock must be non-negative")

        product = Product.objects.create(
            name=input.name,
            price=Decimal(input.price),
            stock=input.stock
        )
        return CreateProduct(product=product)
class CreateOrder(graphene.Mutation):
    class Arguments:
        input = OrderInput(required=True)

    order = graphene.Field(OrderType)

    def mutate(self, info, input):
        try:
            customer = Customer.objects.get(pk=input.customer_id)
        except Customer.DoesNotExist:
            raise Exception("Customer not found")

        products = Product.objects.filter(pk__in=input.product_ids)
        if not products.exists():
            raise Exception("No valid products found")

        total_amount = sum([p.price for p in products])

        order = Order.objects.create(
            customer=customer,
            total_amount=total_amount,
            order_date=input.order_date or datetime.now()
        )
        order.products.set(products)

        return CreateOrder(order=order)

class UpdateLowStockProducts(graphene.Mutation):
    class Arguments:
        pass  # no input needed

    success = graphene.Boolean()
    message = graphene.String()
    products = graphene.List(ProductType)

    def mutate(self, info):
        low_stock_products = Product.objects.filter(stock__lt=10)
        updated_products = []

        for product in low_stock_products:
            product.stock += 10
            product.save()
            updated_products.append(product)

        return UpdateLowStockProducts(
            success=True,
            message="Low stock products restocked successfully.",
            products=updated_products,
        )

class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()

