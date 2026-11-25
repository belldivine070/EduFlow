"""
Finance URL configuration.
"""
from django.urls import path
from finance import views

app_name = "finance"

urlpatterns = [
    # Fee Structure
    path("structures/", views.FeeStructureListView.as_view(), name="fee_structures"),

    # Invoices
    path("invoices/", views.InvoiceListView.as_view(), name="invoice_list"),
    path("invoices/<uuid:pk>/", views.InvoiceDetailView.as_view(), name="invoice_detail"),
    path("invoices/bulk-generate/", views.ClassInvoiceBulkGenerateView.as_view(), name="invoice_bulk_generate"),

    # Payments & Paystack
    path("invoices/<uuid:pk>/pay/", views.PaymentRecordView.as_view(), name="payment_record"),
    path("paystack/verify/", views.PaystackVerifyView.as_view(), name="paystack_verify"),
    path("receipt/<uuid:pk>/", views.PaymentReceiptView.as_view(), name="payment_receipt"),
]
