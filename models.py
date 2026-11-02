from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

# Initialize SQLAlchemy
db = SQLAlchemy()

# User table for authentication (Admin, Teacher, Student)
class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(10), nullable=False) # 'admin', 'teacher', 'student'
    created_at = db.Column(db.DateTime, default=datetime.now)

    # Relationships
    student_profile = db.relationship('Student', foreign_keys='Student.user_id', backref='user_account', uselist=False)
    predictions_made = db.relationship('Prediction', backref='creator', lazy=True)


# Student profile table
class Student(db.Model):
    __tablename__ = 'students'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, unique=True)
    roll_no = db.Column(db.String(30), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(15), nullable=True)
    mentor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    branch = db.Column(db.String(50), nullable=True)
    semester = db.Column(db.Integer, nullable=True)
    section = db.Column(db.String(5), nullable=True)
    gender = db.Column(db.String(10), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    # Relationships
    mentor = db.relationship('User', foreign_keys=[mentor_id], backref='mentored_students')
    marks = db.relationship('Mark', backref='student', cascade='all, delete-orphan', lazy=True)
    attendance_records = db.relationship('Attendance', backref='student', cascade='all, delete-orphan', lazy=True)
    details = db.relationship('StudentDetail', backref='student', cascade='all, delete-orphan', uselist=False)
    predictions = db.relationship('Prediction', backref='student', cascade='all, delete-orphan', lazy=True)
    semester_results = db.relationship('SemesterResult', backref='student', cascade='all, delete-orphan', lazy=True)
    remarks = db.relationship('Remark', backref='student', cascade='all, delete-orphan', lazy=True)


# Subjects table
class Subject(db.Model):
    __tablename__ = 'subjects'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    semester = db.Column(db.Integer, nullable=True)
    branch = db.Column(db.String(50), nullable=True)

    # Relationships
    marks = db.relationship('Mark', backref='subject', lazy=True)
    attendance_records = db.relationship('Attendance', backref='subject', lazy=True)


# Marks table
class Mark(db.Model):
    __tablename__ = 'marks'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False, index=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    exam_type = db.Column(db.String(20), nullable=False) # 'mid1', 'mid2', 'assignment', 'final'
    marks_obtained = db.Column(db.Float, nullable=False)
    max_marks = db.Column(db.Float, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('student_id', 'subject_id', 'exam_type', name='uq_student_subject_exam'),
    )


# Attendance table
class Attendance(db.Model):
    __tablename__ = 'attendance'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False, index=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    total_classes = db.Column(db.Integer, nullable=False, default=0)
    attended_classes = db.Column(db.Integer, nullable=False, default=0)

    __table_args__ = (
        db.UniqueConstraint('student_id', 'subject_id', name='uq_student_subject_attendance'),
    )


# Extra academic details for prediction
class StudentDetail(db.Model):
    __tablename__ = 'student_details'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False, unique=True)
    prev_percentage = db.Column(db.Float, nullable=False, default=0.0)
    study_hours = db.Column(db.Float, nullable=False, default=0.0)
    assignment_pct = db.Column(db.Float, nullable=False, default=0.0)
    backlogs = db.Column(db.Integer, nullable=False, default=0)


# Prediction history table
class Prediction(db.Model):
    __tablename__ = 'predictions'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
    predicted_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    attendance_pct = db.Column(db.Float, nullable=False)
    internal_marks_pct = db.Column(db.Float, nullable=False)
    prev_percentage = db.Column(db.Float, nullable=False)
    study_hours = db.Column(db.Float, nullable=False)
    assignment_pct = db.Column(db.Float, nullable=False)
    backlogs = db.Column(db.Integer, nullable=False)
    result = db.Column(db.String(5), nullable=False) # 'PASS' or 'FAIL'
    pass_probability = db.Column(db.Float, nullable=False)
    predicted_percentage = db.Column(db.Float, nullable=True)
    predicted_grade = db.Column(db.String(3), nullable=True)
    risk_level = db.Column(db.String(10), nullable=False) # 'Low', 'Medium', 'High'
    reasons = db.Column(db.Text, nullable=True) # reasons joined by ';'
    model_id = db.Column(db.Integer, db.ForeignKey('model_info.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    __table_args__ = (
        db.Index('idx_student_created', 'student_id', 'created_at'),
    )


# Machine learning model metadata
class ModelInfo(db.Model):
    __tablename__ = 'model_info'

    id = db.Column(db.Integer, primary_key=True)
    model_name = db.Column(db.String(50), nullable=False)
    model_type = db.Column(db.String(15), default='classifier') # 'classifier' or 'regressor'
    accuracy = db.Column(db.Float, nullable=True)
    precision_score = db.Column(db.Float, nullable=True)
    recall_score = db.Column(db.Float, nullable=True)
    f1_score = db.Column(db.Float, nullable=True)
    mae = db.Column(db.Float, nullable=True)
    r2_score = db.Column(db.Float, nullable=True)
    feature_importance = db.Column(db.Text, nullable=True) # JSON format
    confusion_matrix = db.Column(db.String(100), nullable=True)
    dataset_rows = db.Column(db.Integer, nullable=False)
    trained_at = db.Column(db.DateTime, default=datetime.now)
    is_active = db.Column(db.Boolean, default=True)

    predictions = db.relationship('Prediction', backref='model_used', lazy=True)


# Announcements table
class Announcement(db.Model):
    __tablename__ = 'announcements'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    posted_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    target_branch = db.Column(db.String(50), nullable=True) # e.g. 'IT', or empty for all
    target_semester = db.Column(db.Integer, nullable=True) # e.g. 5, or None for all
    created_at = db.Column(db.DateTime, default=datetime.now)

    poster = db.relationship('User', backref='announcements')


# Notifications table
class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(200), nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    recipient = db.relationship('User', backref='notifications')


# Teacher remarks table
class Remark(db.Model):
    __tablename__ = 'remarks'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    remark_text = db.Column(db.Text, nullable=False)
    action_plan = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(30), default='Not Contacted') # 'Not Contacted', 'Counselled', 'Improving', 'Resolved'
    visible_to_student = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    teacher = db.relationship('User', backref='remarks_given')


# Semester past results table
class SemesterResult(db.Model):
    __tablename__ = 'semester_results'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    sgpa = db.Column(db.Float, nullable=False)
    backlogs = db.Column(db.Integer, default=0)

    __table_args__ = (
        db.UniqueConstraint('student_id', 'semester', name='uq_student_semester'),
    )


# Password reset requests table
class PasswordResetRequest(db.Model):
    __tablename__ = 'password_reset_requests'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(20), default='pending') # 'pending', 'done'
    created_at = db.Column(db.DateTime, default=datetime.now)


# Activity log table
class ActivityLog(db.Model):
    __tablename__ = 'activity_log'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    user = db.relationship('User', backref='activities')
