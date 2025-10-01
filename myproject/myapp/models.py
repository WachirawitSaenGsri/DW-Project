# models.py
from django.db import models

# Create your models here.
from django.db import models

class Customer(models.Model):
    customer_id = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255, blank=True)
    segment = models.CharField(max_length=64, blank=True)

    def __str__(self):
        return f"{self.customer_id} - {self.name}"

class MenuItem(models.Model):
    sku = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=128, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.sku} {self.name}"

class Order(models.Model):
    order_id = models.CharField(max_length=64, unique=True)
    order_ts = models.DateTimeField()
    channel = models.CharField(max_length=64, blank=True)
    customer = models.ForeignKey(Customer, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return self.order_id

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    menu_item = models.ForeignKey(MenuItem, on_delete=models.PROTECT)
    qty = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)