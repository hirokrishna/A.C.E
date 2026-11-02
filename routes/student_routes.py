from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort, jsonify
from models import db, Student, Subject, Mark, Attendance, StudentDetail, Prediction, SemesterResult, Remark, User
from auth_helpers import login_required, role_required
from academic_helpers import (
    calculate_attendance_pct, calculate_internal_pct, 
    calculate_student_rank, calculate_subject_analysis
)
from helpers import log_action, add_notification

# Blueprint for student management
student_bp = Blueprint('student', __name__)

# List students with search, filters, sorting and pagination
@student_bp.route('/students')
@role_required('admin', 'teacher')
def student_list():
    search_query = request.args.get('search', '').strip()
    branch_filter = request.args.get('branch', '').strip()
    semester_filter = request.args.get('semester', '').strip()
    page = request.args.get('page', 1, type=int)
    sort_by = request.args.get('sort', 'roll_no').strip()
    order = request.args.get('order', 'asc').strip().lower()
    per_page = 10

    query = Student.query

    # Apply search filter
    if search_query:
        query = query.filter(
            (Student.name.ilike(f'%{search_query}%')) | 
            (Student.roll_no.ilike(f'%{search_query}%'))
        )

    # Apply branch filter
    if branch_filter:
        query = query.filter_by(branch=branch_filter)

    # Apply semester filter
    if semester_filter and semester_filter.isdigit():
        query = query.filter_by(semester=int(semester_filter))

    # Apply sorting
    sort_col = getattr(Student, sort_by, Student.roll_no)
    if order == 'desc':
        query = query.order_by(sort_col.desc())
    else:
        query = query.order_by(sort_col.asc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    students = pagination.items

    return render_template(
        'students_list.html',
        students=students,
        pagination=pagination,
        search=search_query,
        branch=branch_filter,
        semester=semester_filter,
        sort=sort_by,
        order=order
    )

# Add student form
@student_bp.route('/students/add', methods=['GET', 'POST'])
@role_required('admin', 'teacher')
def add_student():
    teachers = User.query.filter_by(role='teacher').all()

    if request.method == 'POST':
        roll_no = request.form.get('roll_no', '').strip().upper()
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        mentor_id = request.form.get('mentor_id', '').strip()
        branch = request.form.get('branch', '').strip()
        semester = request.form.get('semester', '').strip()
        section = request.form.get('section', 'A').strip().upper()
        gender = request.form.get('gender', 'Male').strip()

        if not roll_no or not name:
            flash('Roll number and Name are required.', 'error')
            return render_template('student_form.html', roll_no=roll_no, name=name, email=email, phone=phone, branch=branch, semester=semester, section=section, gender=gender, teachers=teachers, is_edit=False)

        existing_student = Student.query.filter_by(roll_no=roll_no).first()
        if existing_student:
            flash('A student with this roll number already exists.', 'error')
            return render_template('student_form.html', roll_no=roll_no, name=name, email=email, phone=phone, branch=branch, semester=semester, section=section, gender=gender, teachers=teachers, is_edit=False)

        sem_int = int(semester) if semester.isdigit() else 1
        m_id = int(mentor_id) if mentor_id.isdigit() else None

        new_student = Student(
            roll_no=roll_no,
            name=name,
            email=email if email else None,
            phone=phone if phone else None,
            mentor_id=m_id,
            branch=branch if branch else 'IT',
            semester=sem_int,
            section=section,
            gender=gender
        )
        db.session.add(new_student)
        db.session.commit()

        log_action(session.get('user_id'), "ADD_STUDENT", f"Added student {name} ({roll_no})")
        flash(f'Student {name} ({roll_no}) added successfully.', 'success')
        return redirect(url_for('student.student_detail', student_id=new_student.id))

    return render_template('student_form.html', teachers=teachers, is_edit=False)

# View single student details
@student_bp.route('/students/<int:student_id>')
@login_required
def student_detail(student_id):
    student = Student.query.get_or_404(student_id)

    # Student role can only view own record
    if session.get('role') == 'student' and student.user_id != session.get('user_id'):
        abort(403)

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

    # Class rank
    rank, total_classmates = calculate_student_rank(student)

    # Subject-wise status analysis
    subject_analysis, weak_subjects = calculate_subject_analysis(student)

    # Latest prediction
    latest_prediction = Prediction.query.filter_by(student_id=student.id).order_by(Prediction.created_at.desc()).first()

    # Semester SGPA results
    sem_results = SemesterResult.query.filter_by(student_id=student.id).order_by(SemesterResult.semester.asc()).all()

    # Teacher Remarks (students only see visible_to_student==True)
    if session.get('role') == 'student':
        remarks_list = [r for r in student.remarks if r.visible_to_student]
    else:
        remarks_list = student.remarks

    # Teachers list for mentor assignment if admin
    teachers = User.query.filter_by(role='teacher').all() if session.get('role') == 'admin' else []

    return render_template(
        'student_detail.html',
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
        sem_results=sem_results,
        remarks_list=remarks_list,
        teachers=teachers,
        details=student.details,
        latest_prediction=latest_prediction
    )

# Edit student form
@student_bp.route('/students/<int:student_id>/edit', methods=['GET', 'POST'])
@role_required('admin', 'teacher')
def edit_student(student_id):
    student = Student.query.get_or_404(student_id)
    teachers = User.query.filter_by(role='teacher').all()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        branch = request.form.get('branch', '').strip()
        semester = request.form.get('semester', '').strip()
        section = request.form.get('section', 'A').strip().upper()
        gender = request.form.get('gender', 'Male').strip()

        if not name:
            flash('Name is required.', 'error')
            return render_template('student_form.html', student=student, teachers=teachers, is_edit=True)

        student.name = name
        student.email = email if email else None
        student.phone = phone if phone else None
        student.branch = branch
        student.semester = int(semester) if semester.isdigit() else student.semester
        student.section = section
        student.gender = gender

        # Admin can update mentor
        if session.get('role') == 'admin':
            mentor_id_val = request.form.get('mentor_id', '').strip()
            student.mentor_id = int(mentor_id_val) if mentor_id_val.isdigit() else None

        db.session.commit()
        log_action(session.get('user_id'), "EDIT_STUDENT", f"Updated student {student.name} ({student.roll_no})")
        flash('Student details updated successfully.', 'success')
        return redirect(url_for('student.student_detail', student_id=student.id))

    return render_template('student_form.html', student=student, teachers=teachers, is_edit=True)

# Admin mentor assignment shortcut: POST /students/<id>/mentor
@student_bp.route('/students/<int:student_id>/mentor', methods=['POST'])
@role_required('admin')
def assign_mentor(student_id):
    student = Student.query.get_or_404(student_id)
    mentor_id_str = request.form.get('mentor_id', '').strip()
    student.mentor_id = int(mentor_id_str) if mentor_id_str.isdigit() else None
    db.session.commit()
    flash(f"Mentor updated for {student.name}.", "success")
    return redirect(url_for('student.student_detail', student_id=student.id))

# Delete student
@student_bp.route('/students/<int:student_id>/delete', methods=['POST'])
@role_required('admin', 'teacher')
def delete_student(student_id):
    student = Student.query.get_or_404(student_id)
    student_name = student.name
    roll = student.roll_no
    db.session.delete(student)
    db.session.commit()

    log_action(session.get('user_id'), "DELETE_STUDENT", f"Deleted student {student_name} ({roll})")
    flash(f'Student {student_name} deleted successfully.', 'success')
    return redirect(url_for('student.student_list'))

# Prediction trend JSON route: /api/student/<id>/trend
@student_bp.route('/api/student/<int:student_id>/trend')
@login_required
def student_trend_api(student_id):
    student = Student.query.get_or_404(student_id)

    if session.get('role') == 'student' and student.user_id != session.get('user_id'):
        abort(403)

    history = Prediction.query.filter_by(student_id=student.id).order_by(Prediction.created_at.asc()).all()
    dates = []
    probabilities = []
    percentages = []

    for p in history:
        dates.append(p.created_at.strftime('%Y-%m-%d'))
        probabilities.append(round(p.pass_probability * 100.0, 1))
        percentages.append(round(p.predicted_percentage, 1) if p.predicted_percentage is not None else round(p.pass_probability * 100.0, 1))

    return jsonify({
        'dates': dates,
        'probabilities': probabilities,
        'percentages': percentages
    })

# Class Ranking page: /ranking
@student_bp.route('/ranking')
@role_required('admin', 'teacher')
def class_ranking():
    branch_filter = request.args.get('branch', 'IT').strip()
    semester_filter = request.args.get('semester', '5').strip()
    page = request.args.get('page', 1, type=int)

    query = Student.query
    if branch_filter:
        query = query.filter_by(branch=branch_filter)
    if semester_filter and semester_filter.isdigit():
        query = query.filter_by(semester=int(semester_filter))

    students = query.all()

    ranked_list = []
    for s in students:
        int_pct = calculate_internal_pct(s.id)
        att_pct = calculate_attendance_pct(s.id)
        ranked_list.append({
            'student': s,
            'internal_pct': int_pct,
            'attendance_pct': att_pct
        })

    # Sort descending by internal marks %
    ranked_list.sort(key=lambda x: x['internal_pct'], reverse=True)

    # Assign ranks
    for idx, item in enumerate(ranked_list):
        item['rank'] = idx + 1

    top_10 = ranked_list[:10]

    # Pagination: 10 per page
    per_page = 10
    total_count = len(ranked_list)
    start_idx = (page - 1) * per_page
    paginated_items = ranked_list[start_idx:start_idx + per_page]
    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1

    return render_template(
        'ranking.html',
        top_10=top_10,
        records=paginated_items,
        page=page,
        total_pages=total_pages,
        total_count=total_count,
        branch=branch_filter,
        semester=semester_filter
    )

# Printable Student Report: /students/<id>/report
@student_bp.route('/students/<int:student_id>/report')
@login_required
def student_report(student_id):
    student = Student.query.get_or_404(student_id)

    if session.get('role') == 'student' and student.user_id != session.get('user_id'):
        abort(403)

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
    latest_prediction = Prediction.query.filter_by(student_id=student.id).order_by(Prediction.created_at.desc()).first()
    rank, total_classmates = calculate_student_rank(student)
    subject_analysis, weak_subjects = calculate_subject_analysis(student)
    sem_results = SemesterResult.query.filter_by(student_id=student.id).order_by(SemesterResult.semester.asc()).all()

    # Remarks
    if session.get('role') == 'student':
        visible_remarks = [r for r in student.remarks if r.visible_to_student]
    else:
        visible_remarks = student.remarks

    return render_template(
        'student_report.html',
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
        sem_results=sem_results,
        latest_prediction=latest_prediction,
        remarks=visible_remarks,
        details=student.details
    )

# Student personal profile edit: /profile
@student_bp.route('/profile', methods=['GET', 'POST'])
@role_required('student')
def student_profile():
    student = Student.query.filter_by(user_id=session.get('user_id')).first()
    if not student:
        flash("Student profile not found.", "error")
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()

        if not name:
            flash('Name is required.', 'error')
            return render_template('student_profile.html', student=student)

        student.name = name
        student.email = email if email else None
        student.phone = phone if phone else None

        # Also update linked User record
        if student.user_account:
            student.user_account.name = name
            if email:
                student.user_account.email = email
            session['user_name'] = name

        db.session.commit()
        log_action(session.get('user_id'), "PROFILE_UPDATE", f"Student {student.name} updated own profile")
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('dashboard.student_dashboard'))

    return render_template('student_profile.html', student=student)

