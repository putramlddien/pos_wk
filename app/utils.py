# app/utils.py
import requests
from django.conf import settings

def create_midtrans_snap_token(order, customer_info, item_details):
    """
    Membuat Snap Token Midtrans untuk order tertentu.
    order: instance Order
    customer_info: dict {'name': ..., 'email': ...}
    item_details: list of dict [{'id':..., 'price':..., ...}]
    Return: snap_token (str), error (None kalau sukses)
    """
    # Server Key dari settings
    server_key = getattr(settings, 'MIDTRANS_SERVER_KEY', 'YOUR_DEFAULT_KEY')
    url = 'https://app.sandbox.midtrans.com/snap/v1/transactions'
    
    payload = {
        "transaction_details": {
            "order_id": str(order.id),
            "gross_amount": int(order.total)
        },
        "customer_details": customer_info,
        "item_details": item_details,
        "enabled_payments": ["gopay", "bank_transfer", "qris", "shopeepay", "bca_klikbca"],
    }
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            auth=(server_key, '')
        )
        response.raise_for_status()
        snap_token = response.json().get("token")
        return snap_token, None
    except Exception as e:
        return None, str(e)
