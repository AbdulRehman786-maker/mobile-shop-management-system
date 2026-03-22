"""
Customer management routes
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Customer, Sale
from app.utils.money import to_cents
from app.utils.validators import is_non_empty, is_valid_email, is_valid_pk_phone
from app.utils.authz import staff_required

customers_bp = Blueprint('customers', __name__, url_prefix='/customers')


@customers_bp.route('/')
@login_required
@staff_required
def list_customers():
    """List all customers"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    
    query = Customer.query.filter_by(is_active=True)
    
    if search:
        query = query.filter(
            (Customer.name.ilike(f'%{search}%')) |
            (Customer.phone.ilike(f'%{search}%')) |
            (Customer.email.ilike(f'%{search}%'))
        )
    
    customers = query.order_by(Customer.id).paginate(page=page, per_page=current_app.config['ITEMS_PER_PAGE'])
    
    return render_template('customers/list.html', customers=customers, search=search)


@customers_bp.route('/add', methods=['GET', 'POST'])
@login_required
@staff_required
def add_customer():
    """Add new customer"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        if not is_non_empty(name):
            flash('Customer name is required.', 'danger')
            return render_template('customers/form.html', title='Add Customer')
        if not is_valid_pk_phone(phone):
            flash('Phone must be in Pakistani format: 03XXXXXXXXX.', 'danger')
            return render_template('customers/form.html', title='Add Customer')
        if email and not is_valid_email(email):
            flash('Invalid email address.', 'danger')
            return render_template('customers/form.html', title='Add Customer')

        customer = Customer(
            name=name,
            phone=phone,
            email=email or None,
            address=request.form.get('address'),
            city=request.form.get('city'),
            state=request.form.get('state'),
            postal_code=request.form.get('postal_code'),
            created_by=current_user.id
        )
        
        db.session.add(customer)
        db.session.commit()
        
        flash('Customer added successfully!', 'success')
        return redirect(url_for('customers.list_customers'))
    
    return render_template('customers/form.html', title='Add Customer')


@customers_bp.route('/<int:customer_id>/edit', methods=['GET', 'POST'])
@login_required
@staff_required
def edit_customer(customer_id):
    """Edit customer"""
    customer = Customer.query.get_or_404(customer_id)
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        if not is_non_empty(name):
            flash('Customer name is required.', 'danger')
            return render_template('customers/form.html', customer=customer, title='Edit Customer')
        if not is_valid_pk_phone(phone):
            flash('Phone must be in Pakistani format: 03XXXXXXXXX.', 'danger')
            return render_template('customers/form.html', customer=customer, title='Edit Customer')
        if email and not is_valid_email(email):
            flash('Invalid email address.', 'danger')
            return render_template('customers/form.html', customer=customer, title='Edit Customer')

        customer.name = name
        customer.phone = phone
        customer.email = email or None
        customer.address = request.form.get('address')
        customer.city = request.form.get('city')
        customer.state = request.form.get('state')
        customer.postal_code = request.form.get('postal_code')
        
        db.session.commit()
        
        flash('Customer updated successfully!', 'success')
        return redirect(url_for('customers.list_customers'))
    
    return render_template('customers/form.html', customer=customer, title='Edit Customer')


@customers_bp.route('/<int:customer_id>/view')
@login_required
@staff_required
def view_customer(customer_id):
    """View customer details and purchase history"""
    customer = Customer.query.get_or_404(customer_id)
    sales = Sale.query.filter_by(customer_id=customer_id).order_by(Sale.sale_date.desc()).all()

    total_spent_cents = sum(
        (sale.total_amount_cents or to_cents(sale.total_amount)) for sale in sales
    )
    average_spent_cents = int(total_spent_cents / len(sales)) if sales else 0
    
    return render_template(
        'customers/view.html',
        customer=customer,
        sales=sales,
        total_spent_cents=total_spent_cents,
        average_spent_cents=average_spent_cents
    )


@customers_bp.route('/<int:customer_id>/delete', methods=['POST'])
@login_required
@staff_required
def delete_customer(customer_id):
    """Delete customer"""
    customer = Customer.query.get_or_404(customer_id)
    
    # Check if customer has sales
    if customer.sales:
        customer.is_active = False
        db.session.commit()
        flash('Customer has sales history, so it was archived instead of deleted.', 'warning')
        return redirect(url_for('customers.list_customers'))
    
    db.session.delete(customer)
    db.session.commit()
    
    flash('Customer deleted successfully!', 'success')
    return redirect(url_for('customers.list_customers'))


@customers_bp.route('/api/search')
@login_required
def search_customers():
    """API endpoint for customer search"""
    query = request.args.get('q', '', type=str)
    
    if len(query) < 2:
        return {'customers': []}
    
    customers = Customer.query.filter(
        Customer.is_active == True,
        (
            (Customer.name.ilike(f'%{query}%')) |
            (Customer.phone.ilike(f'%{query}%'))
        )
    ).limit(10).all()
    
    return {
        'customers': [
            {
                'id': c.id,
                'name': c.name,
                'phone': c.phone,
                'email': c.email
            }
            for c in customers
        ]
    }
