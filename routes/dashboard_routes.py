import csv
import io
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, Response, flash, abort
from models import (
    db, Student, Subject, Prediction, StudentDetail, 
    Announcement, Notification, PasswordResetRequest, Remark
)
from auth_helpers import login_required, role_required
from academic_helpers import (
    calculate_attendance_pct, calculate_internal_pct,
    calculate_student_rank, calculate_subject_analysis
)
from ml.predictor import generate_suggestions
from helpers import log_action

# Blueprint for dashboards and reports
dashboard_bp = Blueprint('dashboard', __name__)

# Helper to gather students with their latest predictions
def get_students_with_predictions():
    students = Student.query.order_by(Student.roll_no.asc()).all()
    student_records = []

    for s in students:
        att_pct = calculate_attendance_pct(s.id)
        int_pct = calculate_internal_pct(s.id)
        latest_pred = Prediction.query.filter_by(student_id=s.id).order_by(Prediction.created_at.desc()).first()
        has_data = bool(s.attendance_records and s.marks and s.details)

        record = {
            'student': s,
            'attendance_pct': att_pct,
            'internal_pct': int_pct,
            'has_data': has_data,
            'prediction': latest_pred
        }
        student_records.append(record)

    return student_records

# Admin and Teacher main dashboard
@dashboard_bp.route('/dashboard')
@role_required('admin', 'teacher')
def dashboard_home():
    student_records = get_students_with_predictions()

    total_students = len(student_records)
    high_risk_count = 0
    medium_risk_count = 0
    low_risk_count = 0
    pass_count = 0
    fail_count = 0
    shortage_count = 0

    high_risk_students = []

    for item in student_records:
        if item['attendance_pct'] < 75.0:
            shortage_count += 1

        pred = item['prediction']
        if pred:
            if pred.risk_level == 'High':
                high_risk_count += 1
                high_risk_students.append(item)
            elif pred.risk_level == 'Medium':
                medium_risk_count += 1
            elif pred.risk_level == 'Low':
                low_risk_count += 1

            if pred.result == 'PASS':
                pass_count += 1
            else:
                fail_count += 1

    # Sort high risk students by lowest pass probability
    high_risk_students.sort(key=lambda x: x['prediction'].pass_probability)
    top_5_high_risk = high_risk_students[:5]

    # Additional dashboard cards
    pending_pw_count = PasswordResetRequest.query.filter_by(status='pending').count() if session.get('role') == 'admin' else 0
    unread_notifs = Notification.query.filter_by(user_id=session.get('user_id'), is_read=False).count()
    recent_announcements = Announcement.query.order_by(Announcement.created_at.desc()).limit(3).all()

    return render_template(
        'dashboard.html',
        total_students=total_students,
        high_risk_count=high_risk_count,
        medium_risk_count=medium_risk_count,
        low_risk_count=low_risk_count,
        pass_count=pass_count,
        fail_count=fail_count,
        shortage_count=shortage_count,
        pending_pw_count=pending_pw_count,
        unread_notifs=unread_notifs,
        recent_announcements=recent_announcements,
        top_5_high_risk=top_5_high_risk
    )

# JSON API route for Chart.js
@dashboard_bp.route('/api/chart-data')
@role_required('admin', 'teacher')
def chart_data():
    student_records = get_students_with_predictions()

    pass_count = 0
    fail_count = 0
    high_risk_count = 0
    medium_risk_count = 0
    low_risk_count = 0

    for item in student_records:
        pred = item['prediction']
        if pred:
            if pred.result == 'PASS':
                pass_count += 1
            else:
                fail_count += 1

            if pred.risk_level == 'High':
                high_risk_count += 1
            elif pred.risk_level == 'Medium':
                medium_risk_count += 1
            elif pred.risk_level == 'Low':
                low_risk_count += 1

    return jsonify({
        'pass_count': pass_count,
        'fail_count': fail_count,
        'high_risk_count': high_risk_count,
        'medium_risk_count': medium_risk_count,
        'low_risk_count': low_risk_count
    })

