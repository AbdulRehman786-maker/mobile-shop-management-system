"""
Sales management routes
"""
import csv
from io import StringIO
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, Response, stream_with_context
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Sale, SaleItem, Product, Customer, InventoryLog
from app.utils.security import api_token_required
from app.utils.money import to_cents, from_cents
from app.utils.authz import staff_required
from sqlalchemy.orm import selectinload

sales_bp = Blueprint('sales', __name__, url_prefix='/sales')


@sales_bp.route('/')
@login_required
@staff_required
def list_sales():
    """List all sales"""
    page = request.args.get('page', 1, type=int)
    start_date = request.args.get('start_date', '', type=str)
    end_date = request.args.get('end_date', '', type=str)
    
    query = Sale.query.order_by(Sale.sale_date.desc())
    
    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Sale.sale_date >= start)
        except ValueError:
            pass
    
    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d')
            end = end.replace(hour=23, minute=59, second=59)
            query = query.filter(Sale.sale_date <= end)
        except ValueError:
            pass
    
    sales = query.paginate(page=page, per_page=current_app.config['ITEMS_PER_PAGE'])
    
    return render_template('sales/list.html', sales=sales, start_date=start_date, end_date=end_date)


@sales_bp.route('/export-csv')
@login_required
@staff_required
def export_sales_csv():
    """Export filtered sales list as CSV."""
    start_date = request.args.get('start_date', '', type=str)
    end_date = request.args.get('end_date', '', type=str)

    query = Sale.query.options(
        selectinload(Sale.customer),
        selectinload(Sale.staff),
        selectinload(Sale.sale_items)
    ).order_by(Sale.sale_date.desc())
    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Sale.sale_date >= start)
        except ValueError:
            pass
    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d')
            end = end.replace(hour=23, minute=59, second=59)
            query = query.filter(Sale.sale_date <= end)
        except ValueError:
            pass

    def generate():
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Invoice ID', 'Date', 'Customer', 'Staff', 'Items', 'Payment Method', 'Discount', 'Tax', 'Total'])
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        for sale in query.yield_per(1000):
            writer.writerow([
                sale.id,
                sale.sale_date.strftime('%Y-%m-%d %H:%M'),
                sale.customer.name,
                sale.staff.name,
                len(sale.sale_items),
                sale.payment_method,
                f'{from_cents(sale.discount_cents or to_cents(sale.discount)):.2f}',
                f'{from_cents(sale.tax_cents or to_cents(sale.tax)):.2f}',
                f'{from_cents(sale.total_amount_cents or to_cents(sale.total_amount)):.2f}'
            ])
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    return Response(
        stream_with_context(generate()),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=sales_{datetime.utcnow().strftime("%Y%m%d")}.csv'}
    )


