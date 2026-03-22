"""
Dashboard and reporting routes
"""
from datetime import datetime, timedelta
import csv
from io import StringIO
from flask import Blueprint, render_template, jsonify, request, Response, flash, url_for, redirect
from flask_login import login_required, current_user
from sqlalchemy import func
from app.extensions import db
from app.models import Sale, SaleItem, Product, Customer, Supplier
from app.utils.money import from_cents, to_cents

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')


@dashboard_bp.route('/')
@login_required
def index():
    """Main dashboard"""
    # Get statistics
    total_sales_cents = db.session.query(func.sum(Sale.total_amount_cents)).scalar() or 0
    products_sold = db.session.query(func.sum(SaleItem.quantity)).scalar() or 0
    total_customers = Customer.query.filter_by(is_active=True).count()
    total_suppliers = Supplier.query.filter_by(is_active=True).count()
    
    # Low stock products
    low_stock_products = Product.query.filter(
        Product.is_listed == True,
        Product.stock_quantity <= 10
    ).order_by(Product.stock_quantity.asc(), Product.name.asc()).all()
    
    # Recent sales
    recent_sales = Sale.query.order_by(Sale.sale_date.desc()).limit(5).all()
    
    # Revenue this month
    today = datetime.utcnow()
    month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_revenue_cents = db.session.query(func.sum(Sale.total_amount_cents)).filter(
        Sale.sale_date >= month_start
    ).scalar() or 0
    
    # Revenue today
    day_start = today.replace(hour=0, minute=0, second=0, microsecond=0)
    day_revenue_cents = db.session.query(func.sum(Sale.total_amount_cents)).filter(
        Sale.sale_date >= day_start
    ).scalar() or 0
    
    return render_template('dashboard/index.html',
        total_sales_cents=total_sales_cents,
        products_sold=products_sold,
        total_customers=total_customers,
        total_suppliers=total_suppliers,
        low_stock_products=low_stock_products,
        recent_sales=recent_sales,
        month_revenue_cents=month_revenue_cents,
        day_revenue_cents=day_revenue_cents
    )


@dashboard_bp.route('/api/sales-chart')
@login_required
def sales_chart():
    """API endpoint for daily sales chart"""
    days = request.args.get('days', 30, type=int)
    
    today = datetime.utcnow()
    start_date = today - timedelta(days=days)
    
    # Get sales grouped by date
    sales_data = db.session.query(
        func.date(Sale.sale_date).label('date'),
        func.sum(Sale.total_amount_cents).label('amount'),
        func.count(Sale.id).label('count')
    ).filter(
        Sale.sale_date >= start_date
    ).group_by(
        func.date(Sale.sale_date)
    ).order_by('date').all()
    
    dates = []
    amounts = []
    
    for sale in sales_data:
        dates.append(sale.date.strftime('%Y-%m-%d'))
        amounts.append(from_cents(int(sale.amount or 0)))
    
    return jsonify({
        'labels': dates,
        'data': amounts
    })


@dashboard_bp.route('/api/revenue-chart')
@login_required
def revenue_chart():
    """API endpoint for monthly revenue chart"""
    months = request.args.get('months', 12, type=int)
    
    today = datetime.utcnow()
    start_date = today - timedelta(days=31 * max(months, 1))

    # DB-agnostic monthly aggregation (works on SQLite/Postgres/MySQL)
    sales = Sale.query.filter(Sale.sale_date >= start_date).all()
    month_totals = {}
    for sale in sales:
        month_key = sale.sale_date.strftime('%Y-%m')
        month_totals[month_key] = month_totals.get(month_key, 0) + int(sale.total_amount_cents or to_cents(sale.total_amount))

    sorted_keys = sorted(month_totals.keys())
    labels = [datetime.strptime(k, '%Y-%m').strftime('%B %Y') for k in sorted_keys]
    amounts = [from_cents(month_totals[k]) for k in sorted_keys]
    
    return jsonify({
        'labels': labels,
        'data': amounts
    })


@dashboard_bp.route('/api/top-products')
@login_required
def top_products():
    """API endpoint for top selling products"""
    limit = request.args.get('limit', 10, type=int)
    
    top_products_data = db.session.query(
        Product.name,
        func.sum(SaleItem.quantity).label('total_quantity'),
        func.sum(SaleItem.subtotal_cents).label('total_revenue')
    ).join(
        SaleItem, Product.id == SaleItem.product_id
    ).group_by(
        Product.id, Product.name
    ).order_by(
        func.sum(SaleItem.quantity).desc()
    ).limit(limit).all()
    
    names = []
    quantities = []
    revenues = []
    
    for product in top_products_data:
        names.append(product.name)
        quantities.append(int(product.total_quantity or 0))
        revenues.append(from_cents(int(product.total_revenue or 0)))
    
    return jsonify({
        'names': names,
        'quantities': quantities,
        'revenues': revenues
    })