# Risk List page with sorting and pagination
@dashboard_bp.route('/risk-list')
@role_required('admin', 'teacher')
def risk_list():
    page = request.args.get('page', 1, type=int)
    sort_by = request.args.get('sort', 'risk')
    order = request.args.get('order', 'asc')

    student_records = get_students_with_predictions()

    high_list = []
    medium_list = []
    low_list = []
    unpredicted_list = []

    for item in student_records:
        pred = item['prediction']
        if pred:
            if pred.risk_level == 'High':
                high_list.append(item)
            elif pred.risk_level == 'Medium':
                medium_list.append(item)
            else:
                low_list.append(item)
        else:
            unpredicted_list.append(item)

    # Sort default: High -> Medium -> Low
    high_list.sort(key=lambda x: x['prediction'].pass_probability)
    medium_list.sort(key=lambda x: x['prediction'].pass_probability)
    low_list.sort(key=lambda x: x['prediction'].pass_probability)
    all_sorted = high_list + medium_list + low_list + unpredicted_list

    if sort_by == 'name':
        all_sorted.sort(key=lambda x: x['student'].name.lower(), reverse=(order == 'desc'))
    elif sort_by == 'roll_no':
        all_sorted.sort(key=lambda x: x['student'].roll_no, reverse=(order == 'desc'))
    elif sort_by == 'attendance':
        all_sorted.sort(key=lambda x: x['attendance_pct'], reverse=(order == 'desc'))
    elif sort_by == 'internal':
        all_sorted.sort(key=lambda x: x['internal_pct'], reverse=(order == 'desc'))
    elif sort_by == 'probability':
        all_sorted.sort(key=lambda x: (x['prediction'].pass_probability if x['prediction'] else -1), reverse=(order == 'desc'))

    # Pagination: 10 per page
    per_page = 10
    total_count = len(all_sorted)
    start_idx = (page - 1) * per_page
    paginated_items = all_sorted[start_idx:start_idx + per_page]
    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1

    return render_template(
        'risk_list.html',
        records=paginated_items,
        page=page,
        total_pages=total_pages,
        total_count=total_count,
        sort=sort_by,
        order=order
    )

# Export student predictions to CSV
@dashboard_bp.route('/export-csv')
@role_required('admin', 'teacher')
def export_csv():
    student_records = get_students_with_predictions()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        'Roll No',
        'Student Name',
        'Branch',
        'Semester',
        'Attendance %',
        'Internal Marks %',
        'Previous %',
        'Study Hours/Week',
        'Assignment %',
        'Backlogs',
        'Prediction Result',
        'Pass Probability %',
        'Predicted Score %',
        'Predicted Grade',
        'Risk Level',
        'Predicted Date'
    ])

    for item in student_records:
        s = item['student']
        d = s.details
        pred = item['prediction']

        writer.writerow([
            s.roll_no,
            s.name,
            s.branch,
            s.semester,
            item['attendance_pct'],
            item['internal_pct'],
            d.prev_percentage if d else '',
            d.study_hours if d else '',
            d.assignment_pct if d else '',
            d.backlogs if d else '',
            pred.result if pred else 'Not Predicted',
            round(pred.pass_probability * 100, 1) if pred else '',
            pred.predicted_percentage if (pred and pred.predicted_percentage is not None) else '',
            pred.predicted_grade if (pred and pred.predicted_grade) else '',
            pred.risk_level if pred else 'N/A',
            pred.created_at.strftime('%Y-%m-%d %H:%M') if pred else ''
        ])

    csv_data = output.getvalue()
    return Response(
        csv_data,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=students_risk_report.csv'}
    )

# Announcements page: /announcements
@dashboard_bp.route('/announcements', methods=['GET', 'POST'])
@role_required('admin', 'teacher')
def announcements():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        message = request.form.get('message', '').strip()
        target_branch = request.form.get('target_branch', '').strip()
        target_semester = request.form.get('target_semester', '').strip()

        if not title or not message:
            flash('Title and message are required.', 'error')
            return redirect(url_for('dashboard.announcements'))

        sem_val = int(target_semester) if target_semester.isdigit() else None
        branch_val = target_branch if target_branch else None

        new_ann = Announcement(
            title=title,
            message=message,
            posted_by=session.get('user_id'),
            target_branch=branch_val,
            target_semester=sem_val
        )
        db.session.add(new_ann)
        db.session.commit()

        log_action(session.get('user_id'), "POST_ANNOUNCEMENT", f"Posted announcement: {title}")
        flash('Announcement posted successfully.', 'success')
        return redirect(url_for('dashboard.announcements'))

    page = request.args.get('page', 1, type=int)
    pagination = Announcement.query.order_by(Announcement.created_at.desc()).paginate(page=page, per_page=10, error_out=False)
    return render_template('announcements.html', pagination=pagination, announcements=pagination.items)

