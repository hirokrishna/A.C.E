import os
import json
import pandas as pd
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from models import db, User, ModelInfo, PasswordResetRequest, ActivityLog
from auth_helpers import role_required
from ml.train_model import train_and_save_model, FEATURE_COLUMNS
from ml.predictor import reload_model
from helpers import log_action

# Blueprint for admin actions
admin_bp = Blueprint('admin', __name__)

# List all users and pending password reset requests
@admin_bp.route('/admin/users')
@role_required('admin')
def user_list():
    users = User.query.order_by(User.id.asc()).all()
    pending_requests = PasswordResetRequest.query.filter_by(status='pending').order_by(PasswordResetRequest.created_at.desc()).all()
    return render_template('admin_users.html', users=users, pending_requests=pending_requests)

# Add new user (teacher or admin)
@admin_bp.route('/admin/users/add', methods=['GET', 'POST'])
@role_required('admin')
def add_user():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        role = request.form.get('role', 'teacher')

        if not name or not email or not password:
            flash('All fields are required.', 'error')
            return render_template('admin_user_form.html', name=name, email=email, role=role)

        existing = User.query.filter_by(email=email).first()
        if existing:
            flash('Email already exists.', 'error')
            return render_template('admin_user_form.html', name=name, role=role)

        new_user = User(
            name=name,
            email=email,
            password_hash=generate_password_hash(password),
            role=role
        )
        db.session.add(new_user)
        db.session.commit()

        log_action(session.get('user_id'), "ADD_USER", f"Admin created user {name} ({email}) as {role}")
        flash(f'User {name} added successfully as {role}.', 'success')
        return redirect(url_for('admin.user_list'))

    return render_template('admin_user_form.html')

# Reset user password to default
@admin_bp.route('/admin/users/<int:user_id>/reset', methods=['POST'])
@role_required('admin')
def reset_password(user_id):
    user = User.query.get_or_404(user_id)
    default_pass = "Reset@123"
    user.password_hash = generate_password_hash(default_pass)
    db.session.commit()

    log_action(session.get('user_id'), "RESET_PASSWORD", f"Password reset for {user.email}")
    flash(f"Password for {user.name} ({user.email}) has been reset to '{default_pass}'.", 'success')
    return redirect(url_for('admin.user_list'))

# Resolve pending password reset request
@admin_bp.route('/admin/reset-requests/<int:req_id>/resolve', methods=['POST'])
@role_required('admin')
def resolve_reset_request(req_id):
    req_entry = PasswordResetRequest.query.get_or_404(req_id)
    user = User.query.filter_by(email=req_entry.email).first()

    temp_password = "TempPass@2026"
    if user:
        user.password_hash = generate_password_hash(temp_password)

    req_entry.status = 'done'
    db.session.commit()

    log_action(session.get('user_id'), "RESOLVE_PASSWORD_REQUEST", f"Resolved password reset for {req_entry.email}")
    flash(f"Password request for {req_entry.email} resolved. Temporary password: '{temp_password}' (Share with user once).", 'success')
    return redirect(url_for('admin.user_list'))

# Delete user
@admin_bp.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@role_required('admin')
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if user.id == session.get('user_id'):
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('admin.user_list'))

    user_email = user.email
    db.session.delete(user)
    db.session.commit()

    log_action(session.get('user_id'), "DELETE_USER", f"Deleted user {user_email}")
    flash(f'User {user_email} deleted successfully.', 'success')
    return redirect(url_for('admin.user_list'))

# Activity Log page: /admin/activity
@admin_bp.route('/admin/activity')
@role_required('admin')
def activity_log():
    action_filter = request.args.get('action', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 10

    query = ActivityLog.query
    if action_filter:
        query = query.filter_by(action=action_filter)

    query = query.order_by(ActivityLog.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # Distinct actions for dropdown
    actions = [r[0] for r in db.session.query(ActivityLog.action).distinct().all()]

    return render_template(
        'activity_log.html',
        pagination=pagination,
        logs=pagination.items,
        actions=actions,
        selected_action=action_filter
    )

# Model management and retraining page
@admin_bp.route('/admin/model')
@role_required('admin')
def model_management():
    # Active models
    active_clf = ModelInfo.query.filter_by(model_type='classifier', is_active=True).first()
    active_reg = ModelInfo.query.filter_by(model_type='regressor', is_active=True).first()

    # All compared models (from most recent run)
    all_classifiers = ModelInfo.query.filter_by(model_type='classifier').order_by(ModelInfo.id.desc()).limit(3).all()
    all_regressors = ModelInfo.query.filter_by(model_type='regressor').order_by(ModelInfo.id.desc()).limit(2).all()

    # Parse confusion matrix
    cm_matrix = None
    if active_clf and active_clf.confusion_matrix:
        try:
            cm_matrix = json.loads(active_clf.confusion_matrix)
        except Exception:
            cm_matrix = None

    # Parse feature importances
    feature_importances = None
    if active_clf and active_clf.feature_importance:
        try:
            feature_importances = json.loads(active_clf.feature_importance)
        except Exception:
            feature_importances = None

    return render_template(
        'admin_model.html',
        active_clf=active_clf,
        active_reg=active_reg,
        classifiers=all_classifiers,
        regressors=all_regressors,
        cm=cm_matrix,
        features=feature_importances
    )

# Retrain model action
@admin_bp.route('/admin/model/retrain', methods=['POST'])
@role_required('admin')
def retrain_model():
    dataset_file = request.files.get('dataset_file')
    csv_path = 'data/students_dataset.csv'

    if dataset_file and dataset_file.filename != '':
        filename = secure_filename(dataset_file.filename)
        if not filename.endswith('.csv'):
            flash('Only CSV files are allowed for training data.', 'error')
            return redirect(url_for('admin.model_management'))

        temp_path = os.path.join('data', 'temp_upload.csv')
        dataset_file.save(temp_path)

        try:
            df = pd.read_csv(temp_path)
            required = set(FEATURE_COLUMNS + ['result', 'final_percentage'])
            if not required.issubset(df.columns):
                missing = required - set(df.columns)
                os.remove(temp_path)
                flash(f"Uploaded CSV is missing columns: {', '.join(missing)}", 'error')
                return redirect(url_for('admin.model_management'))
            
            os.replace(temp_path, csv_path)
            flash(f"Uploaded new dataset with {len(df)} rows.", 'success')
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            flash(f"Failed to read CSV: {str(e)}", 'error')
            return redirect(url_for('admin.model_management'))

    try:
        results = train_and_save_model(csv_path)
        reload_model()
        log_action(session.get('user_id'), "RETRAIN_MODEL", f"Retrained models. Best Clf: {results['best_classifier']} (F1: {results['f1']:.4f}), Best Reg: {results['best_regressor']} (R2: {results['r2']:.4f})")
        flash(f"Models retrained successfully! Classifier: {results['best_classifier']} (F1: {results['f1']:.4f}), Regressor: {results['best_regressor']} (R2: {results['r2']:.4f})", 'success')
    except Exception as e:
        flash(f"Training failed: {str(e)}", 'error')

    return redirect(url_for('admin.model_management'))
