"""
Purchase management routes
"""
import base64
import binascii
import os
from uuid import uuid4
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy import func
from app.extensions import db
from app.models import Purchase, PurchaseItem, Product, Supplier, InventoryLog
from app.utils.security import api_token_required
from app.utils.money import to_cents, from_cents
from app.utils.images import detect_image_type
from app.utils.authz import admin_required

purchases_bp = Blueprint('purchases', __name__, url_prefix='/purchases')


def _save_inline_image(image_data, product_name):
    """Save data-URL image and return stored filename."""
    if not image_data or not isinstance(image_data, str) or ',' not in image_data:
        return None

    header, encoded = image_data.split(',', 1)
    if not header.startswith('data:image/'):
        return None

    mime_part = header.split(';')[0].replace('data:image/', '').lower()
    ext_map = {'jpeg': 'jpg', 'jpg': 'jpg', 'png': 'png', 'webp': 'webp', 'gif': 'gif'}
    ext = ext_map.get(mime_part)
    if not ext:
        return None

    try:
        content = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        return None

    # Keep uploads bounded for safety (5 MB).
    if len(content) > 5 * 1024 * 1024:
        return None

    # Verify content type by signature
    detected = detect_image_type(content)
    if detected == 'jpeg':
        detected = 'jpg'
    if detected not in ext_map:
        return None

    upload_dir = current_app.config.get('UPLOAD_FOLDER', 'app/static/uploads')
    os.makedirs(upload_dir, exist_ok=True)
    base_name = secure_filename(product_name or 'product')
    filename = f"{base_name}_{uuid4().hex[:8]}.{ext}"
    with open(os.path.join(upload_dir, filename), 'wb') as f:
        f.write(content)
    return filename


@purchases_bp.route('/')
@login_required
@admin_required
def list_purchases():
    """List all purchases"""
    page = request.args.get('page', 1, type=int)
    start_date = request.args.get('start_date', '', type=str)
    end_date = request.args.get('end_date', '', type=str)
    status = request.args.get('status', '', type=str)
    
    query = Purchase.query.order_by(Purchase.purchase_date.desc())
    
    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Purchase.purchase_date >= start)
        except ValueError:
            pass
    
    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d')
            end = end.replace(hour=23, minute=59, second=59)
            query = query.filter(Purchase.purchase_date <= end)
        except ValueError:
            pass
    
    if status:
        query = query.filter_by(payment_status=status)
    
    purchases = query.paginate(page=page, per_page=current_app.config['ITEMS_PER_PAGE'])
    product_stocks = Product.query.order_by(Product.stock_quantity.desc(), Product.name.asc()).all()
    
    return render_template(
        'purchases/list.html',
        purchases=purchases,
        start_date=start_date,
        end_date=end_date,
        status=status,
        product_stocks=product_stocks
    )


