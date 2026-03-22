"""initial schema

Revision ID: c9436d4f0733
Revises:
Create Date: 2026-03-17 02:19:43.491441
"""
from alembic import op
import sqlalchemy as sa


revision = "c9436d4f0733"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=120), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="staff"),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=False)

    op.create_table(
        "suppliers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("company", sa.String(length=120), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("email", sa.String(length=120), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("postal_code", sa.String(length=20), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("email", sa.String(length=120), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("postal_code", sa.String(length=20), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_customers_created_by_users"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_customers_phone", "customers", ["phone"], unique=False)
    op.create_index("ix_customers_created_by", "customers", ["created_by"], unique=False)

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("brand", sa.String(length=100), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("cost_price", sa.Float(), nullable=False),
        sa.Column("price_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_price_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stock_quantity", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("barcode", sa.String(length=100), nullable=True),
        sa.Column("imei", sa.String(length=100), nullable=True),
        sa.Column("image", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_listed", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("first_purchased_at", sa.DateTime(), nullable=True),
        sa.Column("listed_at", sa.DateTime(), nullable=True),
        sa.Column("archived_at", sa.DateTime(), nullable=True),
        sa.Column("archived_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["archived_by"], ["users.id"], name="fk_products_archived_by_users"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("barcode"),
    )
    op.create_index("ix_products_barcode", "products", ["barcode"], unique=False)

    op.create_table(
        "purchases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=False),
        sa.Column("purchase_date", sa.DateTime(), nullable=True),
        sa.Column("total_amount", sa.Float(), nullable=False),
        sa.Column("total_amount_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("payment_status", sa.String(length=50), nullable=True, server_default="pending"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], name="fk_purchases_supplier_id_suppliers"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_purchases_purchase_date", "purchases", ["purchase_date"], unique=False)
    op.create_index("ix_purchases_supplier_id", "purchases", ["supplier_id"], unique=False)

    op.create_table(
        "sales",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("staff_id", sa.Integer(), nullable=False),
        sa.Column("sale_date", sa.DateTime(), nullable=True),
        sa.Column("total_amount", sa.Float(), nullable=False),
        sa.Column("total_amount_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("discount", sa.Float(), nullable=True, server_default="0"),
        sa.Column("discount_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tax", sa.Float(), nullable=True, server_default="0"),
        sa.Column("tax_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("payment_method", sa.String(length=50), nullable=True, server_default="cash"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], name="fk_sales_customer_id_customers"),
        sa.ForeignKeyConstraint(["staff_id"], ["users.id"], name="fk_sales_staff_id_users"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sales_customer_id", "sales", ["customer_id"], unique=False)
    op.create_index("ix_sales_sale_date", "sales", ["sale_date"], unique=False)
    op.create_index("ix_sales_staff_id", "sales", ["staff_id"], unique=False)

    op.create_table(
        "purchase_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("purchase_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("cost_price", sa.Float(), nullable=False),
        sa.Column("cost_price_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("subtotal", sa.Float(), nullable=False),
        sa.Column("subtotal_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], name="fk_purchase_items_product_id_products"),
        sa.ForeignKeyConstraint(["purchase_id"], ["purchases.id"], name="fk_purchase_items_purchase_id_purchases"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_purchase_items_product_id", "purchase_items", ["product_id"], unique=False)
    op.create_index("ix_purchase_items_purchase_id", "purchase_items", ["purchase_id"], unique=False)

    op.create_table(
        "sale_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sale_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("price_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("subtotal", sa.Float(), nullable=False),
        sa.Column("subtotal_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], name="fk_sale_items_product_id_products"),
        sa.ForeignKeyConstraint(["sale_id"], ["sales.id"], name="fk_sale_items_sale_id_sales"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sale_items_product_id", "sale_items", ["product_id"], unique=False)
    op.create_index("ix_sale_items_sale_id", "sale_items", ["sale_id"], unique=False)

    op.create_table(
        "inventory_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("change_type", sa.String(length=50), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("reference_id", sa.Integer(), nullable=True),
        sa.Column("reference_type", sa.String(length=50), nullable=True),
        sa.Column("sale_id", sa.Integer(), nullable=True),
        sa.Column("purchase_id", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], name="fk_inventory_logs_product_id_products"),
        sa.ForeignKeyConstraint(["purchase_id"], ["purchases.id"], name="fk_inventory_logs_purchase_id_purchases"),
        sa.ForeignKeyConstraint(["sale_id"], ["sales.id"], name="fk_inventory_logs_sale_id_sales"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inventory_logs_created_at", "inventory_logs", ["created_at"], unique=False)
    op.create_index("ix_inventory_logs_product_id", "inventory_logs", ["product_id"], unique=False)
    op.create_index("ix_inventory_logs_purchase_id", "inventory_logs", ["purchase_id"], unique=False)
    op.create_index("ix_inventory_logs_sale_id", "inventory_logs", ["sale_id"], unique=False)


def downgrade():
    op.drop_index("ix_inventory_logs_sale_id", table_name="inventory_logs")
    op.drop_index("ix_inventory_logs_purchase_id", table_name="inventory_logs")
    op.drop_index("ix_inventory_logs_product_id", table_name="inventory_logs")
    op.drop_index("ix_inventory_logs_created_at", table_name="inventory_logs")
    op.drop_table("inventory_logs")

    op.drop_index("ix_sale_items_sale_id", table_name="sale_items")
    op.drop_index("ix_sale_items_product_id", table_name="sale_items")
    op.drop_table("sale_items")

    op.drop_index("ix_purchase_items_purchase_id", table_name="purchase_items")
    op.drop_index("ix_purchase_items_product_id", table_name="purchase_items")
    op.drop_table("purchase_items")

    op.drop_index("ix_sales_staff_id", table_name="sales")
    op.drop_index("ix_sales_sale_date", table_name="sales")
    op.drop_index("ix_sales_customer_id", table_name="sales")
    op.drop_table("sales")

    op.drop_index("ix_purchases_supplier_id", table_name="purchases")
    op.drop_index("ix_purchases_purchase_date", table_name="purchases")
    op.drop_table("purchases")

    op.drop_index("ix_products_barcode", table_name="products")
    op.drop_table("products")

    op.drop_index("ix_customers_created_by", table_name="customers")
    op.drop_index("ix_customers_phone", table_name="customers")
    op.drop_table("customers")

    op.drop_table("suppliers")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
