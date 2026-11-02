from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from models import db, Student, StudentDetail, Prediction, ModelInfo
from auth_helpers import login_required, role_required
from academic_helpers import calculate_attendance_pct, calculate_internal_pct
from ml.predictor import predict_student
from helpers import add_notification, log_action

# Blueprint for prediction operations
predict_bp = Blueprint('predict', __name__)

# Run prediction for a single student
@predict_bp.route('/predict/<int:student_id>', methods=['POST'])
@role_required('admin', 'teacher')
def predict_one(student_id):
    student = Student.query.get_or_404(student_id)

    # Check for missing data
    missing_items = []

    if not student.attendance_records:
        missing_items.append("Attendance records")
    if not student.marks:
        missing_items.append("Marks records")
    if not student.details:
        missing_items.append("Academic Profile / Extra Details (study hours, backlogs, etc.)")

    if missing_items:
        flash(f"Cannot run prediction for {student.name}. Missing: {', '.join(missing_items)}.", 'error')
        return redirect(url_for('student.student_detail', student_id=student.id))

    # Calculate features
    attendance_pct = calculate_attendance_pct(student.id)
    internal_marks_pct = calculate_internal_pct(student.id)

    features = {
        'attendance_pct': attendance_pct,
        'internal_marks_pct': internal_marks_pct,
        'prev_percentage': student.details.prev_percentage,
        'study_hours': student.details.study_hours,
        'assignment_pct': student.details.assignment_pct,
        'backlogs': student.details.backlogs
    }

    # Run ML prediction
    try:
        prediction_result = predict_student(features)
    except Exception as e:
        flash(f"Prediction failed: {str(e)}", 'error')
        return redirect(url_for('student.student_detail', student_id=student.id))

    # Find active model id
    active_model = ModelInfo.query.filter_by(is_active=True).first()
    model_id = active_model.id if active_model else None

    # Save to predictions table
    new_prediction = Prediction(
        student_id=student.id,
        predicted_by=session.get('user_id'),
        attendance_pct=features['attendance_pct'],
        internal_marks_pct=features['internal_marks_pct'],
        prev_percentage=features['prev_percentage'],
        study_hours=features['study_hours'],
        assignment_pct=features['assignment_pct'],
        backlogs=features['backlogs'],
        result=prediction_result['result'],
        pass_probability=prediction_result['pass_probability'],
        predicted_percentage=prediction_result['predicted_percentage'],
        predicted_grade=prediction_result['predicted_grade'],
        risk_level=prediction_result['risk_level'],
        reasons='; '.join(prediction_result['reasons']),
        model_id=model_id
    )
    db.session.add(new_prediction)
    db.session.commit()

    # Notifications for High risk predictions
    if prediction_result['risk_level'] == 'High':
        if student.user_id:
            add_notification(student.user_id, "Academic Alert: High risk prediction received. Please meet your mentor.", "/my-dashboard")
        if student.mentor_id:
            add_notification(student.mentor_id, f"Alert: Student {student.name} ({student.roll_no}) predicted as High risk.", f"/students/{student.id}")

    # Log action
    log_action(session.get('user_id'), "PREDICTION", f"Predicted for {student.name} ({student.roll_no}): {prediction_result['result']} (Grade: {prediction_result['predicted_grade']})")

    flash(f"Prediction generated: {prediction_result['result']} ({prediction_result['predicted_percentage']}%, Grade: {prediction_result['predicted_grade']}, Risk: {prediction_result['risk_level']})", 'success')
    return redirect(url_for('student.student_detail', student_id=student.id))

