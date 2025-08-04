from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from .models import Product, Order, OrderDetail, Payment
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import CustomLoginForm
from django.contrib.auth.decorators import login_required
from .decorators import role_required 
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, FileResponse
import json
from django.db.models import Sum, Count, F
from django.utils import timezone
from datetime import datetime, timedelta
import requests
import logging
from .models import Table, CustomerOTPSession
from django.views.decorators.http import require_POST
from django.conf import settings
import os
import random
from django.views.decorators.http import require_GET

def kasir_owner_login(request):
    if request.method == 'POST':
        form = CustomLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None and user.is_active:
                if hasattr(user, 'role') and user.role in ['kasir', 'owner']:
                    login(request, user)
                    return redirect('kasir_dashboard')  # Redirect ke dashboard kasir atau owner
                else:
                    messages.error(request, "You do not have the required permissions.")
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Form is not valid.")
    else:
        form = CustomLoginForm()

    return render(request, 'kasir_owner_login.html', {'form': form})

@login_required
@role_required(allowed_roles=['kasir', 'owner'])
def dashboard(request):
    if request.user.role == 'owner':
        return render(request, 'dashboard.html')
    elif request.user.role == 'kasir':
        return render(request, 'dashboard.html')
    else:
        return redirect('home')

@login_required
@role_required(allowed_roles=['kasir', 'owner'])
def product_list(request):
    products = Product.objects.all()

    paginator = Paginator(products, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    page_range = list(page_obj.paginator.page_range)
    start_index = max(page_obj.number - 1, 0)
    end_index = min(page_obj.number + 1, len(page_range) - 1)

    page_range = page_range[start_index:end_index + 1]
    
    return render(request, 'product.html', {'products': page_obj, 'page_range': page_range})

@login_required
@role_required(allowed_roles=['kasir', 'owner'])
def add_product(request):
    if request.method == 'POST':
        name = request.POST['name']
        price = request.POST['price']
        stock = request.POST['stock']
        category = request.POST['category']
        description = request.POST['description']
        image = request.FILES.get('image', None)  # Ambil file gambar yang di-upload

        product = Product.objects.create(
            name=name,
            price=price,
            stock=stock,
            category=category,
            description=description,
            image=image  # Menyimpan gambar jika ada
        )
        return redirect('product_list')  # Redirect ke halaman daftar produk setelah menyimpan
    return render(request, 'product_add.html')  # Tampilkan form jika bukan POST

@login_required
@role_required(allowed_roles=['kasir', 'owner'])
def edit_product(request, product_id):
    product = Product.objects.get(id=product_id)

    if request.method == 'POST':
        product.name = request.POST.get('name')
        product.price = request.POST.get('price')
        product.stock = request.POST.get('stock')
        product.description = request.POST.get('description')
        product.save()
        return redirect('product_list')  # Redirect ke halaman produk setelah mengedit

    return render(request, 'product.html', {'product': product})

@login_required
@role_required(allowed_roles=['kasir', 'owner'])
def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.delete()
    return redirect('product_list')  # Kembali ke halaman produk setelah menghapus

@login_required
@role_required(allowed_roles=['kasir', 'owner'])
def order_menu(request):
    # Ambil semua produk dan kategori unik
    products = Product.objects.all()
    categories = Product.objects.values_list('category', flat=True).distinct()
    from .models import Table
    tables = Table.objects.all()

    # Filter kategori
    selected_category = request.GET.get('category', 'all')
    if selected_category != 'all':
        products = products.filter(category=selected_category)

    # Search produk
    search_query = request.GET.get('search', '').strip()
    if search_query:
        products = products.filter(name__icontains=search_query)

    # Pagination (9 per page)
    paginator = Paginator(products, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    page_range = list(page_obj.paginator.page_range)
    start_index = max(page_obj.number - 1, 0)
    end_index = min(page_obj.number + 1, len(page_range) - 1)
    page_range = page_range[start_index:end_index + 1]

    return render(request, 'order.html', {
        'products': page_obj,
        'categories': categories,
        'tables': tables,
        'selected_category': selected_category,
        'search_query': search_query,
        'page_range': page_range,
    })

@csrf_exempt
@login_required
@role_required(allowed_roles=['kasir', 'owner'])
def create_order(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        cart = data.get('cart', [])
        customer_name = data.get('customer_name', '')
        table_id = data.get('table_id')
        # Pastikan cart tidak kosong
        if not cart:
            return JsonResponse({'success': False, 'error': 'Cart is empty'}, status=400)
        total = 0
        for item in cart:
            product = Product.objects.filter(id=item['id']).first()
            if not product:
                return JsonResponse({'success': False, 'error': f"Product with ID {item['id']} not found"}, status=400)
            total += float(item['price']) * int(item['qty'])
        table_obj = None
        if table_id:
            from .models import Table
            try:
                table_obj = Table.objects.get(id=table_id)
            except Table.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Table not found'}, status=400)
        order = Order.objects.create(
            user=request.user,
            kasir=request.user,
            total_price=total,
            status='Processing',
            table=table_obj,
            customer_name=customer_name,
            source='manual',
            payment_status='Pending',  # Ganti dari 'Unpaid' ke 'Pending'
        )
        for item in cart:
            product = Product.objects.get(id=item['id'])
            OrderDetail.objects.create(
                order=order,
                product=product,
                quantity=int(item['qty']),
                price=float(item['price']),
            )
            product.stock = max(0, product.stock - int(item['qty']))
            product.save()
        return JsonResponse({'success': True, 'order_id': order.id, 'redirect_url': f'/checkout/{order.id}/'})
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

@login_required
@role_required(allowed_roles=['kasir', 'owner'])
def order_list(request):
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('order_id'):
        order_id = request.GET.get('order_id')
        try:
            order = Order.objects.select_related('table', 'kasir').prefetch_related('order_details__product').get(id=order_id)
            items = [
                {
                    'product_name': od.product.name,
                    'quantity': od.quantity,
                    'price': float(od.price)
                } for od in order.order_details.all()
            ]
            # Cek apakah order by kasir atau by customer
            by_kasir = True if order.kasir else False
            # Pastikan payment status
            is_paid = order.payment_status.lower() == 'paid'
            return JsonResponse({
                'order': {
                    'id': order.id,
                    'customer_name': order.customer_name or '-',
                    'table': order.table.table_number if order.table else 'Takeaway',
                    'total_price': float(order.total_price),
                    'payment_method': order.payment_status if order.payment_status else '-',
                    'kasir': order.kasir.username if order.kasir else '-',
                    'items': items,
                    'by_kasir': by_kasir,
                    'is_paid': is_paid
                }
            })
        except Order.DoesNotExist:
            return JsonResponse({'error': 'Order not found'}, status=404)
    orders = Order.objects.filter(status='Processing').select_related('table', 'kasir').prefetch_related('order_details__product')
    return render(request, 'order_list.html', {'orders': orders})


@csrf_exempt
@login_required
@role_required(allowed_roles=['kasir', 'owner'])
def complete_order(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        order_id = data.get('order_id')
        try:
            order = Order.objects.get(id=order_id)
            order.status = 'Completed'
            order.kasir = request.user
            order.save()
            return JsonResponse({'success': True})
        except Order.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Order not found'})
    return JsonResponse({'success': False, 'error': 'Invalid request'})

@login_required
@role_required(allowed_roles=['kasir', 'owner'])
def kasir_dashboard(request):
    today = timezone.now().date()
    month = today.month
    year = today.year
    # Pendapatan per hari (7 hari terakhir)
    days = [(today - timedelta(days=i)) for i in range(6, -1, -1)]
    daily_income = []
    for d in days:
        total = Order.objects.filter(status='Completed', date_ordered__date=d).aggregate(total=Sum('total_price'))['total'] or 0
        daily_income.append({'date': d.strftime('%d-%m'), 'total': float(total)})
    # Pendapatan per bulan (12 bulan terakhir)
    monthly_income = []
    for m in range(1, 13):
        total = Order.objects.filter(status='Completed', date_ordered__year=year, date_ordered__month=m).aggregate(total=Sum('total_price'))['total'] or 0
        monthly_income.append({'month': m, 'total': float(total)})
    # Pendapatan per tahun (5 tahun terakhir)
    years = [year - i for i in range(4, -1, -1)]
    yearly_income = []
    for y in years:
        total = Order.objects.filter(status='Completed', date_ordered__year=y).aggregate(total=Sum('total_price'))['total'] or 0
        yearly_income.append({'year': y, 'total': float(total)})
    # Transaksi per metode pembayaran
    cash = Order.objects.filter(status='Completed', payment_status='Paid').count()
    midtrans = Payment.objects.filter(order__status='Completed', payment_method='Midtrans', payment_status='Paid').count()
    # Ranking produk terlaris
    product_ranking = OrderDetail.objects.filter(order__status='Completed').values('product__name').annotate(total=Sum('quantity')).order_by('-total')[:10]
    context = {
        'daily_income': daily_income,
        'monthly_income': monthly_income,
        'yearly_income': yearly_income,
        'cash_count': cash,
        'midtrans_count': midtrans,
        'product_ranking': product_ranking,
    }
    return render(request, 'kasir_dashboard.html', context)

@login_required
@role_required(allowed_roles=['kasir', 'owner'])
def kasir_order_report(request):
    # Filter
    status = request.GET.get('status', 'Completed')
    period = request.GET.get('period', 'day')
    date_str = request.GET.get('date')
    search = request.GET.get('search', '')
    orders = Order.objects.filter(status=status)
    if date_str:
        if period == 'day':
            orders = orders.filter(date_ordered__date=datetime.strptime(date_str, '%Y-%m-%d').date())
        elif period == 'month':
            dt = datetime.strptime(date_str, '%Y-%m')
            orders = orders.filter(date_ordered__year=dt.year, date_ordered__month=dt.month)
        elif period == 'year':
            dt = datetime.strptime(date_str, '%Y')
            orders = orders.filter(date_ordered__year=dt.year)
    if search:
        orders = orders.filter(notes__icontains=search) | orders.filter(id__icontains=search)
    orders = orders.select_related('table', 'kasir').prefetch_related('order_details__product').order_by('-date_ordered')
    total_income = orders.aggregate(total=Sum('total_price'))['total'] or 0
    return render(request, 'kasir_order_report.html', {
        'orders': orders,
        'total_income': total_income,
        'status': status,
        'period': period,
        'date_str': date_str or '',
        'search': search,
    })

@login_required
@role_required(allowed_roles=['kasir', 'owner'])
def checkout(request, order_id):
    order = Order.objects.select_related('table', 'kasir').prefetch_related('order_details__product').get(id=order_id)
    return render(request, 'checkout.html', {'order': order})

@csrf_exempt
def midtrans_webhook(request):
    import json
    from django.http import JsonResponse
    logger = logging.getLogger(__name__)
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid request method"}, status=400)
    if not request.body:
        return JsonResponse({"status": "error", "message": "Empty request body"}, status=400)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Invalid JSON format"}, status=400)
    order_id = data.get("order_id")
    transaction_status = data.get("transaction_status")
    logger.info(f"Midtrans Webhook: order_id={order_id}, transaction_status={transaction_status}")
    if not order_id:
        logger.error("No order_id in webhook data")
        return JsonResponse({"status": "error", "message": "No order_id"}, status=400)
    try:
        order = Order.objects.get(id=order_id)
        if transaction_status in ["settlement", "capture"]:
            order.payment_status = "Paid"
            order.save()
            # Update Payment record if exists
            payment, created = Payment.objects.get_or_create(order=order)
            payment.payment_method = 'Midtrans'
            payment.payment_status = 'Paid'
            payment.amount_paid = order.total_price
            payment.save()
            logger.info(f"Order {order_id} updated to Paid (Processing).")
        elif transaction_status in ["cancel", "expire"]:
            order.payment_status = "Cancelled"
            order.status = "Cancelled"
            order.save()
            payment, created = Payment.objects.get_or_create(order=order)
            payment.payment_method = 'Midtrans'
            payment.payment_status = 'Cancelled'
            payment.amount_paid = 0
            payment.save()
            logger.info(f"Order {order_id} updated to Cancelled.")
        else:
            logger.info(f"Order {order_id} received transaction_status: {transaction_status}")
        return JsonResponse({"status": "ok"})
    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found.")
        return JsonResponse({"status": "not found"}, status=404)
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

@login_required
@role_required(allowed_roles=['kasir', 'owner'])
def get_midtrans_token(request, order_id):
    order = Order.objects.get(id=order_id)
    url = 'https://app.sandbox.midtrans.com/snap/v1/transactions'
    server_key = 'SB-Mid-server-kq9bJK9lOejbQFONtGzpVySZ'
    import base64, json, requests
    encoded = base64.b64encode(f"{server_key}:".encode()).decode()
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': f'Basic {encoded}'
    }
    items = [
        {
            'id': d.product.id,
            'price': int(d.price),
            'quantity': d.quantity,
            'name': d.product.name
        } for d in order.order_details.all()
    ]
    gross_amount = sum(item['price'] * item['quantity'] for item in items)
    payload = {
        'transaction_details': {
            'order_id': str(order.id),
            'gross_amount': gross_amount
        },
        'item_details': items,
        'customer_details': {
            'first_name': order.notes or 'Customer',
            'table': order.table.table_number if order.table else 'Takeaway',
        },
        'enabled_payments': ['gopay', 'qris', 'bank_transfer', 'echannel', 'bca_klikbca', 'bca_klikpay', 'bri_epay', 'cimb_clicks', 'danamon_online', 'indomaret', 'alfamart', 'akulaku'],
    }
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    try:
        snap_token = response.json().get('token')
    except Exception:
        snap_token = None
    if not snap_token:
        print('MIDTRANS ERROR:', response.text)
        # Return error message to frontend
        return JsonResponse({'token': None, 'error': response.text}, status=400)
    return JsonResponse({'token': snap_token})

def kasir_owner_logout(request):
    logout(request)
    return redirect('kasir_owner_login')

@csrf_exempt
@login_required
@role_required(allowed_roles=['kasir', 'owner'])
def pay_cash(request, order_id):
    if request.method == 'POST':
        try:
            order = Order.objects.get(id=order_id)
            if order.status not in ['Completed', 'Cancelled']:
                order.payment_status = 'Paid'
                order.status = 'Processing'  # Set to Processing for cash
                order.save()
                Payment.objects.create(order=order, payment_method='Cash', payment_status='Paid', amount=order.total_price)
                return JsonResponse({'success': True, 'message': 'Order telah dibayar.'})
            else:
                return JsonResponse({'success': False, 'message': 'Order sudah selesai atau dibatalkan.'})
        except Order.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Order tidak ditemukan.'})
    return JsonResponse({'success': False, 'message': 'Invalid request.'})

@csrf_exempt
@login_required
@role_required(allowed_roles=['kasir', 'owner'])
def confirm_cash_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    # Hanya boleh confirm cash jika order dari customer dan belum paid
    if not order.kasir and order.payment_status.lower() != 'paid':
        order.payment_status = 'Paid'
        order.kasir = request.user
        order.save()
        # Optional: buat Payment record atau update
        payment, created = Payment.objects.get_or_create(
            order=order,
            defaults={
                'payment_method': 'Cash',
                'payment_status': 'Paid',
                'amount': order.total_price  # Pastikan nama field-nya sesuai model
            }
        )
        if not created:
            payment.payment_method = 'Cash'
            payment.payment_status = 'Paid'
            payment.amount = order.total_price
            payment.save()

        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)

@login_required
@role_required(allowed_roles=['owner', 'kasir'])
def download_qr(request, table_id):
    table = get_object_or_404(Table, id=table_id)
    if not table.qr_code:
        return JsonResponse({'error': 'QR code not found'}, status=404)
    qr_path = table.qr_code.path if hasattr(table.qr_code, 'path') else os.path.join(settings.MEDIA_ROOT, str(table.qr_code))
    return FileResponse(open(qr_path, 'rb'), as_attachment=True, filename=f'meja-{table.table_number}.png')

@login_required
@role_required(allowed_roles=['owner', 'kasir'])
def qr_list(request):
    tables = Table.objects.all()
    return render(request, 'qr_list.html', {'tables': tables})

def customer_login(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        if not name or not phone:
            return render(request, 'customer_login.html', {'error': 'Nama dan nomor WhatsApp wajib diisi.'})
        # Batasi OTP per nomor (misal 3x/10 menit)
        recent_otp_count = CustomerOTPSession.objects.filter(phone_number=phone, created_at__gte=timezone.now()-timedelta(minutes=10)).count()
        if recent_otp_count >= 3:
            return render(request, 'customer_login.html', {'error': 'Terlalu banyak permintaan OTP. Coba lagi nanti.'})
        otp = f"{random.randint(100000, 999999)}"
        expires = timezone.now() + timedelta(minutes=5)
        session = CustomerOTPSession.objects.create(phone_number=phone, otp_code=otp, expires_at=expires)
        # Kirim OTP via WhatsApp (dummy print, ganti dengan Twilio/Meta API)
        print(f"OTP untuk {phone}: {otp}")
        request.session['otp_session_token'] = str(session.session_token)
        request.session['customer_name'] = name
        request.session['customer_phone'] = phone
        return redirect('customer_otp_verify')
    # GET
    return render(request, 'customer_login.html')

def customer_otp_verify(request):
    token = request.session.get('otp_session_token')
    if not token:
        return redirect('customer_login')
    session = CustomerOTPSession.objects.filter(session_token=token).first()
    if not session or session.is_expired():
        return render(request, 'customer_otp_verify.html', {'error': 'OTP sudah kedaluwarsa. Silakan login ulang.'})
    if request.method == 'POST':
        otp_input = request.POST.get('otp')
        if otp_input == session.otp_code:
            session.is_verified = True
            session.save()
            request.session['is_customer_verified'] = True
            return redirect('customer_order')
        else:
            return render(request, 'customer_otp_verify.html', {'error': 'OTP salah. Coba lagi.'})
    return render(request, 'customer_otp_verify.html')

from django.views.decorators.http import require_GET
@require_GET
def customer_order(request):
    # Hanya bisa akses jika sudah login dan OTP
    if not request.session.get('is_customer_verified'):
        return redirect('customer_login')
    from .models import Table, Product
    tables = Table.objects.all()
    products = Product.objects.all()
    customer_name = request.session.get('customer_name', '')
    customer_phone = request.session.get('customer_phone', '')
    return render(request, 'customer_order.html', {
        'products': products,
        'tables': tables,
        'customer_name': customer_name,
        'customer_phone': customer_phone,
    })

@csrf_exempt
def customer_update_name(request):
    if not request.session.get('is_customer_verified'):
        return JsonResponse({'success': False, 'error': 'Belum login.'}, status=403)
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        if not name:
            return JsonResponse({'success': False, 'error': 'Nama tidak boleh kosong.'})
        request.session['customer_name'] = name
        return JsonResponse({'success': True, 'name': name})
    return JsonResponse({'success': False, 'error': 'Invalid request.'}, status=400)

@csrf_exempt
def customer_logout(request):
    request.session.flush()
    return JsonResponse({'success': True})

@csrf_exempt
def customer_order_checkout(request):
    # Hanya bisa akses jika sudah login dan OTP
    if not request.session.get('is_customer_verified'):
        return JsonResponse({'success': False, 'error': 'Belum login.'}, status=403)
    if request.method == 'POST':
        import json
        from .models import Table, Order, OrderDetail
        data = json.loads(request.body)
        cart = data.get('cart', [])
        customer_name = request.session.get('customer_name', 'Pelanggan QR')
        customer_phone = request.session.get('customer_phone', '')
        meja_number = data.get('meja_number', '')
        takeaway = data.get('takeaway', False)
        payment_method = data.get('payment_method', 'midtrans')
        table = None
        if not takeaway and meja_number:
            table = Table.objects.filter(table_number=meja_number).first()
        # Buat order
        order = Order.objects.create(
            table=table,
            total_price=sum(int(item['price']) * int(item['qty']) for item in cart),
            status='Processing',
            payment_status='Pending',
            source='qr_scan',
            notes='',
            phone_number=customer_phone,
            payment_method=payment_method,
            customer_name=customer_name,  # Simpan nama customer
        )
        for item in cart:
            OrderDetail.objects.create(
                order=order,
                product_id=item['id'],
                quantity=item['qty'],
                price=item['price'],
            )
        # Payment
        if payment_method == 'cash':
            return JsonResponse({'success': True, 'order_id': order.id})
        # Midtrans Snap: gunakan logika yang sudah ada (copy dari get_midtrans_token)
        import requests, base64
        import json as pyjson
        url = 'https://app.sandbox.midtrans.com/snap/v1/transactions'
        server_key = 'SB-Mid-server-kq9bJK9lOejbQFONtGzpVySZ'
        encoded = base64.b64encode(f"{server_key}:".encode()).decode()
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': f'Basic {encoded}'
        }
        items = [
            {
                'id': d['id'],
                'price': int(d['price']),
                'quantity': int(d['qty']),
                'name': d['name'] if 'name' in d else 'Produk'
            } for d in cart
        ]
        gross_amount = sum(item['price'] * item['quantity'] for item in items)
        payload = {
            'transaction_details': {
                'order_id': str(order.id),
                'gross_amount': gross_amount
            },
            'item_details': items,
            'customer_details': {
                'first_name': customer_name or 'Customer',
                'phone': customer_phone,
                'table': table.table_number if table else 'Takeaway',
            },
            'enabled_payments': [
                'gopay', 'qris', 'bank_transfer', 'echannel', 'bca_klikbca',
                'bca_klikpay', 'bri_epay', 'cimb_clicks', 'danamon_online',
                'indomaret', 'alfamart', 'akulaku'
            ],
        }
        response = requests.post(url, headers=headers, data=pyjson.dumps(payload))
        try:
            snap_token = response.json().get('token')
        except Exception:
            snap_token = None
        if not snap_token:
            return JsonResponse({'success': False, 'error': response.text}, status=400)
        return JsonResponse({'success': True, 'order_id': order.id, 'snap_token': snap_token})
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

def customer_order_success(request, order_id):
    from .models import Order
    order = Order.objects.filter(id=order_id).first()
    if not order:
        return render(request, 'customer_order_error.html', {'error': 'Order tidak ditemukan.'})
    return render(request, 'customer_order_success.html', {'order': order})

from django.views.decorators.http import require_GET
@require_GET
def customer_checkout(request):
    # Hanya bisa akses jika sudah login dan OTP
    if not request.session.get('is_customer_verified'):
        return redirect('customer_login')
    from .models import Table
    tables = Table.objects.all()
    return render(request, 'customer_checkout.html', {'tables': tables})

from django.views.decorators.http import require_GET

@require_GET
def customer_order_history(request):
    # Hanya bisa akses jika sudah login dan OTP
    if not request.session.get('is_customer_verified'):
        return JsonResponse({'orders': []})
    from .models import Order
    customer_phone = request.session.get('customer_phone', '')
    orders = Order.objects.filter(phone_number=customer_phone, source='qr_scan').order_by('-date_ordered')
    data = [
        {
            'id': o.id,
            'status': o.status,
            'created_at': o.date_ordered.strftime('%d %b %Y %H:%M'),
            'total_price': int(o.total_price),
        }
        for o in orders
    ]
    return JsonResponse({'orders': data})

@require_GET
def customer_order_history_detail(request, order_id):
    # Hanya bisa akses jika sudah login dan OTP
    if not request.session.get('is_customer_verified'):
        return JsonResponse({'order': None})
    from .models import Order, OrderDetail
    customer_phone = request.session.get('customer_phone', '')
    try:
        order = Order.objects.get(id=order_id, phone_number=customer_phone, source='qr_scan')
    except Order.DoesNotExist:
        return JsonResponse({'order': None})
    items = [
        {
            'name': d.product.name,
            'qty': d.quantity,
            'price': int(d.price),
        }
        for d in order.order_details.all()
    ]
    data = {
        'id': order.id,
        'status': order.status,
        'created_at': order.date_ordered.strftime('%d %b %Y %H:%M'),
        'total_price': int(order.total_price),
        'items': items,
    }
    return JsonResponse({'order': data})

