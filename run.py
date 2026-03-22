"""
Application entry point
"""
import os
import secrets
from sqlalchemy import inspect
from dotenv import load_dotenv

load_dotenv()
from app import create_app, db
from app.models import User, Product, Customer, Supplier, Sale, Purchase

app = create_app(os.environ.get('FLASK_ENV', 'development'))


@app.shell_context_processor
def make_shell_context():
    """Make models available in Flask shell"""
    return {
        'db': db,
        'User': User,
        'Product': Product,
        'Customer': Customer,
        'Supplier': Supplier,
        'Sale': Sale,
        'Purchase': Purchase
    }


@app.cli.command()
def init_db():
    """Initialize database and bootstrap admin/staff accounts."""
    if not inspect(db.engine).has_table('users'):
        raise RuntimeError('Database tables are missing. Run "flask db upgrade" first.')

    admin_email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
    admin_password = os.environ.get('ADMIN_PASSWORD') or secrets.token_urlsafe(10)
    staff_email = os.environ.get('STAFF_EMAIL', 'staff@example.com')
    staff_password = os.environ.get('STAFF_PASSWORD') or secrets.token_urlsafe(10)

    created_accounts = []

    if not User.query.filter_by(email=admin_email).first():
        admin = User(
            name='Admin User',
            email=admin_email,
            role='admin'
        )
        admin.set_password(admin_password)
        db.session.add(admin)
        created_accounts.append(('Admin', admin_email, admin_password))

    if not User.query.filter_by(email=staff_email).first():
        staff = User(
            name='Staff Member',
            email=staff_email,
            role='staff'
        )
        staff.set_password(staff_password)
        db.session.add(staff)
        created_accounts.append(('Staff', staff_email, staff_password))

    db.session.commit()

    if created_accounts:
        for role_name, email, password in created_accounts:
            print(f'{role_name} account created: {email} / {password}')
    else:
        print('Database already initialized. No new users were created.')


if __name__ == '__main__':
    app.run(debug=app.config.get('DEBUG', False))
