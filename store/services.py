"""
Store and inventory services.

Handles atomic stock adjustments, auditable movement logging,
and purchase order processing with race-condition prevention and oversell protection.
"""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from store.models import (
    Product,
    StockMovement,
    StoreOrder,
    StoreOrderItem,
    MOVEMENT_TYPE_SALE,
    ORDER_STATUS_COMPLETED,
)


def generate_order_number(school) -> str:
    """
    Generate unique store order number for school tenant.
    Format: {SCHOOL_CODE}-ORD-{YEAR}-{SEQ:04d}
    """
    year = str(timezone.now().year)
    prefix = f"{school.code}-ORD-{year}-"
    latest = (
        StoreOrder.objects.filter(school=school, order_number__startswith=prefix)
        .order_by("-order_number")
        .first()
    )
    if latest:
        try:
            last_seq = int(latest.order_number.split("-")[-1])
            new_seq = last_seq + 1
        except (ValueError, IndexError):
            new_seq = 1
    else:
        new_seq = 1
    return f"{prefix}{new_seq:04d}"


@transaction.atomic
def adjust_stock(
    *,
    product: Product,
    quantity_changed: int,
    movement_type: str,
    reason: str = "",
    user=None,
) -> StockMovement:
    """
    Atomically updates a product's stock quantity and writes an auditable StockMovement.
    Locks the product row using select_for_update to prevent race conditions.
    """
    # Lock row for update
    locked_product = Product.objects.select_for_update().get(id=product.id)
    prev_qty = locked_product.stock_quantity
    new_qty = prev_qty + quantity_changed

    if new_qty < 0:
        raise ValidationError(
            f"Cannot adjust inventory for '{locked_product.name}'. Requested change ({quantity_changed}) "
            f"exceeds current available stock ({prev_qty})."
        )

    locked_product.stock_quantity = new_qty
    locked_product.save(update_fields=["stock_quantity", "updated_at"])

    movement = StockMovement.objects.create(
        school=locked_product.school,
        product=locked_product,
        movement_type=movement_type,
        previous_quantity=prev_qty,
        quantity_changed=quantity_changed,
        new_quantity=new_qty,
        reason=reason.strip(),
        created_by=user,
        created_at=timezone.now(),
    )
    return movement


@transaction.atomic
def process_store_purchase(
    *,
    school,
    items_data: list,
    customer_name: str,
    student=None,
    payment_method: str = "cash",
    user=None,
) -> StoreOrder:
    """
    Process a store order across multiple items.
    items_data: list of dicts [{'product_id': UUID/str, 'quantity': int}]
    Validates inventory availability across all items before deducting.
    """
    if not items_data:
        raise ValidationError("Store order must include at least one product.")

    order_number = generate_order_number(school)
    total_order_amount = Decimal("0.00")
    order_items_to_create = []

    # 1. Lock all target products and validate stock availability
    for item_spec in items_data:
        product_id = item_spec["product_id"]
        qty = int(item_spec["quantity"])
        if qty <= 0:
            raise ValidationError("Item quantity must be greater than zero.")

        product = Product.objects.select_for_update().get(id=product_id, school=school)
        if product.stock_quantity < qty:
            raise ValidationError(
                f"Insufficient stock for '{product.name}'. Requested: {qty}, Available: {product.stock_quantity}."
            )

        line_total = product.price * qty
        total_order_amount += line_total
        order_items_to_create.append({
            "product": product,
            "quantity": qty,
            "unit_price": product.price,
            "total_price": line_total,
        })

    # 2. Create Order Header
    order = StoreOrder.objects.create(
        school=school,
        order_number=order_number,
        student=student,
        customer_name=customer_name.strip() or (student.user.get_full_name() if student else "Walk-in Customer"),
        total_amount=total_order_amount,
        status=ORDER_STATUS_COMPLETED,
        payment_method=payment_method,
        created_by=user,
        completed_at=timezone.now(),
    )

    # 3. Create items and log stock deductions
    for item_spec in order_items_to_create:
        product = item_spec["product"]
        qty = item_spec["quantity"]

        StoreOrderItem.objects.create(
            order=order,
            product=product,
            quantity=qty,
            unit_price=item_spec["unit_price"],
            total_price=item_spec["total_price"],
        )

        # Deduct stock and log movement
        adjust_stock(
            product=product,
            quantity_changed=-qty,
            movement_type=MOVEMENT_TYPE_SALE,
            reason=f"Store Order {order.order_number}",
            user=user,
        )

    return order
