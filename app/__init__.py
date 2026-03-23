"""
Flask application factory
"""
import os
from flask import Flask, redirect, url_for
from flask_login import current_user
from sqlalchemy import inspect, text
from config import config
from app.extensions import db, login_manager, migrate, csrf
from app.utils.security import get_api_token
from app.utils.money import from_cents


def create_app(config_name=None):
    """Application factory function"""
    
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'production')
    
    app = Flask(__name__)
    app.config.from_object(config.get(config_name, config['development']))

    if config_name == 'production' and app.config.get('SECRET_KEY') == 'dev-secret-key-change-in-production':
        raise RuntimeError("SECRET_KEY must be set in production.")
    
    # Create upload folder if it doesn't exist
    upload_folder = app.config['UPLOAD_FOLDER']
    os.makedirs(upload_folder, exist_ok=True)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    
    # Register user loader
    from app.models import User
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register blueprints
    from app.auth.routes import auth_bp
    from app.dashboard.routes import dashboard_bp
    from app.products.routes import products_bp
    from app.sales.routes import sales_bp
    from app.purchases.routes import purchases_bp
    from app.customers.routes import customers_bp
    from app.suppliers.routes import suppliers_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(purchases_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(suppliers_bp)

    @app.route('/')
    def home():
        """Send guests to login and signed-in users to dashboard."""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard.index'))
        return redirect(url_for('auth.login'))

    @app.route('/favicon.ico')
    def favicon():
        """Serve a lightweight favicon from the static folder."""
        return redirect(url_for('static', filename='favicon.svg'))

    @app.context_processor
    def inject_api_token():
        return {"api_token": get_api_token()}

    @app.template_filter("money")
    def money_filter(cents):
        return f"{from_cents(cents):.2f}"
    
    # Development-only safety: normalize roles (schema should be managed via migrations).
    with app.app_context():
        _normalize_user_roles()
        _bootstrap_initial_users()
    
    return app


def _normalize_user_roles():
    """Keep only supported roles in runtime database."""
    inspector = inspect(db.engine)
    if not inspector.has_table('users'):
        return

    db.session.execute(
        text("UPDATE users SET role = 'staff' WHERE role IS NULL OR role NOT IN ('admin','staff')")
    )
    db.session.commit()


def _bootstrap_initial_users():
    """Create initial admin/staff users from environment variables on first deploy."""
    inspector = inspect(db.engine)
    if not inspector.has_table('users'):
        return

    from app.models import User

    admin_email = os.environ.get('BOOTSTRAP_ADMIN_EMAIL') or os.environ.get('ADMIN_EMAIL')
    admin_password = os.environ.get('BOOTSTRAP_ADMIN_PASSWORD') or os.environ.get('ADMIN_PASSWORD')
    staff_email = os.environ.get('BOOTSTRAP_STAFF_EMAIL') or os.environ.get('STAFF_EMAIL')
    staff_password = os.environ.get('BOOTSTRAP_STAFF_PASSWORD') or os.environ.get('STAFF_PASSWORD')

    created = []

    if admin_email and admin_password and not User.query.filter_by(email=admin_email).first():
        admin = User(name='Admin User', email=admin_email, role='admin')
        admin.set_password(admin_password)
        db.session.add(admin)
        created.append(admin_email)

    if staff_email and staff_password and not User.query.filter_by(email=staff_email).first():
        staff = User(name='Staff Member', email=staff_email, role='staff')
        staff.set_password(staff_password)
        db.session.add(staff)
        created.append(staff_email)

    if created:
        db.session.commit()
        print(f"Bootstrapped users: {', '.join(created)}")
