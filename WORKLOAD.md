# Project Workload & 5-Member Team Allocation

This document outlines the module division across all 5 team members for the presentation, viva, and code walkthrough. 

For the complete, beginner-friendly line-by-line explanation and viva preparation script, please refer to:
👉 **[TEAM_PROJECT_GUIDE.md](file:///c:/Users/patha/OneDrive/Desktop/student%20prediction%20system/TEAM_PROJECT_GUIDE.md)**

---

## 5-Member Module Division Summary

### Member 1: Database Architecture, Configuration & System Setup
- **Role:** Database Designer & Systems Engineer
- **Core Files:** `models.py`, `config.py`, `migrate.py`, `seed.py`, `app.py`, `helpers.py`
- **Key Deliverables:**
  - Relational database schema with 14 tables (Users, Students, Subjects, Marks, Attendance, Details, Predictions, ModelInfo, Announcements, Notifications, Remarks, SemesterResults, PasswordResetRequests, ActivityLog).
  - Safe database migration script (`migrate.py`) for SQLite & PostgreSQL preserving live data.
  - Seeding engine (`seed.py`) with 30 students, mentors, past semester SGPA, and announcements.
  - Flask app factory, blueprint routing, and unread notification context processor.

### Member 2: Dual Machine Learning Engine (Classification & Regression)
- **Role:** Data Scientist & AI Specialist
- **Core Files:** `ml/make_dataset.py`, `ml/train_model.py`, `ml/predictor.py`, `data/students_dataset.csv`, `ml/model.pkl`, `ml/model_reg.pkl`
- **Key Deliverables:**
  - Synthetic dataset generation (1,000 records) with realistic noise and academic weights.
  - Classifier comparison: Logistic Regression, Decision Tree, Random Forest (evaluated by F1-Score & Accuracy).
  - Regressor comparison: Linear Regression, Random Forest Regressor (evaluated by R² Score & MAE).
  - Model serialization to `.pkl` files and tracking metrics, confusion matrix, and feature importances.
  - Inference engine returning pass probability, risk level, predicted percentage, and letter grade.
  - Final exam target calculator logic: `required_final_marks(internal, target)`.

### Member 3: Authentication, Security, Role Control & Audit Logs
- **Role:** Security & User Management Specialist
- **Core Files:** `auth_helpers.py`, `routes/auth_routes.py`, `routes/admin_routes.py`, `templates/login.html`, `templates/register.html`, `templates/forgot_password.html`, `templates/change_password.html`, `templates/admin_users.html`, `templates/activity_log.html`
- **Key Deliverables:**
  - 3-tier user role authentication (Admin, Teacher, Student) using PBKDF2:SHA-256 password hashing.
  - Session-based access control with `@login_required` and `@role_required` decorators.
  - Forgot password request workflow and administrative one-time temporary password generation.
  - Activity audit log (`/admin/activity`) recording all system operations with filtering and pagination.
  - Notification management (in-app alerts, unread counts, and mark-as-read handlers).

### Member 4: Academic Tracking, Predictions, Interventions & Bulk Import
- **Role:** Academic Engine & Business Logic Specialist
- **Core Files:** `academic_helpers.py`, `routes/academic_routes.py`, `routes/predict_routes.py`, `templates/semester_results.html`, `templates/target_calculator.html`, `templates/attendance_shortage.html`, `templates/bulk_import.html`, `templates/what_if.html`, `templates/prediction_history.html`
- **Key Deliverables:**
  - Academic metrics calculation (attendance %, internal exam averages, subject performance tagging).
  - Semester results management (SGPA and backlogs for Semesters 1 to 8).
  - Attendance shortage detection (<75% overall; <65% red, 65–75% orange) with automatic alerts.
  - Target marks calculator UI for students.
  - Bulk CSV import for students and marks with row-by-row validation and error logs.
  - Single student prediction, batch prediction ("Predict All"), and What-If simulation.

### Member 5: Teacher Mentorship, Student Portal, UI & Frontend Visualization
- **Role:** User Experience, Mentorship & Visualization Specialist
- **Core Files:** `routes/student_routes.py`, `routes/dashboard_routes.py`, `static/style.css`, `templates/base.html`, `templates/dashboard.html`, `templates/student_dashboard.html`, `templates/student_detail.html`, `templates/my_students.html`, `templates/interventions.html`, `templates/announcements.html`, `templates/ranking.html`, `templates/student_report.html`, `templates/student_profile.html`
- **Key Deliverables:**
  - Mentor-mentee pairing and dedicated teacher portal (`/my-students`).
  - Teacher counseling remarks workflow with action plans and student visibility control.
  - Interventions dashboard for high-risk students.
  - Personalized student dashboard with class rank, weak subjects alert, and campus notices.
  - Printable official student report card with clean `@media print` CSS styling.
  - Interactive Chart.js visualizations (SGPA line chart, pass probability trend, feature importance).
  - Plain, clean beginner CSS styling under 200 lines adhering to university project guidelines.
