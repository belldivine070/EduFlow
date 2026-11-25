"""
Store views.

Handles product management, category setup, atomic stock adjustments,
point-of-sale store orders, and auditable stock movement logs.
"""
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Sum

from schools.services import resolve_school_template
from academics.models import StudentProfile
from store.models import (
    ProductCategory,
    Product,
    StockMovement,
    StoreOrder,
    MOVEMENT_TYPE_CHOICES,
    MOVEMENT_TYPE_RESTOCK,
)
from store.services import (
    adjust_stock,
    process_store_purchase,
)


class SchoolRequiredMixin(LoginRequiredMixin):
    def get_school(self):
        return getattr(self.request, "school", None)

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        school = self.get_school()
        if not school:
            messages.warning(request, "Please access the store through a verified school domain.")
            return redirect("accounts:dashboard")
        return super().dispatch(request, *args, **kwargs)


class ProductListView(SchoolRequiredMixin, View):
    """
    Store inventory management: list products, check stock quantities, add new products.
    """
    def get(self, request):
        school = self.get_school()
        categories = ProductCategory.objects.filter(school=school)
        products = Product.objects.filter(school=school).select_related("category")

        total_products = products.count()
        low_stock_count = sum(1 for p in products if p.is_low_stock)

        template = resolve_school_template(school, "store/products/list.html")
        return render(request, template, {
            "school": school,
            "categories": categories,
            "products": products,
            "total_products": total_products,
            "low_stock_count": low_stock_count,
            "movement_types": MOVEMENT_TYPE_CHOICES,
        })

    def post(self, request):
        school = self.get_school()
        action = request.POST.get("action")

        if action == "create_category":
            name = request.POST.get("name", "").strip()
            desc = request.POST.get("description", "").strip()
            if name:
                ProductCategory.objects.get_or_create(school=school, name=name, defaults={"description": desc})
                messages.success(request, f"Category '{name}' created.")
            else:
                messages.error(request, "Category name is required.")

        elif action == "create_product":
            cat_id = request.POST.get("category_id")
            name = request.POST.get("name", "").strip()
            sku = request.POST.get("sku", "").strip()
            price_str = request.POST.get("price", "0")
            initial_stock = int(request.POST.get("initial_stock", "0"))
            threshold = int(request.POST.get("threshold", "5"))

            try:
                category = get_object_or_404(ProductCategory, id=cat_id, school=school)
                price = Decimal(price_str)
                product = Product.objects.create(
                    school=school,
                    category=category,
                    name=name,
                    sku=sku,
                    price=price,
                    stock_quantity=initial_stock,
                    low_stock_threshold=threshold,
                )
                if initial_stock > 0:
                    StockMovement.objects.create(
                        school=school,
                        product=product,
                        movement_type=MOVEMENT_TYPE_RESTOCK,
                        previous_quantity=0,
                        quantity_changed=initial_stock,
                        new_quantity=initial_stock,
                        reason="Initial Stock Setup",
                        created_by=request.user,
                    )
                messages.success(request, f"Product '{name}' added to inventory.")
            except Exception as e:
                messages.error(request, f"Failed to create product: {str(e)}")

        return redirect("store:product_list")


class StockAdjustmentView(SchoolRequiredMixin, View):
    """
    Audit stock adjustment (restock, damage, audit correction).
    """
    def post(self, request, pk):
        school = self.get_school()
        product = get_object_or_404(Product, id=pk, school=school)

        qty_str = request.POST.get("quantity_changed", "0")
        movement_type = request.POST.get("movement_type")
        reason = request.POST.get("reason", "").strip()

        try:
            qty_changed = int(qty_str)
            movement = adjust_stock(
                product=product,
                quantity_changed=qty_changed,
                movement_type=movement_type,
                reason=reason,
                user=request.user,
            )
            messages.success(
                request,
                f"Stock adjusted for {product.name}. New Quantity: {movement.new_quantity}."
            )
        except ValidationError as e:
            messages.error(request, str(e.message if hasattr(e, 'message') else e))
        except Exception as e:
            messages.error(request, f"Failed to adjust stock: {str(e)}")

        return redirect("store:product_list")


class StorePOSView(SchoolRequiredMixin, View):
    """
    Point of Sale interface for selling store products directly to students or walk-ins.
    """
    def get(self, request):
        school = self.get_school()
        products = Product.objects.filter(school=school, is_active=True, stock_quantity__gt=0).select_related("category")
        students = StudentProfile.objects.filter(school=school, is_active=True).select_related("user")

        template = resolve_school_template(school, "store/pos.html")
        return render(request, template, {
            "school": school,
            "products": products,
            "students": students,
        })

    def post(self, request):
        school = self.get_school()
        customer_name = request.POST.get("customer_name", "").strip()
        student_id = request.POST.get("student_id")
        payment_method = request.POST.get("payment_method", "cash")

        student = StudentProfile.objects.filter(id=student_id, school=school).first() if student_id else None

        # Parse selected products and quantities: product_{id}
        items_data = []
        for key, val in request.POST.items():
            if key.startswith("qty_") and int(val or 0) > 0:
                prod_id = key.replace("qty_", "")
                items_data.append({
                    "product_id": prod_id,
                    "quantity": int(val),
                })

        try:
            order = process_store_purchase(
                school=school,
                items_data=items_data,
                customer_name=customer_name,
                student=student,
                payment_method=payment_method,
                user=request.user,
            )
            messages.success(request, f"Store Order #{order.order_number} completed! Total: ₦{order.total_amount:,.2f}.")
            return redirect("store:order_list")
        except ValidationError as e:
            messages.error(request, str(e.message if hasattr(e, 'message') else e))
        except Exception as e:
            messages.error(request, f"Failed to process store order: {str(e)}")

        return redirect("store:pos")


class StoreOrderListView(SchoolRequiredMixin, View):
    """
    List historical store sales and orders.
    """
    def get(self, request):
        school = self.get_school()
        orders = StoreOrder.objects.filter(school=school).select_related("student__user", "created_by").prefetch_related("items__product")
        total_sales = orders.aggregate(s=Sum("total_amount"))["s"] or Decimal("0.00")

        template = resolve_school_template(school, "store/orders.html")
        return render(request, template, {
            "school": school,
            "orders": orders[:100],
            "total_sales": total_sales,
        })


class StockMovementHistoryView(SchoolRequiredMixin, View):
    """
    Auditable inventory movement ledger.
    """
    def get(self, request):
        school = self.get_school()
        movements = StockMovement.objects.filter(school=school).select_related("product", "created_by")

        template = resolve_school_template(school, "store/movements.html")
        return render(request, template, {
            "school": school,
            "movements": movements[:150],
        })
