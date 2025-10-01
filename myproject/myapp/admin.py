# Register your models here.
from django.contrib import admin
from .models import Customer, MenuItem, Order, OrderItem

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("customer_id", "name", "segment")

@admin.register(MenuItem)
class MenuAdmin(admin.ModelAdmin):
    list_display = ("sku", "name", "category", "price")

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_id", "order_ts", "channel", "customer")
    inlines = [OrderItemInline]