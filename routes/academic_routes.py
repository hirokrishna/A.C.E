import io
import csv
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from models import db, Student, Subject, Mark, Attendance, StudentDetail, SemesterResult
from auth_helpers import login_required, role_required
from academic_helpers import calculate_attendance_pct, calculate_internal_pct
from ml.predictor import required_final_marks
from helpers import add_notification, log_action

# Blueprint for academic data management
academic_bp = Blueprint('academic', __name__)

# List subjects and add subject form (admin only)
@academic_bp.route('/subjects', methods=['GET', 'POST'])
@role_required('admin')
def subject_list():
    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        name = request.form.get('name', '').strip()
        semester = request.form.get('semester', '').strip()
        branch = request.form.get('branch', 'IT').strip().upper()

        if not code or not name:
            flash('Subject code and name are required.', 'error')
            return redirect(url_for('academic.subject_list'))

        existing = Subject.query.filter_by(code=code).first()
        if existing:
            flash('Subject code already exists.', 'error')
            return redirect(url_for('academic.subject_list'))

        sem_int = int(semester) if semester.isdigit() else 5
        subject = Subject(code=code, name=name, semester=sem_int, branch=branch)
        db.session.add(subject)
        db.session.commit()

        flash(f'Subject {code} - {name} added.', 'success')
        return redirect(url_for('academic.subject_list'))

    subjects = Subject.query.order_by(Subject.semester.asc(), Subject.code.asc()).all()
    return render_template('subjects.html', subjects=subjects)

