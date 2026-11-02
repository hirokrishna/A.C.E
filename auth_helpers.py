from functools import wraps
from flask import session, redirect, url_for, abort, flash

# Decorator to check if user is logged in
def login_required(view_function):
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.', 'error')
            return redirect(url_for('auth.login'))
        return view_function(*args, **kwargs)
    return decorated_function

# Decorator to check user role
def role_required(*allowed_roles):
    def decorator(view_function):
        @wraps(view_function)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in first.', 'error')
                return redirect(url_for('auth.login'))
            
            user_role = session.get('role')
            if user_role not in allowed_roles:
                abort(403)
                
            return view_function(*args, **kwargs)
        return decorated_function
    return decorator

