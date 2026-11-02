from flask import request, session
from models import db, Notification, ActivityLog

# Add a notification for a user
def add_notification(user_id, message, link=None):
    if not user_id:
        return
    notif = Notification(
        user_id=user_id,
        message=message,
        link=link,
        is_read=False
    )
    db.session.add(notif)
    db.session.commit()

# Log system or user actions
def log_action(user_id, action, details=None):
    log_entry = ActivityLog(
        user_id=user_id,
        action=action,
        details=details
    )
    db.session.add(log_entry)
    db.session.commit()

# Helper for pagination and sorting queries
def paginate_and_sort(query, model_class, default_sort='id', allowed_sort_cols=None, default_order='asc', per_page=10):
    page = request.args.get('page', 1, type=int)
    sort_col_name = request.args.get('sort', default_sort).strip()
    order = request.args.get('order', default_order).strip().lower()

    if allowed_sort_cols and sort_col_name not in allowed_sort_cols:
        sort_col_name = default_sort

    sort_col = getattr(model_class, sort_col_name, getattr(model_class, default_sort))

    if order == 'desc':
        query = query.order_by(sort_col.desc())
    else:
        query = query.order_by(sort_col.asc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return pagination, sort_col_name, order

# Context processor for unread notifications count in navigation bar
def inject_unread_notifications():
    user_id = session.get('user_id')
    if not user_id:
        return {'unread_notif_count': 0}
    
    count = Notification.query.filter_by(user_id=user_id, is_read=False).count()
    return {'unread_notif_count': count}