# Delete subject (admin only)
@academic_bp.route('/subjects/<int:subject_id>/delete', methods=['POST'])
@role_required('admin')
def delete_subject(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    subject_code = subject.code
    db.session.delete(subject)
    db.session.commit()

    flash(f'Subject {subject_code} deleted.', 'success')
    return redirect(url_for('academic.subject_list'))

# Enter / edit marks for a student
@academic_bp.route('/students/<int:student_id>/marks', methods=['GET', 'POST'])
@role_required('admin', 'teacher')
def enter_marks(student_id):
    student = Student.query.get_or_404(student_id)
    subjects = Subject.query.filter_by(semester=student.semester).all()
    if not subjects:
        subjects = Subject.query.all()

    if request.method == 'POST':
        exam_max = {
            'mid1': 25.0,
            'mid2': 25.0,
            'assignment': 20.0,
            'final': 100.0
        }

        try:
            for subject in subjects:
                for exam in ['mid1', 'mid2', 'assignment', 'final']:
                    field_name = f'mark_{subject.id}_{exam}'
                    mark_val_str = request.form.get(field_name, '').strip()

                    if mark_val_str != '':
                        obtained = float(mark_val_str)
                        max_allowed = exam_max[exam]

                        if obtained < 0 or obtained > max_allowed:
                            flash(f'Marks for {subject.code} ({exam}) must be between 0 and {max_allowed}.', 'error')
                            return redirect(url_for('academic.enter_marks', student_id=student.id))

                        mark_record = Mark.query.filter_by(
                            student_id=student.id,
                            subject_id=subject.id,
                            exam_type=exam
                        ).first()

                        if not mark_record:
                            mark_record = Mark(
                                student_id=student.id,
                                subject_id=subject.id,
                                exam_type=exam,
                                marks_obtained=obtained,
                                max_marks=max_allowed
                            )
                            db.session.add(mark_record)
                        else:
                            mark_record.marks_obtained = obtained
                            mark_record.max_marks = max_allowed

            db.session.commit()
            flash('Marks saved successfully.', 'success')
            return redirect(url_for('student.student_detail', student_id=student.id))

        except ValueError:
            flash('Please enter valid numeric values for marks.', 'error')
            return redirect(url_for('academic.enter_marks', student_id=student.id))

    marks_dict = {}
    for mark in student.marks:
        if mark.subject_id not in marks_dict:
            marks_dict[mark.subject_id] = {}
        marks_dict[mark.subject_id][mark.exam_type] = mark.marks_obtained

    return render_template('marks_form.html', student=student, subjects=subjects, marks_dict=marks_dict)

# Enter / edit attendance for a student
@academic_bp.route('/students/<int:student_id>/attendance', methods=['GET', 'POST'])
@role_required('admin', 'teacher')
def enter_attendance(student_id):
    student = Student.query.get_or_404(student_id)
    subjects = Subject.query.filter_by(semester=student.semester).all()
    if not subjects:
        subjects = Subject.query.all()

    if request.method == 'POST':
        try:
            for subject in subjects:
                total_classes_str = request.form.get(f'total_{subject.id}', '0').strip()
                attended_classes_str = request.form.get(f'attended_{subject.id}', '0').strip()

                total_classes = int(total_classes_str) if total_classes_str else 0
                attended_classes = int(attended_classes_str) if attended_classes_str else 0

                if total_classes < 0 or attended_classes < 0:
                    flash('Classes cannot be negative.', 'error')
                    return redirect(url_for('academic.enter_attendance', student_id=student.id))

                if attended_classes > total_classes:
                    flash(f'Attended classes cannot exceed total classes for {subject.code}.', 'error')
                    return redirect(url_for('academic.enter_attendance', student_id=student.id))

                att_record = Attendance.query.filter_by(
                    student_id=student.id,
                    subject_id=subject.id
                ).first()

                if not att_record:
                    att_record = Attendance(
                        student_id=student.id,
                        subject_id=subject.id,
                        total_classes=total_classes,
                        attended_classes=attended_classes
                    )
                    db.session.add(att_record)
                else:
                    att_record.total_classes = total_classes
                    att_record.attended_classes = attended_classes

            db.session.commit()

            # Check if overall attendance is below 75% and trigger student notification
            overall_pct = calculate_attendance_pct(student.id)
            if overall_pct < 75.0 and student.user_id:
                add_notification(
                    student.user_id,
                    f"Warning: Your overall attendance is currently {overall_pct}%, which is below the mandatory 75%.",
                    "/my-dashboard"
                )

            flash('Attendance saved successfully.', 'success')
            return redirect(url_for('student.student_detail', student_id=student.id))

        except ValueError:
            flash('Please enter valid integers for attendance.', 'error')
            return redirect(url_for('academic.enter_attendance', student_id=student.id))

    att_dict = {}
    for att in student.attendance_records:
        att_dict[att.subject_id] = {
            'total': att.total_classes,
            'attended': att.attended_classes
        }

    return render_template('attendance_form.html', student=student, subjects=subjects, att_dict=att_dict)

# Enter / edit student extra details
@academic_bp.route('/students/<int:student_id>/details', methods=['GET', 'POST'])
@role_required('admin', 'teacher')
def extra_details(student_id):
    student = Student.query.get_or_404(student_id)
    details = student.details

    if request.method == 'POST':
        try:
            prev_pct = float(request.form.get('prev_percentage', 0))
            study_hrs = float(request.form.get('study_hours', 0))
            asg_pct = float(request.form.get('assignment_pct', 0))
            backlogs = int(request.form.get('backlogs', 0))

            if prev_pct < 0 or prev_pct > 100:
                flash('Previous percentage must be between 0 and 100.', 'error')
                return render_template('details_form.html', student=student, details=details)

            if study_hrs < 0 or study_hrs > 80:
                flash('Weekly study hours must be between 0 and 80.', 'error')
                return render_template('details_form.html', student=student, details=details)

            if asg_pct < 0 or asg_pct > 100:
                flash('Assignment completion % must be between 0 and 100.', 'error')
                return render_template('details_form.html', student=student, details=details)

            if backlogs < 0:
                flash('Backlogs count cannot be negative.', 'error')
                return render_template('details_form.html', student=student, details=details)

            if not details:
                details = StudentDetail(
                    student_id=student.id,
                    prev_percentage=prev_pct,
                    study_hours=study_hrs,
                    assignment_pct=asg_pct,
                    backlogs=backlogs
                )
                db.session.add(details)
            else:
                details.prev_percentage = prev_pct
                details.study_hours = study_hrs
                details.assignment_pct = asg_pct
                details.backlogs = backlogs

            db.session.commit()
            flash('Extra academic details saved.', 'success')
            return redirect(url_for('student.student_detail', student_id=student.id))

        except ValueError:
            flash('Invalid number entered.', 'error')
            return render_template('details_form.html', student=student, details=details)

    return render_template('details_form.html', student=student, details=details)

# Manage semester SGPA and backlogs (semesters 1 to 8)
@academic_bp.route('/students/<int:student_id>/semesters', methods=['GET', 'POST'])
@login_required
def semester_results_page(student_id):
    student = Student.query.get_or_404(student_id)

    # Student can only view their own
    if session.get('role') == 'student' and student.user_id != session.get('user_id'):
        abort(403)

    if request.method == 'POST':
        if session.get('role') not in ['admin', 'teacher']:
            abort(403)

        try:
            for sem in range(1, 9):
                sgpa_str = request.form.get(f'sgpa_{sem}', '').strip()
                backlogs_str = request.form.get(f'backlogs_{sem}', '').strip()

                if sgpa_str != '':
                    sgpa_val = float(sgpa_str)
                    backlogs_val = int(backlogs_str) if backlogs_str else 0

                    if sgpa_val < 0.0 or sgpa_val > 10.0:
                        flash(f'SGPA for Semester {sem} must be between 0.0 and 10.0.', 'error')
                        return redirect(url_for('academic.semester_results_page', student_id=student.id))

                    if backlogs_val < 0:
                        flash(f'Backlogs for Semester {sem} cannot be negative.', 'error')
                        return redirect(url_for('academic.semester_results_page', student_id=student.id))

                    res = SemesterResult.query.filter_by(student_id=student.id, semester=sem).first()
                    if not res:
                        res = SemesterResult(student_id=student.id, semester=sem, sgpa=sgpa_val, backlogs=backlogs_val)
                        db.session.add(res)
                    else:
                        res.sgpa = sgpa_val
                        res.backlogs = backlogs_val

            db.session.commit()
            flash('Semester results saved successfully.', 'success')
            return redirect(url_for('student.student_detail', student_id=student.id))

        except ValueError:
            flash('Please enter valid numbers for SGPA and backlogs.', 'error')
            return redirect(url_for('academic.semester_results_page', student_id=student.id))

    # Pre-populate existing semester results
    sem_dict = {}
    for r in student.semester_results:
        sem_dict[r.semester] = {'sgpa': r.sgpa, 'backlogs': r.backlogs}

    return render_template('semester_results.html', student=student, sem_dict=sem_dict)

# Target calculator page: /students/<id>/target
@academic_bp.route('/students/<int:student_id>/target', methods=['GET', 'POST'])
@login_required
def target_calculator(student_id):
    student = Student.query.get_or_404(student_id)

    if session.get('role') == 'student' and student.user_id != session.get('user_id'):
        abort(403)

    internal_pct = calculate_internal_pct(student.id)
    target_pct = request.form.get('target_pct', '75.0') if request.method == 'POST' else '75.0'
    required_final = None
    status_message = None

    if request.method == 'POST':
        try:
            target_val = float(target_pct)
            if target_val < 0 or target_val > 100:
                flash('Target percentage must be between 0 and 100.', 'error')
            else:
                needed = required_final_marks(internal_pct, target_val)
                required_final = round(needed, 1)

                if required_final > 100.0:
                    status_message = f"Not possible (Requires {required_final}% in final exam, which exceeds 100%)."
                elif required_final <= 0.0:
                    status_message = f"Already achieved! Even scoring 0% in final exam satisfies this target."
                else:
                    status_message = f"You need at least {required_final}% in the final exam to achieve {target_val}% overall."
        except ValueError:
            flash('Please enter a valid numeric target percentage.', 'error')

    return render_template(
        'target_calculator.html',
        student=student,
        internal_pct=internal_pct,
        target_pct=target_pct,
        required_final=required_final,
        status_message=status_message
    )

# Attendance shortage page: students with attendance below 75%
@academic_bp.route('/attendance-shortage')
@role_required('admin', 'teacher')
def attendance_shortage():
    branch_filter = request.args.get('branch', '').strip()
    semester_filter = request.args.get('semester', '').strip()
    page = request.args.get('page', 1, type=int)
    sort_by = request.args.get('sort', 'attendance')
    order = request.args.get('order', 'asc')

    query = Student.query
    if branch_filter:
        query = query.filter_by(branch=branch_filter)
    if semester_filter and semester_filter.isdigit():
        query = query.filter_by(semester=int(semester_filter))

    all_students = query.all()
    shortage_list = []

    for s in all_students:
        att = calculate_attendance_pct(s.id)
        if att < 75.0:
            shortage_list.append({
                'student': s,
                'attendance_pct': att
            })

    # Sorting
    if sort_by == 'name':
        shortage_list.sort(key=lambda x: x['student'].name.lower(), reverse=(order == 'desc'))
    elif sort_by == 'roll_no':
        shortage_list.sort(key=lambda x: x['student'].roll_no, reverse=(order == 'desc'))
    else:
        shortage_list.sort(key=lambda x: x['attendance_pct'], reverse=(order == 'desc'))

    # Pagination: 10 per page
    per_page = 10
    total_count = len(shortage_list)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_items = shortage_list[start_idx:end_idx]
    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1

    return render_template(
        'attendance_shortage.html',
        records=paginated_items,
        page=page,
        total_pages=total_pages,
        total_count=total_count,
        branch=branch_filter,
        semester=semester_filter,
        sort=sort_by,
        order=order
    )

# Bulk import CSV page: /import
@academic_bp.route('/import', methods=['GET', 'POST'])
@role_required('admin', 'teacher')
def bulk_import():
    import_type = request.form.get('import_type')
    success_msg = None
    error_list = []

    if request.method == 'POST':
        csv_file = request.files.get('csv_file')
        if not csv_file or csv_file.filename == '':
            flash('Please select a CSV file to upload.', 'error')
            return redirect(url_for('academic.bulk_import'))

        try:
            stream = io.StringIO(csv_file.stream.read().decode("UTF-8"), newline=None)
            reader = csv.reader(stream)
            header = next(reader, None)

            if not header:
                flash('The uploaded file is empty.', 'error')
                return redirect(url_for('academic.bulk_import'))

            cleaned_header = [h.strip().lower() for h in header]

            if import_type == 'students':
                required_cols = ['roll_no', 'name', 'email', 'branch', 'semester', 'section', 'gender']
                if cleaned_header != required_cols:
                    flash(f"Invalid header for Students CSV. Required exact columns: {', '.join(required_cols)}", 'error')
                    return redirect(url_for('academic.bulk_import'))

                added_count = 0
                for row_idx, row in enumerate(reader, start=2):
                    if not row or not any(row):
                        continue
                    if len(row) < 7:
                        error_list.append(f"Row {row_idx}: Incomplete row, expected 7 columns.")
                        continue

                    roll_no = row[0].strip().upper()
                    name = row[1].strip()
                    email = row[2].strip().lower()
                    branch = row[3].strip()
                    sem_str = row[4].strip()
                    section = row[5].strip().upper()
                    gender = row[6].strip()

                    if not roll_no or not name:
                        error_list.append(f"Row {row_idx}: Roll number and Name are required.")
                        continue

                    if Student.query.filter_by(roll_no=roll_no).first():
                        error_list.append(f"Row {row_idx}: Student with roll number {roll_no} already exists.")
                        continue

                    sem_int = int(sem_str) if sem_str.isdigit() else 1
                    new_student = Student(
                        roll_no=roll_no,
                        name=name,
                        email=email if email else None,
                        branch=branch if branch else 'IT',
                        semester=sem_int,
                        section=section if section else 'A',
                        gender=gender if gender else 'Male'
                    )
                    db.session.add(new_student)
                    added_count += 1

                db.session.commit()
                log_action(session.get('user_id'), "BULK_IMPORT_STUDENTS", f"Imported {added_count} students. Errors: {len(error_list)}")
                flash(f"Students Import: {added_count} added, {len(error_list)} errors.", 'success' if added_count > 0 else 'error')

            elif import_type == 'marks':
                required_cols = ['roll_no', 'subject_code', 'exam_type', 'marks_obtained', 'max_marks']
                if cleaned_header != required_cols:
                    flash(f"Invalid header for Marks CSV. Required exact columns: {', '.join(required_cols)}", 'error')
                    return redirect(url_for('academic.bulk_import'))

                added_count = 0
                for row_idx, row in enumerate(reader, start=2):
                    if not row or not any(row):
                        continue
                    if len(row) < 5:
                        error_list.append(f"Row {row_idx}: Incomplete row, expected 5 columns.")
                        continue

                    roll_no = row[0].strip().upper()
                    subject_code = row[1].strip().upper()
                    exam_type = row[2].strip().lower()
                    marks_str = row[3].strip()
                    max_str = row[4].strip()

                    student = Student.query.filter_by(roll_no=roll_no).first()
                    if not student:
                        error_list.append(f"Row {row_idx}: Student with roll no '{roll_no}' not found.")
                        continue

                    subject = Subject.query.filter_by(code=subject_code).first()
                    if not subject:
                        error_list.append(f"Row {row_idx}: Subject code '{subject_code}' not found.")
                        continue

                    if exam_type not in ['mid1', 'mid2', 'assignment', 'final']:
                        error_list.append(f"Row {row_idx}: Invalid exam type '{exam_type}'. Must be mid1, mid2, assignment, or final.")
                        continue

                    try:
                        obtained = float(marks_str)
                        max_marks = float(max_str)
                        if obtained < 0 or max_marks <= 0 or obtained > max_marks:
                            error_list.append(f"Row {row_idx}: Marks must be >= 0 and <= max marks ({max_marks}).")
                            continue
                    except ValueError:
                        error_list.append(f"Row {row_idx}: Invalid numerical marks.")
                        continue

                    mark_record = Mark.query.filter_by(
                        student_id=student.id,
                        subject_id=subject.id,
                        exam_type=exam_type
                    ).first()

                    if not mark_record:
                        mark_record = Mark(
                            student_id=student.id,
                            subject_id=subject.id,
                            exam_type=exam_type,
                            marks_obtained=obtained,
                            max_marks=max_marks
                        )
                        db.session.add(mark_record)
                    else:
                        mark_record.marks_obtained = obtained
                        mark_record.max_marks = max_marks

                    added_count += 1

                db.session.commit()
                log_action(session.get('user_id'), "BULK_IMPORT_MARKS", f"Imported {added_count} mark records. Errors: {len(error_list)}")
                flash(f"Marks Import: {added_count} added/updated, {len(error_list)} errors.", 'success' if added_count > 0 else 'error')

        except Exception as e:
            flash(f"Failed to process CSV file: {str(e)}", 'error')

    return render_template('bulk_import.html', errors=error_list)
