# A.C.E - Academic Counseling & Early-Warning System

A comprehensive web application developed for colleges and universities to identify weak and at-risk students early using Machine Learning. Teachers and administrators can track attendance, internal exam scores, past semester SGPA, and study habits, generate dual classification/regression predictions (Pass/Fail, Probability %, Final Score %, and Grade), assign faculty mentors, log intervention action plans, publish campus announcements, and export reports. Students can log in to view their performance predictions, improvement recommendations, and subject-wise status.

---

## Default Logins

| Role | Email | Password |
|---|---|---|
| **Admin** | `admin@college.com` | `Admin@123` |
| **Teacher 1** | `teacher1@college.com` | `Teacher@123` |
| **Teacher 2** | `teacher2@college.com` | `Teacher@123` |
| **Student 1** | `student1@college.com` | `Student@123` |
| **Student 2** | `student2@college.com` | `Student@123` |
| **Student 3** | `student3@college.com` | `Student@123` |

---

## Tech Stack (Free Tools Only)

- **Backend:** Python 3.11+, Flask, Flask-SQLAlchemy, Flask-WTF
- **Database:** SQLite (local development) / Supabase PostgreSQL (production)
- **Machine Learning:** scikit-learn, pandas, numpy, joblib (Dual Classifier + Regressor)
- **Frontend:** Plain HTML5, CSS3 (`style.css` plain beginner style), vanilla JavaScript
- **Data Visualization:** Chart.js (via CDN)
- **Production Server:** Gunicorn

---

## Setup & Running Instructions

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   Create a `.env` file (or use `.env.example`):
   ```env
   SECRET_KEY=college_secret_key_12345
   DATABASE_URL=sqlite:///local.db
   ```

3. **Apply database migrations (without data loss):**
   ```bash
   python migrate.py
   ```

4. **Generate training dataset (with final score %):**
   ```bash
   python ml/make_dataset.py
   ```

5. **Train classification and regression models:**
   ```bash
   python ml/train_model.py
   ```

6. **Seed sample data (announcements, remarks, mentors, semester results):**
   ```bash
   python seed.py
   ```

7. **Run local development server:**
   ```bash
   python app.py
   ```
   Open your browser at: **`http://127.0.0.1:5000`**

---

## New Features Overview

### 1. Dual Machine Learning Engine
- **Classifier:** Compares Logistic Regression, Decision Tree, and Random Forest (best by F1-score).
- **Regressor:** Compares Linear Regression and Random Forest Regressor (best by R² and MAE).
- **Predictions Output:** Pass/Fail, Pass Probability %, Predicted Final Score (0-100%), and Predicted Letter Grade (`A+`, `A`, `B`, `C`, `D`, `F`).
- **Feature Importance:** Random Forest weights visualized via Chart.js horizontal bar chart.
- **Confusion Matrix:** 2x2 contingency matrix displayed on the Admin Model page.

### 2. Academic Mentoring & Interventions
- **Faculty Mentors:** Teachers assigned to students; `/my-students` page for teachers to track their mentees.
- **Teacher Remarks & Action Plans:** Teachers log observations, action plans, and progress statuses (`Not Contacted`, `Counselled`, `Improving`, `Resolved`). Optional visibility toggle for students.
- **Interventions List:** `/interventions` lists all High-Risk students for coordinated faculty support.

### 3. Student Academic Features
- **Class Ranking:** `/ranking` calculates real-time class standing within the same branch and semester by internal marks, highlighting Top 10 Toppers.
- **Subject-Wise Analysis:** Evaluates each subject as `Strong` (>70%), `Average` (50-70%), or `Weak` (<50%), highlighting weak subjects needing intervention.
- **Target Calculator:** `/students/<id>/target` calculates the exact exam score required in final exams using the 40/60 weighting formula: `(Target - 0.40 * Internal) / 0.60`.
- **Attendance Shortage:** `/attendance-shortage` flags students below 75% attendance with color coding (critical <65% in red, 65-75% in orange).
- **Printable Student Report:** `/students/<id>/report` formatted for printing with signature lines and automatic media print clean styling.
- **Semester Results:** `/students/<id>/semesters` tracks SGPA and backlogs across semesters 1 to 8 with interactive Chart.js line graph.

### 4. Communication & Administration
- **Announcements:** `/announcements` allows posting targeted updates by department and semester.
- **Notification System:** In-app notification center with unread badge counter in top nav bar. Auto-notifies on High-Risk predictions, low attendance warnings, and new teacher remarks.
- **Forgot Password Workflow:** `/forgot-password` submits reset requests to the admin panel with single-use temporary password issuance.
- **Audit & Activity Log:** `/admin/activity` tracks logins, student modifications, predictions, model retraining, and bulk imports.
- **Bulk CSV Import:** `/import` for bulk uploading students and marks with row-by-row validation.
