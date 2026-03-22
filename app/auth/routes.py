"""
Authentication routes
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models import User
from app.auth.forms import LoginForm, RegistrationForm, ChangePasswordForm
from app.utils.security import rate_limit_check, record_failed_login, clear_failed_login

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        ip = request.headers.get('X-Forwarded-For', request.remote_addr or 'unknown')
        if not rate_limit_check(ip):
            flash('Too many login attempts. Please wait and try again.', 'danger')
            return redirect(url_for('auth.login'))

        user = User.query.filter_by(email=form.email.data).first()
        
        if user is None or not user.check_password(form.password.data):
            record_failed_login(ip)
            flash('Invalid email or password', 'danger')
            return redirect(url_for('auth.login'))
        
        if not user.is_active:
            flash('Your account has been disabled', 'danger')
            return redirect(url_for('auth.login'))

        if user.role not in ['admin', 'staff']:
            flash('This account role is not allowed to access the system.', 'danger')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=True)
        clear_failed_login(ip)
        next_page = request.args.get('next')
        
        if next_page and next_page.startswith('/'):
            return redirect(next_page)
        
        return redirect(url_for('dashboard.index'))
    
    return render_template('auth/login.html', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    """Admin-only staff account creation."""
    if not current_user.is_admin():
        flash('Only admin can create staff accounts.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            name=form.name.data,
            email=form.email.data,
            role='staff'
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Staff account created successfully.', 'success')
        return redirect(url_for('dashboard.index'))
    
    return render_template('auth/register.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change user password"""
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect', 'danger')
            return redirect(url_for('auth.change_password'))
        
        current_user.set_password(form.new_password.data)
        db.session.commit()
        
        flash('Your password has been changed successfully.', 'success')
        return redirect(url_for('dashboard.index'))
    
    return render_template('auth/change_password.html', form=form)


@auth_bp.route('/profile')
@login_required
def profile():
    """User profile page"""
    return render_template('auth/profile.html', user=current_user)