# Run prediction for all students in the class
@predict_bp.route('/predict-all', methods=['POST'])
@role_required('admin', 'teacher')
def predict_all():
    students = Student.query.all()
    active_model = ModelInfo.query.filter_by(is_active=True).first()
    model_id = active_model.id if active_model else None

    predicted_count = 0
    skipped_count = 0

    for student in students:
        # Check if student has required data
        if not student.attendance_records or not student.marks or not student.details:
            skipped_count += 1
            continue

        attendance_pct = calculate_attendance_pct(student.id)
        internal_marks_pct = calculate_internal_pct(student.id)

        features = {
            'attendance_pct': attendance_pct,
            'internal_marks_pct': internal_marks_pct,
            'prev_percentage': student.details.prev_percentage,
            'study_hours': student.details.study_hours,
            'assignment_pct': student.details.assignment_pct,
            'backlogs': student.details.backlogs
        }

        try:
            res = predict_student(features)
            new_prediction = Prediction(
                student_id=student.id,
                predicted_by=session.get('user_id'),
                attendance_pct=features['attendance_pct'],
                internal_marks_pct=features['internal_marks_pct'],
                prev_percentage=features['prev_percentage'],
                study_hours=features['study_hours'],
                assignment_pct=features['assignment_pct'],
                backlogs=features['backlogs'],
                result=res['result'],
                pass_probability=res['pass_probability'],
                predicted_percentage=res['predicted_percentage'],
                predicted_grade=res['predicted_grade'],
                risk_level=res['risk_level'],
                reasons='; '.join(res['reasons']),
                model_id=model_id
            )
            db.session.add(new_prediction)
            predicted_count += 1

            # High risk notifications
            if res['risk_level'] == 'High':
                if student.user_id:
                    add_notification(student.user_id, "Academic Alert: High risk prediction received. Please meet your mentor.", "/my-dashboard")
                if student.mentor_id:
                    add_notification(student.mentor_id, f"Alert: Student {student.name} ({student.roll_no}) predicted as High risk.", f"/students/{student.id}")
        except Exception:
            skipped_count += 1

    db.session.commit()
    log_action(session.get('user_id'), "PREDICT_ALL", f"Class prediction run: {predicted_count} students evaluated.")
    flash(f"Class prediction completed: {predicted_count} students predicted, {skipped_count} skipped.", 'success')
    return redirect(url_for('dashboard.risk_list'))

# What-If manual simulation page
@predict_bp.route('/what-if', methods=['GET', 'POST'])
@role_required('admin', 'teacher')
def what_if_page():
    prediction_result = None
    form_data = {
        'attendance_pct': '75.0',
        'internal_marks_pct': '60.0',
        'prev_percentage': '65.0',
        'study_hours': '12.0',
        'assignment_pct': '80.0',
        'backlogs': '0'
    }

    if request.method == 'POST':
        try:
            form_data = {
                'attendance_pct': request.form.get('attendance_pct', '0'),
                'internal_marks_pct': request.form.get('internal_marks_pct', '0'),
                'prev_percentage': request.form.get('prev_percentage', '0'),
                'study_hours': request.form.get('study_hours', '0'),
                'assignment_pct': request.form.get('assignment_pct', '0'),
                'backlogs': request.form.get('backlogs', '0')
            }

            features = {
                'attendance_pct': float(form_data['attendance_pct']),
                'internal_marks_pct': float(form_data['internal_marks_pct']),
                'prev_percentage': float(form_data['prev_percentage']),
                'study_hours': float(form_data['study_hours']),
                'assignment_pct': float(form_data['assignment_pct']),
                'backlogs': int(form_data['backlogs'])
            }

            prediction_result = predict_student(features)

        except ValueError:
            flash("Please enter valid numeric values in all fields.", "error")

    return render_template('what_if.html', result=prediction_result, form_data=form_data)

# Prediction history for a student
@predict_bp.route('/students/<int:student_id>/history')
@login_required
def student_history(student_id):
    student = Student.query.get_or_404(student_id)

    # Role check
    if session.get('role') == 'student' and student.user_id != session.get('user_id'):
        abort(403)

    page = request.args.get('page', 1, type=int)
    sort_by = request.args.get('sort', 'created_at')
    order = request.args.get('order', 'desc')

    query = Prediction.query.filter_by(student_id=student.id)
    sort_col = getattr(Prediction, sort_by, Prediction.created_at)
    if order == 'asc':
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    pagination = query.paginate(page=page, per_page=10, error_out=False)
    return render_template(
        'prediction_history.html',
        student=student,
        pagination=pagination,
        history=pagination.items,
        sort=sort_by,
        order=order
    )

# Helper route for logged in student to open own history directly
@predict_bp.route('/history')
@predict_bp.route('/my-history')
@login_required
def student_history_own():
    if session.get('role') != 'student':
        return redirect(url_for('dashboard.dashboard_home'))

    student = Student.query.filter_by(user_id=session.get('user_id')).first()
    if not student:
        flash("Student profile not found.", "error")
        return redirect(url_for('auth.login'))

    return redirect(url_for('predict.student_history', student_id=student.id))