# Teacher page: /my-students (assigned mentee students)
@student_bp.route('/my-students')
@role_required('teacher')
def my_students():
    teacher_id = session.get('user_id')
    students = Student.query.filter_by(mentor_id=teacher_id).order_by(Student.roll_no.asc()).all()

    mentee_records = []
    for s in students:
        latest_pred = Prediction.query.filter_by(student_id=s.id).order_by(Prediction.created_at.desc()).first()
        latest_remark = Remark.query.filter_by(student_id=s.id).order_by(Remark.created_at.desc()).first()
        mentee_records.append({
            'student': s,
            'attendance_pct': calculate_attendance_pct(s.id),
            'internal_pct': calculate_internal_pct(s.id),
            'prediction': latest_pred,
            'remark': latest_remark
        })

    return render_template('my_students.html', records=mentee_records)

# Add Teacher Remark: POST /students/<id>/remarks/add
@student_bp.route('/students/<int:student_id>/remarks/add', methods=['POST'])
@role_required('admin', 'teacher')
def add_remark(student_id):
    student = Student.query.get_or_404(student_id)
    remark_text = request.form.get('remark_text', '').strip()
    action_plan = request.form.get('action_plan', '').strip()
    status = request.form.get('status', 'Not Contacted')
    visible_to_student = bool(request.form.get('visible_to_student'))

    if not remark_text:
        flash('Remark text is required.', 'error')
        return redirect(url_for('student.student_detail', student_id=student.id))

    new_remark = Remark(
        student_id=student.id,
        teacher_id=session.get('user_id'),
        remark_text=remark_text,
        action_plan=action_plan if action_plan else None,
        status=status,
        visible_to_student=visible_to_student
    )
    db.session.add(new_remark)
    db.session.commit()

    # If visible to student, send notification
    if visible_to_student and student.user_id:
        add_notification(
            student.user_id,
            f"New academic advisory remark added by {session.get('user_name', 'Teacher')}.",
            "/my-dashboard"
        )

    log_action(session.get('user_id'), "ADD_REMARK", f"Remark added for {student.name}: status '{status}'")
    flash('Remark saved successfully.', 'success')
    return redirect(url_for('student.student_detail', student_id=student.id))

# Intervention List: /interventions
@student_bp.route('/interventions')
@role_required('admin', 'teacher')
def intervention_list():
    students = Student.query.all()
    high_risk_list = []

    for s in students:
        latest_pred = Prediction.query.filter_by(student_id=s.id).order_by(Prediction.created_at.desc()).first()
        if latest_pred and latest_pred.risk_level == 'High':
            latest_remark = Remark.query.filter_by(student_id=s.id).order_by(Remark.created_at.desc()).first()
            high_risk_list.append({
                'student': s,
                'attendance_pct': calculate_attendance_pct(s.id),
                'internal_pct': calculate_internal_pct(s.id),
                'prediction': latest_pred,
                'remark': latest_remark
            })

    # Sort by lowest pass probability
    high_risk_list.sort(key=lambda x: x['prediction'].pass_probability)

    return render_template('interventions.html', records=high_risk_list)
