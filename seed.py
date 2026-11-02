import random
from werkzeug.security import generate_password_hash
from app import app
from models import (
    db, User, Student, Subject, Mark, Attendance, StudentDetail, ModelInfo,
    Announcement, Notification, Remark, SemesterResult, PasswordResetRequest
)

# Seed the database with sample data
def seed_database():
    with app.app_context():
        # Drop all tables and recreate them clean
        db.drop_all()
        db.create_all()

        print("Tables created.")

        # 1. Create Admin user
        admin_user = User(
            name="College Admin",
            email="admin@college.com",
            password_hash=generate_password_hash("Admin@123"),
            role="admin"
        )
        db.session.add(admin_user)

        # 2. Create 2 Teacher users
        teacher1 = User(
            name="Prof. Sharma",
            email="teacher1@college.com",
            password_hash=generate_password_hash("Teacher@123"),
            role="teacher"
        )
        teacher2 = User(
            name="Prof. Verma",
            email="teacher2@college.com",
            password_hash=generate_password_hash("Teacher@123"),
            role="teacher"
        )
        db.session.add(teacher1)
        db.session.add(teacher2)
        db.session.commit()

        print("Admin and Teachers created.")

        # 3. Create 6 Subjects for Semester 5 IT
        subjects_data = [
            ("IT501", "Software Engineering", 5, "IT"),
            ("IT502", "Computer Networks", 5, "IT"),
            ("IT503", "Database Management Systems", 5, "IT"),
            ("IT504", "Web Technologies", 5, "IT"),
            ("IT505", "Operating Systems", 5, "IT"),
            ("IT506", "Artificial Intelligence", 5, "IT")
        ]

        created_subjects = []
        for code, name, sem, branch in subjects_data:
            subject = Subject(code=code, name=name, semester=sem, branch=branch)
            db.session.add(subject)
            created_subjects.append(subject)

        db.session.commit()
        print("6 Subjects created.")

        # 4. Create 30 Sample Students
        first_names = [
            "Aarav", "Aditi", "Amit", "Ananya", "Bhavya", 
            "Chetan", "Deepak", "Divya", "Gaurav", "Harsh", 
            "Ishaan", "Kavita", "Karan", "Manish", "Neha", 
            "Nikhil", "Pooja", "Pranav", "Priya", "Rahul", 
            "Rohan", "Riya", "Sahil", "Sanjay", "Sneha", 
            "Tanvi", "Varun", "Vikas", "Yash", "Zoya"
        ]

        # Use seed for repeatable data
        random.seed(42)

        created_students = []

        for i in range(30):
            roll_number = f"IT2026{i+1:03d}"
            student_name = f"{first_names[i]} Patel"
            student_email = f"student{i+1}@college.com"
            gender = "Female" if i % 2 == 1 else "Male"
            phone = f"9876543{i:03d}"
            mentor = teacher1 if i % 2 == 0 else teacher2

            # Create student user login for first 3 students
            user_account_id = None
            if i < 3:
                student_user = User(
                    name=student_name,
                    email=student_email,
                    password_hash=generate_password_hash("Student@123"),
                    role="student"
                )
                db.session.add(student_user)
                db.session.flush()
                user_account_id = student_user.id

            student = Student(
                user_id=user_account_id,
                roll_no=roll_number,
                name=student_name,
                email=student_email,
                phone=phone,
                mentor_id=mentor.id,
                branch="IT",
                semester=5,
                section="A",
                gender=gender
            )
            db.session.add(student)
            db.session.flush()
            created_students.append(student)

            # Create varying profiles: top students, average students, weak students
            if i < 8:
                # Weak / High risk profile
                att_min, att_max = 20, 28
                m1_min, m1_max = 7, 14
                m2_min, m2_max = 8, 13
                asg_min, asg_max = 8, 14
                fin_min, fin_max = 25, 45
                prev_pct = round(random.uniform(42.0, 56.0), 1)
                study_hrs = round(random.uniform(4.0, 8.0), 1)
                asg_pct = round(random.uniform(45.0, 65.0), 1)
                backlog_count = random.choice([2, 3, 4])
                base_sgpa = 5.2
            elif i < 20:
                # Average / Medium risk profile
                att_min, att_max = 28, 34
                m1_min, m1_max = 14, 19
                m2_min, m2_max = 13, 18
                asg_min, asg_max = 13, 17
                fin_min, fin_max = 50, 68
                prev_pct = round(random.uniform(58.0, 72.0), 1)
                study_hrs = round(random.uniform(9.0, 15.0), 1)
                asg_pct = round(random.uniform(68.0, 82.0), 1)
                backlog_count = random.choice([0, 1])
                base_sgpa = 6.8
            else:
                # Strong / Low risk profile
                att_min, att_max = 35, 39
                m1_min, m1_max = 19, 24
                m2_min, m2_max = 20, 25
                asg_min, asg_max = 17, 20
                fin_min, fin_max = 70, 92
                prev_pct = round(random.uniform(75.0, 92.0), 1)
                study_hrs = round(random.uniform(16.0, 26.0), 1)
                asg_pct = round(random.uniform(85.0, 98.0), 1)
                backlog_count = 0
                base_sgpa = 8.5

            # Add marks and attendance for each subject
            for subject in created_subjects:
                db.session.add(Mark(student_id=student.id, subject_id=subject.id, exam_type="mid1", marks_obtained=random.randint(m1_min, m1_max), max_marks=25.0))
                db.session.add(Mark(student_id=student.id, subject_id=subject.id, exam_type="mid2", marks_obtained=random.randint(m2_min, m2_max), max_marks=25.0))
                db.session.add(Mark(student_id=student.id, subject_id=subject.id, exam_type="assignment", marks_obtained=random.randint(asg_min, asg_max), max_marks=20.0))
                db.session.add(Mark(student_id=student.id, subject_id=subject.id, exam_type="final", marks_obtained=random.randint(fin_min, fin_max), max_marks=100.0))

                db.session.add(Attendance(
                    student_id=student.id,
                    subject_id=subject.id,
                    total_classes=40,
                    attended_classes=random.randint(att_min, att_max)
                ))

            # Add student extra details
            db.session.add(StudentDetail(
                student_id=student.id,
                prev_percentage=prev_pct,
                study_hours=study_hrs,
                assignment_pct=asg_pct,
                backlogs=backlog_count
            ))

            # Add Semester results for semesters 1 to 4
            for sem_num in range(1, 5):
                sem_sgpa = round(min(10.0, max(3.5, base_sgpa + random.uniform(-0.4, 0.4))), 2)
                sem_backlogs = 0 if base_sgpa >= 6.5 else random.choice([0, 1, 2])
                db.session.add(SemesterResult(
                    student_id=student.id,
                    semester=sem_num,
                    sgpa=sem_sgpa,
                    backlogs=sem_backlogs
                ))

        db.session.commit()
        print("30 Students with marks, attendance, details, mentors and semester results created.")

        # 5. Add 3 Announcements
        announcements = [
            Announcement(
                title="Mid-Term Exam Schedule Announced",
                message="Mid 2 examinations for semester 5 will commence from next Monday. Timetable is on the department noticeboard.",
                posted_by=admin_user.id,
                target_branch=None,
                target_semester=None
            ),
            Announcement(
                title="Remedial Classes for IT Department",
                message="Special remedial coaching for Computer Networks and DBMS is scheduled every Saturday from 10:00 AM to 1:00 PM.",
                posted_by=teacher1.id,
                target_branch="IT",
                target_semester=5
            ),
            Announcement(
                title="Assignment Submission Deadline",
                message="All Semester 5 students must submit their Web Technology project assignments before Friday 5:00 PM.",
                posted_by=teacher2.id,
                target_branch="IT",
                target_semester=5
            )
        ]
        for a in announcements:
            db.session.add(a)

        # 6. Add Remarks
        remarks = [
            Remark(
                student_id=created_students[0].id,
                teacher_id=teacher1.id,
                remark_text="Student has low attendance and struggled in Mid 1 test.",
                action_plan="1-on-1 weekly counseling and paired with peer study partner.",
                status="Counselled",
                visible_to_student=True
            ),
            Remark(
                student_id=created_students[1].id,
                teacher_id=teacher2.id,
                remark_text="Programming assignment submissions are delayed.",
                action_plan="Extra practice lab hours allotted.",
                status="Improving",
                visible_to_student=False
            ),
            Remark(
                student_id=created_students[2].id,
                teacher_id=teacher1.id,
                remark_text="Excellent consistency and active participation in class discussions.",
                action_plan="Continue mentoring for competitive programming.",
                status="Resolved",
                visible_to_student=True
            )
        ]
        for r in remarks:
            db.session.add(r)

        # 7. Add Notifications
        notifications = [
            Notification(
                user_id=created_students[0].user_id,
                message="Warning: Your attendance in Computer Networks is below 75%.",
                link="/my-dashboard",
                is_read=False
            ),
            Notification(
                user_id=teacher1.id,
                message="High Risk Alert: Student Aarav Patel (IT2026001) is flagged as high risk.",
                link=f"/students/{created_students[0].id}",
                is_read=False
            ),
            Notification(
                user_id=admin_user.id,
                message="Password reset request submitted for student2@college.com",
                link="/admin/users",
                is_read=False
            )
        ]
        for n in notifications:
            db.session.add(n)

        # 8. Add 1 Pending Password Reset Request
        pw_request = PasswordResetRequest(
            email="student2@college.com",
            status="pending"
        )
        db.session.add(pw_request)

        # 9. Initial ModelInfo baseline
        initial_model = ModelInfo(
            model_name="RandomForest",
            model_type="classifier",
            accuracy=0.865,
            precision_score=0.852,
            recall_score=0.880,
            f1_score=0.866,
            dataset_rows=1000,
            is_active=True
        )
        db.session.add(initial_model)
        db.session.commit()

        print("Announcements, remarks, notifications, and password requests seeded.")
        print("Database seeded successfully!")

if __name__ == '__main__':
    seed_database()