@sales_bp.route('/create', methods=['GET', 'POST'])
@login_required
@staff_required
def create_sale():
    """Create new sale"""
    if request.method == 'POST':
        @api_token_required()
        def _inner():
            data = request.get_json()
            
            if not data.get('customer_id') or not data.get('items'):
                return jsonify({'error': 'Invalid data'}), 400
            
            customer = Customer.query.get(data['customer_id'])
            if not customer or not customer.is_active:
                return jsonify({'error': 'Customer not found'}), 404
            
            sale = Sale(
                customer_id=customer.id,
                staff_id=current_user.id,
                discount=float(data.get('discount', 0) or 0),
                tax=float(data.get('tax', 0) or 0),
                payment_method=data.get('payment_method', 'cash'),
                notes=data.get('notes', '')
            )

            total_amount_cents = 0
            pending_logs = []
            
            for item_data in data['items']:
                quantity = int(item_data['quantity'])
                if quantity <= 0:
                    return jsonify({'error': 'Quantity must be greater than 0'}), 400

                source_ids = item_data.get('source_ids') or []
                primary_id = item_data.get('primary_id') or item_data.get('product_id')
                if primary_id is None:
                    return jsonify({'error': 'Product reference is missing'}), 400

                primary_product = Product.query.get(primary_id)
                if not primary_product:
                    return jsonify({'error': f'Product {primary_id} not found'}), 404

                if source_ids:
                    candidate_products = Product.query.filter(Product.id.in_(source_ids)).all()
                    source_map = {product.id: product for product in candidate_products}
                    allocation_products = [source_map[pid] for pid in source_ids if pid in source_map]
                else:
                    allocation_products = [primary_product]

                if not allocation_products:
                    return jsonify({'error': 'No valid product stock source found'}), 404

                total_available = sum(max(product.stock_quantity or 0, 0) for product in allocation_products)
                if total_available < quantity:
                    return jsonify({'error': f'Insufficient stock for {primary_product.name}'}), 400

                unit_price_cents = int(primary_product.price_cents or to_cents(primary_product.price))
                remaining_qty = quantity

                for product in allocation_products:
                    if remaining_qty <= 0:
                        break
                    available_stock = max(product.stock_quantity or 0, 0)
                    if available_stock <= 0:
                        continue

                    allocated_qty = min(remaining_qty, available_stock)
                    subtotal_cents = allocated_qty * unit_price_cents

                    sale_item = SaleItem(
                        product_id=product.id,
                        quantity=allocated_qty,
                        price=from_cents(unit_price_cents),
                        price_cents=unit_price_cents,
                        subtotal=from_cents(subtotal_cents),
                        subtotal_cents=subtotal_cents
                    )
                    sale.sale_items.append(sale_item)

                    product.stock_quantity -= allocated_qty

                    log = InventoryLog(
                        product_id=product.id,
                        change_type='sale',
                        quantity=-allocated_qty,
                        reference_id=None,
                        reference_type='sale'
                    )
                    db.session.add(log)
                    pending_logs.append(log)

                    total_amount_cents += subtotal_cents
                    remaining_qty -= allocated_qty
            
            discount_cents = max(0, to_cents(sale.discount))
            tax_cents = max(0, to_cents(sale.tax))
            if discount_cents > total_amount_cents:
                discount_cents = total_amount_cents
            sale.discount_cents = discount_cents
            sale.tax_cents = tax_cents
            sale.total_amount_cents = max(0, total_amount_cents - discount_cents + tax_cents)
            sale.total_amount = from_cents(sale.total_amount_cents)
            sale.discount = from_cents(discount_cents)
            sale.tax = from_cents(tax_cents)
            
            db.session.add(sale)
            db.session.flush()
            
            # Update only logs created for this sale.
            for log in pending_logs:
                log.reference_id = sale.id
                log.sale_id = sale.id
            
            db.session.commit()
            
            flash('Sale created successfully!', 'success')
            return jsonify({'id': sale.id, 'redirect': url_for('sales.view_sale', sale_id=sale.id)})

        return _inner()
    
    customers = Customer.query.filter_by(is_active=True).order_by(Customer.name).all()
    products = Product.query.filter(Product.stock_quantity > 0).order_by(Product.name.asc()).all()
    grouped_products = {}
    for product in products:
        group_key = ' | '.join([
            (product.name or '').strip().lower(),
            (product.brand or '').strip().lower(),
            (product.model or '').strip().lower(),
            (product.category or '').strip().lower(),
        ])

        product_price = from_cents(product.price_cents or to_cents(product.price))
        payload = grouped_products.get(group_key)
        if payload is None:
            grouped_products[group_key] = {
                'id': product.id,
                'primary_id': product.id,
                'name': product.name,
                'brand': product.brand or '',
                'model': product.model or '',
                'barcode': product.barcode or '',
                'price': product_price,
                'min_price': product_price,
                'max_price': product_price,
                'stock': int(product.stock_quantity or 0),
                'primary_stock': int(product.stock_quantity or 0),
                'source_ids': [product.id],
            }
            continue

        payload['source_ids'].append(product.id)
        payload['stock'] += int(product.stock_quantity or 0)
        payload['min_price'] = min(payload['min_price'], product_price)
        payload['max_price'] = max(payload['max_price'], product_price)

        candidate_stock = int(product.stock_quantity or 0)
        if candidate_stock > payload['primary_stock']:
            payload['primary_id'] = product.id
            payload['id'] = product.id
            payload['price'] = product_price
            payload['primary_stock'] = candidate_stock
            if product.barcode:
                payload['barcode'] = product.barcode

    searchable_products = []
    for payload in grouped_products.values():
        payload.pop('primary_stock', None)
        searchable_products.append(payload)
    
    return render_template(
        'sales/create.html',
        customers=customers,
        searchable_products=searchable_products
    )


@sales_bp.route('/<int:sale_id>/view')
@login_required
@staff_required
def view_sale(sale_id):
    """View sale details"""
    sale = Sale.query.get_or_404(sale_id)
    return render_template('sales/view.html', sale=sale)


@sales_bp.route('/<int:sale_id>/invoice')
@login_required
@staff_required
def invoice(sale_id):
    """View sale invoice"""
    sale = Sale.query.get_or_404(sale_id)
    print_mode = request.args.get('print') == '1'
    return render_template('sales/invoice.html', sale=sale, print_mode=print_mode)


@sales_bp.route('/<int:sale_id>/pdf')
@login_required
@staff_required
def generate_pdf(sale_id):
    """Open invoice in print mode so browser Save as PDF matches web view."""
    Sale.query.get_or_404(sale_id)
    return redirect(url_for('sales.invoice', sale_id=sale_id, print='1'))


@sales_bp.route('/<int:sale_id>/delete', methods=['POST'])
@login_required
@staff_required
def delete_sale(sale_id):
    """Delete sale (admin only)"""
    if not current_user.is_admin():
        flash('You do not have permission to delete sales.', 'danger')
        return redirect(url_for('sales.list_sales'))
    
    sale = Sale.query.get_or_404(sale_id)
    
    # Restore stock
    for item in sale.sale_items:
        item.product.stock_quantity += item.quantity
        log = InventoryLog(
            product_id=item.product.id,
            change_type='return',
            quantity=item.quantity,
            reference_id=sale.id,
            reference_type='sale',
            sale_id=sale.id,
            notes='Sale cancelled'
        )
        db.session.add(log)
    
    # Delete inventory logs
    InventoryLog.query.filter_by(reference_id=sale_id, reference_type='sale').delete()
    
    db.session.delete(sale)
    db.session.commit()
    
    flash('Sale deleted successfully!', 'success')
    return redirect(url_for('sales.list_sales'))
