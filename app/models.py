from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import uuid

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('kasir', 'Kasir'),
        ('customer', 'Customer'),
    ]
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='customer')

    # Menambahkan related_name untuk menghindari konflik
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='customuser_set',  # Ubah nama relasi
        blank=True
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='customuser_permissions_set',  # Ubah nama relasi
        blank=True
    )

    def __str__(self):
        return self.username

class Product(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    category = models.CharField(max_length=50)  # Misal: Makanan, Minuman, dll.
    stock = models.PositiveIntegerField(default=0)  # Jumlah stok yang tersedia

    def __str__(self):
        return self.name

class Cart(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)  # Pengguna yang membuat keranjang
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

class Table(models.Model):
    table_number = models.CharField(max_length=10, unique=True)  # Nomor meja
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)  # QR code untuk meja

    def __str__(self):
        return f"Table {self.table_number}"


class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]

    ORDER_SOURCE_CHOICES = [
        ('manual', 'Kasir Manual'),
        ('qr_scan', 'Customer QR Scan'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('midtrans_qris', 'Midtrans QRIS'),
        ('midtrans_va', 'Midtrans Virtual Account'),
        ('midtrans_ewallet', 'Midtrans E-Wallet'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)  # Bisa null jika kasir manual
    kasir = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='kasir_orders')  # Untuk tracking siapa kasirnya
    table = models.ForeignKey(Table, on_delete=models.SET_NULL, null=True, blank=True)  # Bisa kosong jika order tanpa meja
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Processing')
    payment_status = models.CharField(max_length=50, choices=[('Pending', 'Pending'), ('Paid', 'Paid'), ('Cancelled', 'Cancelled')], default='Pending')
    source = models.CharField(max_length=10, choices=ORDER_SOURCE_CHOICES, default='manual')  # Tracking asal order
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='cash')
    notes = models.TextField(blank=True, null=True)  # Catatan khusus untuk order
    phone_number = models.CharField(max_length=15, blank=True, null=True)  # Untuk customer yang pesan via WhatsApp
    customer_name = models.CharField(max_length=100, blank=True, null=True)  # Nama pelanggan dari sesi WhatsApp
    date_ordered = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.source == "qr_scan":
            return f"Order #{self.id} by Customer ({self.phone_number})"
        elif self.user:
            return f"Order #{self.id} by {self.user.username}"
        else:
            return f"Order #{self.id} by Kasir"
class OrderDetail(models.Model):
    order = models.ForeignKey(Order, related_name='order_details', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"


class Payment(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE)
    payment_method = models.CharField(max_length=50)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_status = models.CharField(max_length=50, default='Pending')

    def __str__(self):
        return f"Payment for Order #{self.order.id}"


class SalesReport(models.Model):
    date = models.DateField(auto_now_add=True)
    total_sales = models.DecimalField(max_digits=10, decimal_places=2)
    total_orders = models.PositiveIntegerField()

    def __str__(self):
        return f"Sales Report for {self.date}"


class CustomerOTPSession(models.Model):
    phone_number = models.CharField(max_length=20)
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_verified = models.BooleanField(default=False)
    session_token = models.CharField(max_length=64, default=uuid.uuid4, unique=True)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"{self.phone_number} - {self.otp_code} ({'verified' if self.is_verified else 'pending'})"