@dashboard_bp.route('/api/stock-overview')
@login_required
def stock_overview():
    """API endpoint for stock overview"""
    # Stock status
    total_stock_value_cents = db.session.query(
        func.sum(Product.stock_quantity * Product.cost_price_cents)
    ).filter(Product.is_listed == True).scalar() or 0
    
    low_stock = Product.query.filter(
        Product.is_listed == True,
        Product.stock_quantity <= 10
    ).count()
    out_of_stock = Product.query.filter(
        Product.is_listed == True,
        Product.stock_quantity == 0
    ).count()
    
    # Stock by category
    stock_by_category = db.session.query(
        Product.category,
        func.count(Product.id).label('count'),
        func.sum(Product.stock_quantity).label('total_quantity')
    ).filter(Product.is_listed == True).group_by(Product.category).all()
    
    categories = []
    counts = []
    quantities = []
    
    for category in stock_by_category:
        categories.append(category.category)
        counts.append(int(category.count or 0))
        quantities.append(int(category.total_quantity or 0))
    
    return jsonify({
        'total_stock_value': from_cents(int(total_stock_value_cents or 0)),
        'low_stock': low_stock,
        'out_of_stock': out_of_stock,
        'categories': categories,
        'counts': counts,
        'quantities': quantities
    })


@dashboard_bp.route('/reports')
@login_required
def reports():
    """Reports page"""
    if not current_user.is_admin():
        flash('You do not have permission to access reports.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    return render_template('dashboard/reports.html')


@dashboard_bp.route('/api/export-sales')
@login_required
def export_sales():
    """Export sales data to CSV."""
    if not current_user.is_admin():
        return jsonify({'error': 'Unauthorized'}), 403
    
    start_date = request.args.get('start_date', '', type=str)
    end_date = request.args.get('end_date', '', type=str)
    
    query = Sale.query
    
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
    
    sales = query.all()
    
    data = []
    for sale in sales:
        subtotal_cents = sum(item.subtotal_cents or to_cents(item.subtotal) for item in sale.sale_items)
        data.append({
            'Invoice ID': sale.id,
            'Date': sale.sale_date.strftime('%Y-%m-%d %H:%M'),
            'Customer': sale.customer.name,
            'Staff': sale.staff.name,
            'Items': len(sale.sale_items),
            'Subtotal': from_cents(subtotal_cents),
            'Discount': from_cents(sale.discount_cents or to_cents(sale.discount)),
            'Tax': from_cents(sale.tax_cents or to_cents(sale.tax)),
            'Total': from_cents(sale.total_amount_cents or to_cents(sale.total_amount)),
            'Payment Method': sale.payment_method
        })
    
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        'Invoice ID', 'Date', 'Customer', 'Staff', 'Items', 'Subtotal',
        'Discount', 'Tax', 'Total', 'Payment Method'
    ])
    writer.writeheader()
    writer.writerows(data)

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=sales_report_{datetime.utcnow().strftime("%Y%m%d")}.csv'
        }
    )


@dashboard_bp.route('/api/export-inventory')
@login_required
def export_inventory():
    """Export inventory data to CSV."""
    if not current_user.is_admin():
        return jsonify({'error': 'Unauthorized'}), 403
    
    products = Product.query.filter_by(is_listed=True).all()
    
    data = []
    for product in products:
        data.append({
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
            'Stock Value': (product.stock_quantity or 0) * from_cents(product.cost_price_cents or to_cents(product.cost_price))
        })
    
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        'ID', 'Name', 'Brand', 'Model', 'Category', 'Stock Quantity',
        'Cost Price', 'Selling Price', 'Barcode', 'IMEI', 'Stock Value'
    ])
    writer.writeheader()
    writer.writerows(data)

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=inventory_report_{datetime.utcnow().strftime("%Y%m%d")}.csv'
        }
    )


@dashboard_bp.after_app_request
def dashboard_no_cache(response):
    """Prevent stale dashboard metrics/charts from browser cache."""
    if request.endpoint and request.endpoint.startswith('dashboard.'):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response
