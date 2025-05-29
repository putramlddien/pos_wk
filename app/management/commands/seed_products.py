import random
from django.core.management.base import BaseCommand
from app.models import Product
from faker import Faker

class Command(BaseCommand):
    help = 'Seed the Product table with relevant warkop menu items'

    def handle(self, *args, **kwargs):
        fake = Faker()

        # Hapus semua data sebelumnya
        Product.objects.all().delete()

        # Jumlah data yang akan ditambahkan
        num_products = 50  # Ubah jumlah agar lebih realistis

        # Daftar nama makanan dan minuman khas warkop
        warkop_menu = {
            'makanan': ['Indomie Goreng', 'Indomie Kuah', 'Nasi Goreng', 'Mie Rebus', 'Roti Bakar', 'Pisang Goreng'],
            'minuman': ['Kopi Hitam', 'Es Teh Manis', 'Wedang Jahe', 'Kopi Susu', 'Cappuccino', 'Es Jeruk'],
            'snack': ['Kerupuk', 'Kacang Goreng', 'Singkong Goreng', 'Martabak Mini', 'Cilok', 'Tahu Crispy']
        }

        for _ in range(num_products):
            # Pilih kategori produk secara acak
            category = random.choice(list(warkop_menu.keys()))
            
            # Pilih nama produk dari daftar sesuai kategori
            name = random.choice(warkop_menu[category])

            # Tentukan harga berdasarkan kategori
            if category == 'makanan':
                price = random.uniform(10000, 30000)
            elif category == 'minuman':
                price = random.uniform(5000, 20000)
            else:
                price = random.uniform(3000, 15000)

            # Generate data dummy untuk setiap produk
            product = Product(
                name=name,
                description=fake.text(),
                price=round(price, 2),  # Harga dalam format dua desimal
                stock=random.randint(5, 50),  # Stok acak antara 5 hingga 50
                category=category,  # Kategori yang sudah dipilih
                image='products/default.jpg'  # Gunakan gambar default jika belum ada
            )
            product.save()

        self.stdout.write(self.style.SUCCESS(f'{num_products} products created successfully with relevant warkop menu!'))