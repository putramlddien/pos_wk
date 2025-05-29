from django.core.management.base import BaseCommand
from app.models import Table
import qrcode
import os
from django.conf import settings

class Command(BaseCommand):
    help = 'Generate QR code for each table'

    def handle(self, *args, **kwargs):
        qr_dir = os.path.join(settings.MEDIA_ROOT, 'qr_codes')
        os.makedirs(qr_dir, exist_ok=True)
        for table in Table.objects.all():
            url = f'https://pos-wk/order/meja-{table.table_number}/'
            img = qrcode.make(url)
            img_path = os.path.join(qr_dir, f'meja-{table.table_number}.png')
            img.save(img_path)
            table.qr_code = f'qr_codes/meja-{table.table_number}.png'
            table.save()
        self.stdout.write(self.style.SUCCESS('QR codes generated for all tables.'))
