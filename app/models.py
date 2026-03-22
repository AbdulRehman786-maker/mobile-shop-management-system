"""
Database models for Mobile Shop Management System
"""
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.extensions import db


class User(UserMixin, db.Model):
    """User model with role-based access control"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='staff', nullable=False)  # admin, staff
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sales = db.relationship('Sale', backref='staff', lazy=True, foreign_keys='Sale.staff_id')
    customers = db.relationship('Customer', backref='created_by_user', lazy=True)
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify password"""
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        """Check if user is admin"""
        return self.role == 'admin'
    
    def is_staff(self):
        """Check if user is staff"""
        return self.role in ['admin', 'staff']
    
    def __repr__(self):
        return f'<User {self.email}>'


class Product(db.Model):
    """Product model for mobile phones and accessories"""
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    brand = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # mobile, accessory
    price = db.Column(db.Float, nullable=False)
    cost_price = db.Column(db.Float, nullable=False)
    price_cents = db.Column(db.Integer, nullable=False, default=0)
    cost_price_cents = db.Column(db.Integer, nullable=False, default=0)
    stock_quantity = db.Column(db.Integer, default=0)
    barcode = db.Column(db.String(100), unique=True, nullable=True, index=True)
    imei = db.Column(db.String(100), nullable=True)
    image = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    is_listed = db.Column(db.Boolean, default=True, nullable=False)
    first_purchased_at = db.Column(db.DateTime, nullable=True)
    listed_at = db.Column(db.DateTime, nullable=True)
    archived_at = db.Column(db.DateTime, nullable=True)
    archived_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sale_items = db.relationship('SaleItem', backref='product', lazy=True, cascade='all, delete-orphan')
    purchase_items = db.relationship('PurchaseItem', backref='product', lazy=True, cascade='all, delete-orphan')
    inventory_logs = db.relationship('InventoryLog', backref='product', lazy=True, cascade='all, delete-orphan')
    
    def get_low_stock_status(self, threshold=10):
        """Check if product is low on stock"""
        return self.stock_quantity <= threshold
    
    def __repr__(self):
        return f'<Product {self.name}>'


class Customer(db.Model):
    """Customer model"""
    __tablename__ = 'customers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False, index=True)
    email = db.Column(db.String(120), nullable=True)
    address = db.Column(db.Text, nullable=True)
    city = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(100), nullable=True)
    postal_code = db.Column(db.String(20), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sales = db.relationship('Sale', backref='customer', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Customer {self.name}>'


class Supplier(db.Model):
    """Supplier model"""
    __tablename__ = 'suppliers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    company = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    address = db.Column(db.Text, nullable=True)
    city = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(100), nullable=True)
    postal_code = db.Column(db.String(20), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    purchases = db.relationship('Purchase', backref='supplier', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Supplier {self.name}>'


class Sale(db.Model):
    """Sale transaction model"""
    __tablename__ = 'sales'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False, index=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    sale_date = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    total_amount = db.Column(db.Float, nullable=False)
    total_amount_cents = db.Column(db.Integer, nullable=False, default=0)
    discount = db.Column(db.Float, default=0)
    discount_cents = db.Column(db.Integer, nullable=False, default=0)
    tax = db.Column(db.Float, default=0)
    tax_cents = db.Column(db.Integer, nullable=False, default=0)
    payment_method = db.Column(db.String(50), default='cash')  # cash, card, check
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sale_items = db.relationship('SaleItem', backref='sale', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Sale {self.id}>'


class SaleItem(db.Model):
    """Individual items in a sale"""
    __tablename__ = 'sale_items'
    
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    price_cents = db.Column(db.Integer, nullable=False, default=0)
    subtotal = db.Column(db.Float, nullable=False)
    subtotal_cents = db.Column(db.Integer, nullable=False, default=0)
    
    def __repr__(self):
        return f'<SaleItem {self.id}>'


class Purchase(db.Model):
    """Purchase order from suppliers"""
    __tablename__ = 'purchases'
    
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False, index=True)
    purchase_date = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    total_amount = db.Column(db.Float, nullable=False)
    total_amount_cents = db.Column(db.Integer, nullable=False, default=0)
    payment_status = db.Column(db.String(50), default='pending')  # pending, paid, partial
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    purchase_items = db.relationship('PurchaseItem', backref='purchase', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Purchase {self.id}>'


class PurchaseItem(db.Model):
    """Individual items in a purchase"""
    __tablename__ = 'purchase_items'
    
    id = db.Column(db.Integer, primary_key=True)
    purchase_id = db.Column(db.Integer, db.ForeignKey('purchases.id'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    quantity = db.Column(db.Integer, nullable=False)
    cost_price = db.Column(db.Float, nullable=False)
    cost_price_cents = db.Column(db.Integer, nullable=False, default=0)
    subtotal = db.Column(db.Float, nullable=False)
    subtotal_cents = db.Column(db.Integer, nullable=False, default=0)
    
    def __repr__(self):
        return f'<PurchaseItem {self.id}>'


class InventoryLog(db.Model):
    """Inventory change tracking"""
    __tablename__ = 'inventory_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    change_type = db.Column(db.String(50), nullable=False)  # sale, purchase, adjustment, return
    quantity = db.Column(db.Integer, nullable=False)
    reference_id = db.Column(db.Integer, nullable=True)  # sale_id or purchase_id (legacy)
    reference_type = db.Column(db.String(50), nullable=True)  # sale, purchase (legacy)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=True, index=True)
    purchase_id = db.Column(db.Integer, db.ForeignKey('purchases.id'), nullable=True, index=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f'<InventoryLog {self.id}>'
