from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from app.views import confirm_cash_payment, product_list, add_product, edit_product, delete_product, kasir_owner_login, kasir_owner_logout, order_menu, create_order, order_list, complete_order, kasir_dashboard, kasir_order_report, checkout, pay_cash, get_midtrans_token, midtrans_webhook, qr_list, download_qr, customer_login, customer_otp_verify, customer_order, customer_order_checkout, customer_order_success, customer_checkout, customer_order_history, customer_order_history_detail, customer_update_name, customer_logout

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', kasir_owner_login, name='kasir_owner_login'),
    path('logout/', kasir_owner_logout, name='kasir_owner_logout'),
    path('', kasir_dashboard, name='kasir_dashboard'),
    path('products/', product_list, name='product_list'),
    path('products/add/', add_product, name='add_product'),
    path('products/edit/<int:product_id>/', edit_product, name='edit_product'),
    path('products/delete/<int:product_id>/', delete_product, name='delete_product'),
    path('order/', order_menu, name='order_menu'),
    path('order/create/', create_order, name='create_order'),
    path('order-list/', order_list, name='order_list'),
    path('order/complete/', complete_order, name='complete_order'),
    path('order/<int:order_id>/confirm-cash/', confirm_cash_payment, name='confirm_cash_payment'),
    path('kasir/order-report/', kasir_order_report, name='kasir_order_report'),
    path('checkout/<int:order_id>/', checkout, name='checkout'),
    path('checkout/<int:order_id>/pay-cash/', pay_cash, name='pay_cash'),
    path('checkout/<int:order_id>/midtrans-token/', get_midtrans_token, name='get_midtrans_token'),
    path('midtrans-webhook/', midtrans_webhook, name='midtrans_webhook'),
    path('qr-list/', qr_list, name='qr_list'),
    path('download-qr/<int:table_id>/', download_qr, name='download_qr'),
    path('customer/login/', customer_login, name='customer_login'),
    path('customer/otp-verify/', customer_otp_verify, name='customer_otp_verify'),
    path('customer/order/', customer_order, name='customer_order'),
    path('customer/order/checkout/', customer_order_checkout, name='customer_order_checkout'),
    path('customer/order-success/<int:order_id>/', customer_order_success, name='customer_order_success'),
    path('customer/checkout/', customer_checkout, name='customer_checkout'),
    path('customer/order/history/', customer_order_history, name='customer_order_history'),
    path('customer/order/history/<int:order_id>/', customer_order_history_detail, name='customer_order_history_detail'),
    path('customer/profile/update-name/', customer_update_name, name='customer_update_name'),
    path('customer/logout/', customer_logout, name='customer_logout'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)