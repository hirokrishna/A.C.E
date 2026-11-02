from models import db, Student, Subject, Mark, Attendance

# Calculate total attendance percentage for a student across all subjects
def calculate_attendance_pct(student_id):
    records = Attendance.query.filter_by(student_id=student_id).all()
    if not records:
        return 0.0

    total_classes = 0
    attended_classes = 0

    for item in records:
        total_classes += item.total_classes
        attended_classes += item.attended_classes

    if total_classes == 0:
        return 0.0

    percentage = (attended_classes / total_classes) * 100.0
    return round(percentage, 2)

# Calculate internal marks percentage for a student (mid1, mid2, assignment)
def calculate_internal_pct(student_id):
    records = Mark.query.filter(
        Mark.student_id == student_id,
        Mark.exam_type.in_(['mid1', 'mid2', 'assignment'])
    ).all()

    if not records:
        return 0.0

    total_obtained = 0.0
    total_max = 0.0

    for item in records:
        total_obtained += item.marks_obtained
        total_max += item.max_marks

    if total_max == 0:
        return 0.0

    percentage = (total_obtained / total_max) * 100.0
    return round(percentage, 2)

# Calculate class rank within same branch and semester
def calculate_student_rank(student):
    if not student:
        return (1, 1)

    classmates = Student.query.filter_by(branch=student.branch, semester=student.semester).all()
    if not classmates:
        return (1, 1)

    scores = []
    for s in classmates:
        score = calculate_internal_pct(s.id)
        scores.append((s.id, score))

    # Sort descending by score
    scores.sort(key=lambda x: x[1], reverse=True)

    rank = 1
    for idx, (s_id, score) in enumerate(scores):
        if s_id == student.id:
            rank = idx + 1
            break

    return (rank, len(classmates))

# Subject-wise analysis: Subject | Marks % | Attendance % | Status
def calculate_subject_analysis(student):
    if not student:
        return [], []

    subjects = Subject.query.filter_by(semester=student.semester).all()
    if not subjects:
        subjects = Subject.query.all()

    analysis = []
    weak_subjects = []

    for sub in subjects:
        # Marks for internal exams
        marks = Mark.query.filter(
            Mark.student_id == student.id,
            Mark.subject_id == sub.id,
            Mark.exam_type.in_(['mid1', 'mid2', 'assignment'])
        ).all()

        total_obtained = sum(m.marks_obtained for m in marks)
        total_max = sum(m.max_marks for m in marks)
        marks_pct = round((total_obtained / total_max * 100.0), 1) if total_max > 0 else 0.0

        # Attendance
        att = Attendance.query.filter_by(student_id=student.id, subject_id=sub.id).first()
        att_pct = 0.0
        if att and att.total_classes > 0:
            att_pct = round((att.attended_classes / att.total_classes * 100.0), 1)

        # Status: Strong (>70), Average (50-70), Weak (<50)
        if marks_pct >= 70.0:
            status = 'Strong'
            color = 'green'
        elif marks_pct >= 50.0:
            status = 'Average'
            color = 'orange'
        else:
            status = 'Weak'
            color = 'red'
            weak_subjects.append(sub.name)

        analysis.append({
            'subject_code': sub.code,
            'subject_name': sub.name,
            'marks_pct': marks_pct,
            'attendance_pct': att_pct,
            'status': status,
            'color': color
        })

    return analysis, weak_subjects
