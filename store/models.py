"""
Store and Inventory data models.

Supports:
- Product management, categories, SKU tracking, pricing.
- Stock adjustments with auditable StockMovement history (Previous, Changed, New, Reason, User).
- Point of sale & student store orders.
- Atomic stock reduction preventing overselling.
"""
import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone
from core.models import TimestampedModel

MOVEMENT_TYPE_RESTOCK = "restock"
MOVEMENT_TYPE_SALE = "sale"
MOVEMENT_TYPE_DAMAGE = "damage"
MOVEMENT_TYPE_ADJUSTMENT = "adjustment"
MOVEMENT_TYPE_RETURN = "return"

MOVEMENT_TYPE_CHOICES = [
    (MOVEMENT_TYPE_RESTOCK, "Restock / Supply"),
    (MOVEMENT_TYPE_SALE, "Sale / Purchase"),
    (MOVEMENT_TYPE_DAMAGE, "Damaged / Expired"),
    (MOVEMENT_TYPE_ADJUSTMENT, "Audit Adjustment"),
    (MOVEMENT_TYPE_RETURN, "Customer Return"),
]

ORDER_STATUS_PENDING = "pending"
ORDER_STATUS_COMPLETED = "completed"
ORDER_STATUS_CANCELLED = "cancelled"

ORDER_STATUS_CHOICES = [
    (ORDER_STATUS_PENDING, "Pending"),
    (ORDER_STATUS_COMPLETED, "Completed"),
    (ORDER_STATUS_CANCELLED, "Cancelled"),
]


class ProductCategory(TimestampedModel):
    """
    Category for school store items (e.g. Uniforms, Textbooks, Stationery, Sportswear).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="product_categories",
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Product Category"
        verbose_name_plural = "Product Categories"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["school", "name"], name="unique_school_product_category")
        ]

    def __str__(self):
        return f"{self.name} ({self.school.code})"


class Product(TimestampedModel):
    """
    School store item / inventory item.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="products",
    )
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.CASCADE,
        related_name="products",
    )
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=64, blank=True, default="", db_index=True)
    description = models.TextField(blank=True, default="")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    stock_quantity = models.IntegerField(default=0)
    low_stock_threshold = models.IntegerField(default=5)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} (Qty: {self.stock_quantity}) - ₦{self.price:,.2f}"

    @property
    def is_low_stock(self) -> bool:
        return self.stock_quantity <= self.low_stock_threshold


class StockMovement(models.Model):
    """
    Auditable stock transaction log.
    Records every single addition, deduction, or adjustment to inventory.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="stock_movements",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="movements",
    )
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPE_CHOICES)
    previous_quantity = models.IntegerField()
    quantity_changed = models.IntegerField(help_text="Positive for addition, negative for deduction.")
    new_quantity = models.IntegerField()
    reason = models.CharField(max_length=255, blank=True, default="")
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_stock_movements",
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        verbose_name = "Stock Movement"
        verbose_name_plural = "Stock Movements"
        ordering = ["-created_at"]

    def __str__(self):
        sign = "+" if self.quantity_changed > 0 else ""
        return f"{self.product.name}: {sign}{self.quantity_changed} ({self.get_movement_type_display()})"


class StoreOrder(TimestampedModel):
    """
    School store purchase order / receipt.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="store_orders",
    )
    order_number = models.CharField(max_length=64, db_index=True)
    student = models.ForeignKey(
        "academics.StudentProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="store_orders",
    )
    customer_name = models.CharField(max_length=200)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default=ORDER_STATUS_COMPLETED)
    payment_method = models.CharField(max_length=20, default="cash")
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_store_orders",
    )
    completed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Store Order"
        verbose_name_plural = "Store Orders"
        ordering = ["-completed_at"]
        constraints = [
            models.UniqueConstraint(fields=["school", "order_number"], name="unique_school_store_order")
        ]

    def __str__(self):
        return f"{self.order_number} - {self.customer_name} (₦{self.total_amount:,.2f})"


class StoreOrderItem(models.Model):
    """
    Item inside a StoreOrder.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        StoreOrder,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="order_items",
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Store Order Item"
        verbose_name_plural = "Store Order Items"

    def __str__(self):
        return f"{self.quantity}x {self.product.name} @ ₦{self.unit_price:,.2f}"
