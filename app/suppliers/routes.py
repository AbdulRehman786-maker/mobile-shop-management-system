"""
Supplier management routes
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required
from app.extensions import db
from app.models import Supplier, Purchase
from app.utils.money import to_cents
from app.utils.validators import is_non_empty, is_valid_email, is_valid_pk_phone
from app.utils.authz import admin_required

suppliers_bp = Blueprint('suppliers', __name__, url_prefix='/suppliers')


@suppliers_bp.route('/')
@login_required
@admin_required
def list_suppliers():
    """List all suppliers."""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)

    query = Supplier.query.filter_by(is_active=True)
    if search:
        query = query.filter(
            (Supplier.name.ilike(f'%{search}%')) |
            (Supplier.company.ilike(f'%{search}%')) |
            (Supplier.phone.ilike(f'%{search}%')) |
            (Supplier.email.ilike(f'%{search}%'))
        )

    suppliers = query.order_by(Supplier.id).paginate(
        page=page,
        per_page=current_app.config['ITEMS_PER_PAGE']
    )
    return render_template('suppliers/list.html', suppliers=suppliers, search=search)


@suppliers_bp.route('/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_supplier():
    """Add new supplier."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        company = request.form.get('company', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        if not is_non_empty(name) or not is_non_empty(company):
            flash('Supplier name and company are required.', 'danger')
            return render_template('suppliers/form.html', title='Add Supplier')
        if not is_valid_pk_phone(phone):
            flash('Phone must be in Pakistani format: 03XXXXXXXXX.', 'danger')
            return render_template('suppliers/form.html', title='Add Supplier')
        if email and not is_valid_email(email):
            flash('Invalid email address.', 'danger')
            return render_template('suppliers/form.html', title='Add Supplier')

        supplier = Supplier(
            name=name,
            company=company,
            phone=phone,
            email=email or None,
            address=request.form.get('address'),
            city=request.form.get('city'),
            state=request.form.get('state'),
            postal_code=request.form.get('postal_code')
        )

        db.session.add(supplier)
        db.session.commit()

        flash('Supplier added successfully!', 'success')
        return redirect(url_for('suppliers.list_suppliers'))

    return render_template('suppliers/form.html', title='Add Supplier')


@suppliers_bp.route('/<int:supplier_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_supplier(supplier_id):
    """Edit supplier."""
    supplier = Supplier.query.get_or_404(supplier_id)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        company = request.form.get('company', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        if not is_non_empty(name) or not is_non_empty(company):
            flash('Supplier name and company are required.', 'danger')
            return render_template('suppliers/form.html', supplier=supplier, title='Edit Supplier')
        if not is_valid_pk_phone(phone):
            flash('Phone must be in Pakistani format: 03XXXXXXXXX.', 'danger')
            return render_template('suppliers/form.html', supplier=supplier, title='Edit Supplier')
        if email and not is_valid_email(email):
            flash('Invalid email address.', 'danger')
            return render_template('suppliers/form.html', supplier=supplier, title='Edit Supplier')

        supplier.name = name
        supplier.company = company
        supplier.phone = phone
        supplier.email = email or None
        supplier.address = request.form.get('address')
        supplier.city = request.form.get('city')
        supplier.state = request.form.get('state')
        supplier.postal_code = request.form.get('postal_code')

        db.session.commit()
        flash('Supplier updated successfully!', 'success')
        return redirect(url_for('suppliers.list_suppliers'))

    return render_template('suppliers/form.html', supplier=supplier, title='Edit Supplier')


@suppliers_bp.route('/<int:supplier_id>/view')
@login_required
@admin_required
def view_supplier(supplier_id):
    """View supplier details and purchase history."""
    supplier = Supplier.query.get_or_404(supplier_id)
    purchases = Purchase.query.filter_by(supplier_id=supplier_id).order_by(Purchase.purchase_date.desc()).all()
    total_spent_cents = sum(
        (p.total_amount_cents or to_cents(p.total_amount)) for p in purchases
    )
    return render_template(
        'suppliers/view.html',
        supplier=supplier,
        purchases=purchases,
        total_spent_cents=total_spent_cents
    )


@suppliers_bp.route('/<int:supplier_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_supplier(supplier_id):
    """Delete supplier."""
    supplier = Supplier.query.get_or_404(supplier_id)

    if supplier.purchases:
        supplier.is_active = False
        db.session.commit()
        flash('Supplier has purchase history, so it was archived instead of deleted.', 'warning')
        return redirect(url_for('suppliers.list_suppliers'))

    db.session.delete(supplier)
    db.session.commit()
    flash('Supplier deleted successfully!', 'success')
    return redirect(url_for('suppliers.list_suppliers'))
