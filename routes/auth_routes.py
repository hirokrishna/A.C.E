from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Student, PasswordResetRequest, Notification
from auth_helpers import login_required
from helpers import log_action, add_notification

# Blueprint for authentication
auth_bp = Blueprint('auth', __name__)

# Home route: redirects by role
@auth_bp.route('/')
def index():
    if 'user_id' in session:
        role = session.get('role')
        if role in ['admin', 'teacher']:
            return redirect(url_for('dashboard.dashboard_home'))
        elif role == 'student':
            return redirect(url_for('dashboard.student_dashboard'))
    return redirect(url_for('auth.login'))

# Login page and submission
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Please enter both email and password.', 'error')
            return render_template('login.html', email=email)

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['user_name'] = user.name
            session['email'] = user.email
            session['role'] = user.role

            if user.role == 'student':
                student = Student.query.filter_by(user_id=user.id).first()
                if student:
                    session['student_id'] = student.id

            log_action(user.id, "LOGIN", f"User {user.email} logged in ({user.role})")

            if user.role == 'student':
                return redirect(url_for('dashboard.student_dashboard'))
            else:
                return redirect(url_for('dashboard.dashboard_home'))
        else:
            flash('Invalid email or password', 'error')
            return render_template('login.html', email=email)

    return render_template('login.html')

# Forgot password request: /forgot-password
@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()

        if not email:
            flash('Please enter your email address.', 'error')
            return render_template('forgot_password.html')

        # Save pending request
        req_entry = PasswordResetRequest(email=email, status='pending')
        db.session.add(req_entry)
        db.session.commit()

        # Notify all admins
        admins = User.query.filter_by(role='admin').all()
        for a in admins:
            add_notification(a.id, f"Password reset requested for {email}", "/admin/users")

        flash("If an account with that email exists, a password reset request has been submitted to the administrator.", "success")
        return redirect(url_for('auth.login'))

    return render_template('forgot_password.html')

# Register page for students
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        roll_no = request.form.get('roll_no', '').strip().upper()
        branch = request.form.get('branch', '').strip()
        semester = request.form.get('semester', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not name or not email or not roll_no or not password:
            flash('All required fields must be filled.', 'error')
            return render_template('register.html', name=name, email=email, roll_no=roll_no, branch=branch, semester=semester)

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register.html', name=name, email=email, roll_no=roll_no, branch=branch, semester=semester)

        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return render_template('register.html', name=name, email=email, roll_no=roll_no, branch=branch, semester=semester)

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email is already registered. Please login.', 'error')
            return render_template('register.html', name=name, roll_no=roll_no, branch=branch, semester=semester)

        student = Student.query.filter_by(roll_no=roll_no).first()

        if student:
            if student.user_id is not None:
                flash('This roll number is already linked to an account.', 'error')
                return render_template('register.html', name=name, email=email, branch=branch, semester=semester)
            
            new_user = User(
                name=name,
                email=email,
                password_hash=generate_password_hash(password),
                role='student'
            )
            db.session.add(new_user)
            db.session.flush()

            student.user_id = new_user.id
            if email:
                student.email = email
            db.session.commit()
        else:
            new_user = User(
                name=name,
                email=email,
                password_hash=generate_password_hash(password),
                role='student'
            )
            db.session.add(new_user)
            db.session.flush()

            sem_int = int(semester) if semester.isdigit() else 1
            new_student = Student(
                user_id=new_user.id,
                roll_no=roll_no,
                name=name,
                email=email,
                branch=branch if branch else 'IT',
                semester=sem_int,
                section='A'
            )
            db.session.add(new_student)
            db.session.commit()

        log_action(new_user.id, "REGISTER", f"New student registered: {name} ({roll_no})")
        flash('Account created successfully. Please login.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')

# Logout
@auth_bp.route('/logout')
def logout():
    uid = session.get('user_id')
    if uid:
        log_action(uid, "LOGOUT", "User logged out")
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))

# Change password for logged in user
@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        user = User.query.get(session.get('user_id'))
        if not user:
            session.clear()
            return redirect(url_for('auth.login'))

        if not check_password_hash(user.password_hash, current_password):
            flash('Current password is incorrect.', 'error')
            return render_template('change_password.html')

        if new_password != confirm_password:
            flash('New passwords do not match.', 'error')
            return render_template('change_password.html')

        if len(new_password) < 6:
            flash('New password must be at least 6 characters.', 'error')
            return render_template('change_password.html')

        user.password_hash = generate_password_hash(new_password)
        db.session.commit()

        log_action(user.id, "CHANGE_PASSWORD", "User updated password")
        flash('Password changed successfully.', 'success')
        if session.get('role') == 'student':
            return redirect(url_for('dashboard.student_dashboard'))
        else:
            return redirect(url_for('dashboard.dashboard_home'))

    return render_template('change_password.html')

# Notifications page: /notifications
@auth_bp.route('/notifications')
@login_required
def notification_list():
    user_id = session.get('user_id')
    page = request.args.get('page', 1, type=int)
    per_page = 10

    query = Notification.query.filter_by(user_id=user_id).order_by(
        Notification.is_read.asc(),
        Notification.created_at.desc()
    )
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template('notifications.html', pagination=pagination, notifications=pagination.items)

# Mark notification read and open link
@auth_bp.route('/notifications/<int:notif_id>/open')
@login_required
def open_notification(notif_id):
    user_id = session.get('user_id')
    notif = Notification.query.get_or_404(notif_id)

    if notif.user_id != user_id:
        abort(403)

    notif.is_read = True
    db.session.commit()

    if notif.link:
        return redirect(notif.link)
    return redirect(url_for('auth.notification_list'))

# Mark all notifications as read
@auth_bp.route('/notifications/read-all', methods=['POST'])
@login_required
def read_all_notifications():
    user_id = session.get('user_id')
    Notification.query.filter_by(user_id=user_id, is_read=False).update({'is_read': True})
    db.session.commit()
    flash('All notifications marked as read.', 'success')
    return redirect(url_for('auth.notification_list'))