@purchases_bp.route('/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_purchase():
    """Create new purchase"""
    if request.method == 'POST':
        @api_token_required()
        def _inner():
            data = request.get_json()
            
            if not data.get('supplier_id') or not data.get('items'):
                return jsonify({'error': 'Invalid data'}), 400
            
            supplier = Supplier.query.get(data['supplier_id'])
            if not supplier:
                return jsonify({'error': 'Supplier not found'}), 404
            
            purchase = Purchase(
                supplier_id=supplier.id,
                payment_status=data.get('payment_status', 'pending'),
                notes=data.get('notes', '')
            )
            
            total_amount_cents = 0
            pending_logs = []
            
            for item_data in data['items']:
                product = None
                if item_data.get('product_id'):
                    product = Product.query.get(item_data['product_id'])
                    if not product:
                        return jsonify({'error': f'Product {item_data["product_id"]} not found'}), 404
                else:
                    new_product = item_data.get('new_product') or {}
                    required_fields = ['name', 'brand', 'model', 'category']
                    missing = [f for f in required_fields if not str(new_product.get(f, '')).strip()]
                    if missing:
                        return jsonify({'error': f'Missing new product fields: {", ".join(missing)}'}), 400

                    name = new_product['name'].strip()
                    brand = new_product['brand'].strip()
                    model = new_product['model'].strip()
                    category = new_product['category'].strip()
                    barcode = (new_product.get('barcode') or '').strip() or None

                    cost_price = float(item_data.get('cost_price', 0))
                    if cost_price <= 0:
                        return jsonify({'error': 'Cost price must be greater than 0'}), 400

                    selling_price = float(new_product.get('price', cost_price * 1.2))
                    if selling_price <= 0:
                        selling_price = cost_price * 1.2

                    # Reuse existing product when possible; don't create duplicates.
                    if barcode:
                        product = Product.query.filter_by(barcode=barcode).first()
                    if not product:
                        product = Product.query.filter(
                            func.lower(Product.name) == name.lower(),
                            func.lower(Product.brand) == brand.lower(),
                            func.lower(Product.model) == model.lower(),
                            func.lower(Product.category) == category.lower()
                        ).first()

                    if product:
                        # Keep pricing current on repeat purchases.
                        product.cost_price = cost_price
                        product.cost_price_cents = to_cents(cost_price)
                        if selling_price > 0:
                            product.price = selling_price
                            product.price_cents = to_cents(selling_price)
                    else:
                        image_filename = _save_inline_image(new_product.get('image_data'), name)
                        product = Product(
                            name=name,
                            brand=brand,
                            model=model,
                            category=category,
                            price=selling_price,
                            price_cents=to_cents(selling_price),
                            cost_price=cost_price,
                            cost_price_cents=to_cents(cost_price),
                            stock_quantity=0,
                            barcode=barcode,
                            imei=(new_product.get('imei') or '').strip() or None,
                            image=image_filename,
                            description=(new_product.get('description') or '').strip() or None,
                            is_listed=False,
                            first_purchased_at=datetime.utcnow(),
                            listed_at=None
                        )
                        db.session.add(product)
                        db.session.flush()
                
                quantity = int(item_data['quantity'])
                if quantity <= 0:
                    return jsonify({'error': 'Quantity must be greater than 0'}), 400
                
                cost_price = float(item_data.get('cost_price', product.cost_price))
                cost_price_cents = to_cents(cost_price)
                subtotal_cents = quantity * cost_price_cents
                
                existing_purchase_item = next(
                    (pi for pi in purchase.purchase_items if pi.product_id == product.id),
                    None
                )
                if existing_purchase_item:
                    existing_purchase_item.quantity += quantity
                    existing_purchase_item.subtotal_cents += subtotal_cents
                    existing_purchase_item.subtotal = from_cents(existing_purchase_item.subtotal_cents)
                    existing_purchase_item.cost_price_cents = cost_price_cents
                    existing_purchase_item.cost_price = from_cents(cost_price_cents)
                else:
                    purchase_item = PurchaseItem(
                        product_id=product.id,
                        quantity=quantity,
                        cost_price=from_cents(cost_price_cents),
                        cost_price_cents=cost_price_cents,
                        subtotal=from_cents(subtotal_cents),
                        subtotal_cents=subtotal_cents
                    )
                    purchase.purchase_items.append(purchase_item)
                
                # Increase stock
                product.stock_quantity += quantity
                product.cost_price = from_cents(cost_price_cents)
                product.cost_price_cents = cost_price_cents
                
                # Create inventory log
                log = InventoryLog(
                    product_id=product.id,
                    change_type='purchase',
                    quantity=quantity,
                    reference_type='purchase'
                )
                db.session.add(log)
                pending_logs.append(log)
                
                total_amount_cents += subtotal_cents
            
            purchase.total_amount_cents = total_amount_cents
            purchase.total_amount = from_cents(total_amount_cents)
            
            db.session.add(purchase)
            db.session.flush()
            
            # Update only logs created for this purchase.
            for log in pending_logs:
                log.reference_id = purchase.id
                log.purchase_id = purchase.id
            
            db.session.commit()
            
            flash('Purchase created successfully!', 'success')
            return jsonify({'id': purchase.id, 'redirect': url_for('purchases.view_purchase', purchase_id=purchase.id)})

        return _inner()
    
    suppliers = Supplier.query.filter_by(is_active=True).order_by(Supplier.name).all()
    products = Product.query.filter_by(is_listed=True).all()

    if not suppliers:
        flash('Please add at least one supplier before creating a purchase.', 'warning')
        return redirect(url_for('suppliers.add_supplier'))
    
    return render_template('purchases/create.html', suppliers=suppliers, products=products)


@purchases_bp.route('/<int:purchase_id>/view')
@login_required
@admin_required
def view_purchase(purchase_id):
    """View purchase details"""
    purchase = Purchase.query.get_or_404(purchase_id)
    return render_template('purchases/view.html', purchase=purchase)


@purchases_bp.route('/<int:purchase_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_purchase(purchase_id):
    """Edit purchase"""
    purchase = Purchase.query.get_or_404(purchase_id)
    
    if request.method == 'POST':
        if request.is_json:
            @api_token_required()
            def _inner_json():
                data = request.get_json(silent=True) or {}
                purchase.payment_status = data.get('payment_status', purchase.payment_status)
                purchase.notes = data.get('notes', purchase.notes)
                db.session.commit()
                flash('Purchase updated successfully!', 'success')
                return jsonify({'success': True})
            return _inner_json()

        purchase.payment_status = request.form.get('payment_status', purchase.payment_status)
        purchase.notes = request.form.get('notes', purchase.notes)
        db.session.commit()
        flash('Purchase updated successfully!', 'success')
        return redirect(url_for('purchases.view_purchase', purchase_id=purchase.id))
    
    return render_template('purchases/edit.html', purchase=purchase)


@purchases_bp.route('/<int:purchase_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_purchase(purchase_id):
    """Delete purchase"""
    purchase = Purchase.query.get_or_404(purchase_id)
    affected_product_ids = {item.product_id for item in purchase.purchase_items}
    
    # Restore stock
    for item in purchase.purchase_items:
        item.product.stock_quantity -= item.quantity
        if item.product.stock_quantity < 0:
            item.product.stock_quantity = 0
        log = InventoryLog(
            product_id=item.product.id,
            change_type='adjustment',
            quantity=-item.quantity,
            reference_id=purchase_id,
            reference_type='purchase',
            purchase_id=purchase_id,
            notes='Purchase cancelled'
        )
        db.session.add(log)
    
    # Delete inventory logs
    InventoryLog.query.filter_by(reference_id=purchase_id, reference_type='purchase').delete()
    
    db.session.delete(purchase)

    # Remove orphan pending products after purchase deletion.
    for product_id in affected_product_ids:
        product = Product.query.get(product_id)
        if not product:
            continue
        if (
            not product.is_listed
            and (product.stock_quantity or 0) <= 0
            and not product.purchase_items
            and not product.sale_items
        ):
            db.session.delete(product)

    db.session.commit()
    
    flash('Purchase deleted successfully!', 'success')
    return redirect(url_for('purchases.list_purchases'))
