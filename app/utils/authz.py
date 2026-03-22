"""
Authorization decorators.
"""
from __future__ import annotations

from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user


def admin_required(f):
    """Decorator to require admin role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin():
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function


def staff_required(f):
    """Decorator to require staff role (admin or staff)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_staff():
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function
