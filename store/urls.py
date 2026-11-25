"""
Store URL configuration.
"""
from django.urls import path
from store import views

app_name = "store"

urlpatterns = [
    # Products & Stock
    path("products/", views.ProductListView.as_view(), name="product_list"),
    path("products/<uuid:pk>/adjust/", views.StockAdjustmentView.as_view(), name="stock_adjust"),
    path("movements/", views.StockMovementHistoryView.as_view(), name="movement_history"),

    # Point of Sale & Orders
    path("pos/", views.StorePOSView.as_view(), name="pos"),
    path("orders/", views.StoreOrderListView.as_view(), name="order_list"),
]
