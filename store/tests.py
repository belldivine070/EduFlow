"""
Tests for Store and Inventory module.

Covers product management, categories, atomic stock adjustments,
audit ledger movements, point-of-sale store orders, and oversell protection.
"""
import datetime
from decimal import Decimal
from django.test import TestCase, Client
from django.core.exceptions import ValidationError

from schools.models import School, SchoolDomain
from academics.models import AcademicSession, SchoolClass
from academics.services import seed_school_classes, admit_student
from accounts.models import User, SchoolMembership
from core.constants import ROLE_DIRECTOR
from store.models import (
    ProductCategory,
    Product,
    StockMovement,
    StoreOrder,
    MOVEMENT_TYPE_RESTOCK,
    MOVEMENT_TYPE_SALE,
    MOVEMENT_TYPE_DAMAGE,
)
from store.services import (
    generate_order_number,
    adjust_stock,
    process_store_purchase,
)


class StoreTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.school = School.objects.create(
            name="Grace High School",
            code="GHS",
            slug="grace-high-school",
            student_id_prefix="GHS-STD-",
            is_active=True,
        )
        self.domain = SchoolDomain.objects.create(
            school=self.school,
            domain="grace.localhost",
            is_primary=True,
            is_verified=True,
        )

        seed_school_classes(self.school)
        self.jss1 = SchoolClass.objects.get(school=self.school, name="JSS 1")

        self.session = AcademicSession.objects.create(
            school=self.school,
            name="2026/2027",
            start_date=datetime.date(2026, 9, 1),
            end_date=datetime.date(2027, 7, 31),
            is_current=True,
        )

        # Create Director Staff User
        self.staff_user = User.objects.create_user(
            username="GHS-DIR-0001",
            first_name="Victoria",
            last_name="Olatunji",
            email="bursar@grace.ng",
            password="BursarPassword123!",
        )
        SchoolMembership.objects.create(
            user=self.staff_user,
            school=self.school,
            role=ROLE_DIRECTOR,
            id_number="GHS-DIR-0001",
            status="active",
        )

        # Student
        self.student_profile, self.enroll = admit_student(
            school=self.school,
            first_name="Dayo",
            last_name="Ojo",
            gender="male",
            school_class=self.jss1,
            session=self.session,
            date_of_birth=datetime.date(2013, 5, 20),
        )

        # Setup Product Category & Products
        self.uniform_cat = ProductCategory.objects.create(school=self.school, name="School Uniforms")
        self.books_cat = ProductCategory.objects.create(school=self.school, name="Books & Stationery")

        self.uniform_product = Product.objects.create(
            school=self.school,
            category=self.uniform_cat,
            name="Senior Secondary Blazer",
            sku="BLZ-SSS-M",
            price=Decimal("15000.00"),
            stock_quantity=20,
            low_stock_threshold=5,
        )

        self.notebook_product = Product.objects.create(
            school=self.school,
            category=self.books_cat,
            name="Higher Education 60-Leaves Notebook",
            sku="NB-60L",
            price=Decimal("800.00"),
            stock_quantity=50,
            low_stock_threshold=10,
        )

    def test_order_number_generation(self):
        """Order number follows {school.code}-ORD-{year}-{seq:04d} scheme."""
        ord_num = generate_order_number(self.school)
        current_year = datetime.date.today().year
        self.assertEqual(ord_num, f"GHS-ORD-{current_year}-0001")

    def test_adjust_stock_service_and_movement_logging(self):
        """adjust_stock updates quantity and creates an auditable StockMovement."""
        # Restock 10 blazers
        movement = adjust_stock(
            product=self.uniform_product,
            quantity_changed=10,
            movement_type=MOVEMENT_TYPE_RESTOCK,
            reason="Supplier Delivery Batch #44",
            user=self.staff_user,
        )

        self.uniform_product.refresh_from_db()
        self.assertEqual(self.uniform_product.stock_quantity, 30)
        self.assertEqual(movement.previous_quantity, 20)
        self.assertEqual(movement.quantity_changed, 10)
        self.assertEqual(movement.new_quantity, 30)
        self.assertEqual(movement.movement_type, MOVEMENT_TYPE_RESTOCK)
        self.assertEqual(movement.created_by, self.staff_user)

    def test_adjust_stock_prevents_negative_inventory(self):
        """Cannot deduct more than available inventory."""
        with self.assertRaises(ValidationError):
            adjust_stock(
                product=self.uniform_product,
                quantity_changed=-25,  # Only 20 in stock
                movement_type=MOVEMENT_TYPE_DAMAGE,
                reason="Water Damage",
            )
        self.uniform_product.refresh_from_db()
        self.assertEqual(self.uniform_product.stock_quantity, 20)

    def test_process_store_purchase_service(self):
        """Multi-item purchase deducts stock atomically and creates StoreOrder and movements."""
        items = [
            {"product_id": str(self.uniform_product.id), "quantity": 2},
            {"product_id": str(self.notebook_product.id), "quantity": 5},
        ]
        # (2 * 15,000) + (5 * 800) = 30,000 + 4,000 = 34,000
        order = process_store_purchase(
            school=self.school,
            items_data=items,
            customer_name="Mr. Ojo",
            student=self.student_profile,
            payment_method="cash",
            user=self.staff_user,
        )

        self.assertEqual(order.total_amount, Decimal("34000.00"))
        self.assertEqual(order.items.count(), 2)

        # Verify stock deductions
        self.uniform_product.refresh_from_db()
        self.assertEqual(self.uniform_product.stock_quantity, 18)

        self.notebook_product.refresh_from_db()
        self.assertEqual(self.notebook_product.stock_quantity, 45)

        # Verify Stock Movements logged as 'sale'
        movements = StockMovement.objects.filter(product=self.uniform_product, movement_type=MOVEMENT_TYPE_SALE)
        self.assertEqual(movements.count(), 1)
        self.assertEqual(movements.first().quantity_changed, -2)

    def test_store_purchase_prevents_overselling(self):
        """Purchase is rejected and rolled back if requested quantity exceeds stock."""
        items = [
            {"product_id": str(self.uniform_product.id), "quantity": 25},  # Only 20 in stock
        ]
        with self.assertRaises(ValidationError):
            process_store_purchase(
                school=self.school,
                items_data=items,
                customer_name="Walk-in",
            )

        self.uniform_product.refresh_from_db()
        self.assertEqual(self.uniform_product.stock_quantity, 20)
        self.assertEqual(StoreOrder.objects.filter(school=self.school).count(), 0)

    def test_store_views_and_pos_flow(self):
        """Staff can list products, perform POS checkout, and inspect movement ledger."""
        self.client.force_login(self.staff_user)

        # 1. Product list view
        prod_res = self.client.get("/store/products/", HTTP_HOST="grace.localhost")
        self.assertEqual(prod_res.status_code, 200)
        self.assertContains(prod_res, "Senior Secondary Blazer")

        # 2. POS View GET
        pos_res = self.client.get("/store/pos/", HTTP_HOST="grace.localhost")
        self.assertEqual(pos_res.status_code, 200)
        self.assertContains(pos_res, "Point of Sale")

        # 3. POS View POST (Sell 1 Blazer)
        post_data = {
            f"qty_{self.uniform_product.id}": "1",
            "customer_name": "Alhaji Ojo",
            "student_id": str(self.student_profile.id),
            "payment_method": "pos",
        }
        order_res = self.client.post("/store/pos/", post_data, HTTP_HOST="grace.localhost")
        self.assertEqual(order_res.status_code, 302)

        self.uniform_product.refresh_from_db()
        self.assertEqual(self.uniform_product.stock_quantity, 19)

        # 4. Sales Orders View
        orders_res = self.client.get("/store/orders/", HTTP_HOST="grace.localhost")
        self.assertEqual(orders_res.status_code, 200)
        self.assertContains(orders_res, "Alhaji Ojo")

        # 5. Stock Movements Audit Ledger
        mov_res = self.client.get("/store/movements/", HTTP_HOST="grace.localhost")
        self.assertEqual(mov_res.status_code, 200)
        self.assertContains(mov_res, "Senior Secondary Blazer")
