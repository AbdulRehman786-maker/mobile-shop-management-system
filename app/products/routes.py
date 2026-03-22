"""
Product management routes
"""
import csv
from io import StringIO
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, Response
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Product, InventoryLog
from app.utils.money import to_cents, from_cents
from app.utils.authz import admin_required

products_bp = Blueprint('products', __name__, url_prefix='/products')


@products_bp.route('/')
@login_required
def list_products():
    """List all products"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    category = request.args.get('category', '', type=str)
    brand = request.args.get('brand', '', type=str)
    model = request.args.get('model', '', type=str)
    
    query = Product.query.filter_by(is_listed=True)
    
    if search:
        query = query.filter(
            (Product.name.ilike(f'%{search}%')) |
            (Product.brand.ilike(f'%{search}%')) |
            (Product.barcode.ilike(f'%{search}%'))
        )
    
    if category:
        query = query.filter_by(category=category)

    if brand:
        query = query.filter(Product.brand == brand)
    if model:
        query = query.filter(Product.model == model)
    
    products = query.paginate(page=page, per_page=current_app.config['ITEMS_PER_PAGE'])
    brand_query = db.session.query(Product.brand).filter(Product.is_listed == True)
    if category:
        brand_query = brand_query.filter(Product.category == category)
    brand_options = [r[0] for r in brand_query.distinct().order_by(Product.brand).all() if r[0]]

    model_query = db.session.query(Product.model).filter(Product.is_listed == True)
    if category:
        model_query = model_query.filter(Product.category == category)
    if brand:
        model_query = model_query.filter(Product.brand == brand)
    model_options = [r[0] for r in model_query.distinct().order_by(Product.model).all() if r[0]]
    pending_products = []
    if current_user.is_admin():
        pending_products = Product.query.filter(
            Product.is_listed == False,
            Product.listed_at.is_(None),
            Product.stock_quantity > 0
        ).order_by(Product.created_at.desc()).all()
    
    return render_template(
        'products/list.html',
        products=products,
        search=search,
        category=category,
        brand=brand,
        model=model,
        brand_options=brand_options,
        model_options=model_options,
        pending_products=pending_products
    )


@products_bp.route('/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_product():
    """Direct product creation is intentionally disabled."""
    flash('Direct product creation is disabled. Add products from pending purchased items only.', 'warning')
    return redirect(url_for('products.list_products'))


@products_bp.route('/<int:product_id>/view')
@login_required
def view_product(product_id):
    """View product details"""
    product = Product.query.get_or_404(product_id)
    logs = InventoryLog.query.filter_by(product_id=product_id).order_by(InventoryLog.created_at.desc()).limit(20).all()
    
    return render_template('products/view.html', product=product, logs=logs)


@products_bp.route('/<int:product_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_product(product_id):
    """Delete product"""
    product = Product.query.get_or_404(product_id)
    
    # Check if product has sales or purchases
    if product.sale_items or product.purchase_items:
        # Keep transaction history intact: archive instead of hard-delete.
        product.is_listed = False
        if product.listed_at is None:
            product.listed_at = datetime.utcnow()
        product.archived_at = datetime.utcnow()
        product.archived_by = current_user.id
        db.session.commit()
        flash('Product has transaction history, so it was archived instead of deleted.', 'warning')
        return redirect(url_for('products.list_products'))
    
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted successfully!', 'success')
    return redirect(url_for('products.list_products'))


@products_bp.route('/api/search')
@login_required
def search_products():
    """API endpoint for product search (used in sales/purchases)"""
    query = request.args.get('q', '', type=str)
    
    if len(query) < 2:
        return {'products': []}
    
    products = Product.query.filter(
        Product.is_listed == True,
        (Product.name.ilike(f'%{query}%')) |
        (Product.barcode.ilike(f'%{query}%'))
    ).limit(10).all()
    
    return {
        'products': [
            {
                'id': p.id,
                'name': p.name,
                'price': from_cents(p.price_cents or to_cents(p.price)),
                'stock': p.stock_quantity,
                'barcode': p.barcode
            }
            for p in products
        ]
    }


@products_bp.route('/export-csv')
@login_required
def export_products_csv():
    """Export products inventory as CSV."""
    if not current_user.is_staff():
        flash('You do not have permission to export products.', 'danger')
        return redirect(url_for('dashboard.index'))

    search = request.args.get('search', '', type=str)
    category = request.args.get('category', '', type=str)
    brand = request.args.get('brand', '', type=str)
    model = request.args.get('model', '', type=str)

    query = Product.query.filter_by(is_listed=True)
    if search:
        query = query.filter(
            (Product.name.ilike(f'%{search}%')) |
            (Product.brand.ilike(f'%{search}%')) |
            (Product.barcode.ilike(f'%{search}%'))
        )
    if category:
        query = query.filter_by(category=category)
    if brand:
        query = query.filter(Product.brand == brand)
    if model:
        query = query.filter(Product.model == model)

    products = query.order_by(Product.name).all()
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        'ID', 'Name', 'Brand', 'Model', 'Category', 'Stock Quantity',
        'Cost Price', 'Selling Price', 'Barcode', 'IMEI', 'Stock Value'
    ])
    writer.writeheader()

    for product in products:
        writer.writerow({
            'ID': product.id,
            'Name': product.name,
            'Brand': product.brand,
            'Model': product.model,
            'Category': product.category,
            'Stock Quantity': product.stock_quantity,
            'Cost Price': from_cents(product.cost_price_cents or to_cents(product.cost_price)),
            'Selling Price': from_cents(product.price_cents or to_cents(product.price)),
            'Barcode': product.barcode,
            'IMEI': product.imei,
            'Stock Value': (product.stock_quantity or 0) * (from_cents(product.cost_price_cents or to_cents(product.cost_price)))
        })

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=products_inventory.csv'}
    )


@products_bp.route('/add-from-purchase', methods=['POST'])
@login_required
@admin_required
def add_from_purchase():
    """Mark a purchased pending product as listed in product catalog."""
    product_id = request.form.get('product_id', type=int)
    quantity_to_add = request.form.get('quantity_to_add', type=int)
    product = Product.query.get_or_404(product_id)

    if product.is_listed:
        flash('Selected product is already in products list.', 'info')
        return redirect(url_for('products.list_products'))

    available_qty = int(product.stock_quantity or 0)
    if available_qty <= 0:
        flash('Selected pending product has no available stock.', 'danger')
        return redirect(url_for('products.list_products'))

    if not quantity_to_add or quantity_to_add <= 0:
        flash('Please enter a valid quantity to add.', 'danger')
        return redirect(url_for('products.list_products'))

    if quantity_to_add > available_qty:
        flash(f'Quantity exceeds available pending stock ({available_qty}).', 'danger')
        return redirect(url_for('products.list_products'))

    now = datetime.utcnow()
    if quantity_to_add == available_qty:
        product.is_listed = True
        product.listed_at = now
        flash('Purchased item moved to Products list successfully.', 'success')
    else:
        listed_clone = Product(
            name=product.name,
            brand=product.brand,
            model=product.model,
            category=product.category,
            price=product.price,
            cost_price=product.cost_price,
            price_cents=product.price_cents or to_cents(product.price),
            cost_price_cents=product.cost_price_cents or to_cents(product.cost_price),
            stock_quantity=quantity_to_add,
            barcode=product.barcode,
            imei=product.imei,
            image=product.image,
            description=product.description,
            is_listed=True,
            first_purchased_at=product.first_purchased_at,
            listed_at=now
        )
        product.stock_quantity = available_qty - quantity_to_add
        if product.barcode:
            product.barcode = None
        db.session.add(listed_clone)
        flash(f'{quantity_to_add} quantity added to Products. Remaining pending: {product.stock_quantity}.', 'success')

    db.session.commit()
    return redirect(url_for('products.list_products'))