# Delete announcement: POST /announcements/<id>/delete
@dashboard_bp.route('/announcements/<int:ann_id>/delete', methods=['POST'])
@role_required('admin', 'teacher')
def delete_announcement(ann_id):
    ann = Announcement.query.get_or_404(ann_id)
    user_id = session.get('user_id')
    user_role = session.get('role')

    # Can delete own announcement, or admin can delete any
    if user_role != 'admin' and ann.posted_by != user_id:
        flash('You can only delete announcements posted by yourself.', 'error')
        return redirect(url_for('dashboard.announcements'))

    ann_title = ann.title
    db.session.delete(ann)
    db.session.commit()

    log_action(user_id, "DELETE_ANNOUNCEMENT", f"Deleted announcement: {ann_title}")
    flash('Announcement deleted.', 'success')
    return redirect(url_for('dashboard.announcements'))

# Student personal dashboard
@dashboard_bp.route('/my-dashboard')
@role_required('student')
def student_dashboard():
    user_id = session.get('user_id')
    student = Student.query.filter_by(user_id=user_id).first()

    if not student:
        flash("Student profile not found. Please contact the administrator.", "error")
        return redirect(url_for('auth.login'))

    subjects = Subject.query.filter_by(semester=student.semester).all()
    if not subjects:
        subjects = Subject.query.all()

    student_marks = {}
    for mark in student.marks:
        if mark.subject_id not in student_marks:
            student_marks[mark.subject_id] = {}
        student_marks[mark.subject_id][mark.exam_type] = mark.marks_obtained

    attendance_dict = {}
    for att in student.attendance_records:
        pct = 0.0
        if att.total_classes > 0:
            pct = round((att.attended_classes / att.total_classes) * 100.0, 1)
        attendance_dict[att.subject_id] = {
            'total': att.total_classes,
            'attended': att.attended_classes,
            'pct': pct
        }

    overall_attendance = calculate_attendance_pct(student.id)
    overall_internal = calculate_internal_pct(student.id)
    rank, total_classmates = calculate_student_rank(student)
    subject_analysis, weak_subjects = calculate_subject_analysis(student)

    latest_prediction = Prediction.query.filter_by(student_id=student.id).order_by(Prediction.created_at.desc()).first()

    # Generate suggestions
    suggestions = []
    if student.details:
        features = {
            'attendance_pct': overall_attendance,
            'internal_marks_pct': overall_internal,
            'study_hours': student.details.study_hours,
            'assignment_pct': student.details.assignment_pct,
            'backlogs': student.details.backlogs
        }
        suggestions = generate_suggestions(features)

    # Announcements matching student's branch and semester
    matching_announcements = Announcement.query.filter(
        (Announcement.target_branch == None) | (Announcement.target_branch == student.branch),
        (Announcement.target_semester == None) | (Announcement.target_semester == student.semester)
    ).order_by(Announcement.created_at.desc()).all()

    # Visible remarks
    visible_remarks = [r for r in student.remarks if r.visible_to_student]

    return render_template(
        'student_dashboard.html',
        student=student,
        subjects=subjects,
        student_marks=student_marks,
        attendance_dict=attendance_dict,
        overall_attendance=overall_attendance,
        overall_internal=overall_internal,
        rank=rank,
        total_classmates=total_classmates,
        subject_analysis=subject_analysis,
        weak_subjects=weak_subjects,
        details=student.details,
        latest_prediction=latest_prediction,
        suggestions=suggestions,
        announcements=matching_announcements,
        remarks=visible_remarks
    )
