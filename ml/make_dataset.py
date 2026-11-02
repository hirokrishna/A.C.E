import os
import random
import pandas as pd
import numpy as np

# Generate realistic student dataset with final_percentage and pass/fail result
def generate_student_dataset(output_path='data/students_dataset.csv', num_rows=1000):
    np.random.seed(42)
    random.seed(42)

    rows = []

    for _ in range(num_rows):
        student_type = random.choices(['weak', 'average', 'strong'], weights=[0.25, 0.45, 0.30])[0]

        if student_type == 'weak':
            attendance = np.clip(np.random.normal(52, 11), 30, 75)
            internal = np.clip(np.random.normal(38, 9), 18, 58)
            prev_pct = np.clip(np.random.normal(46, 8), 32, 60)
            study_hrs = np.clip(np.random.normal(5, 2.5), 1, 10)
            assignment = np.clip(np.random.normal(52, 14), 20, 70)
            backlogs = np.random.choice([1, 2, 3, 4, 5], p=[0.25, 0.35, 0.20, 0.10, 0.10])
        elif student_type == 'average':
            attendance = np.clip(np.random.normal(76, 8), 60, 90)
            internal = np.clip(np.random.normal(62, 9), 45, 78)
            prev_pct = np.clip(np.random.normal(65, 8), 50, 78)
            study_hrs = np.clip(np.random.normal(12, 4), 6, 20)
            assignment = np.clip(np.random.normal(78, 9), 58, 94)
            backlogs = np.random.choice([0, 1, 2], p=[0.65, 0.25, 0.10])
        else: # strong
            attendance = np.clip(np.random.normal(88, 6), 75, 100)
            internal = np.clip(np.random.normal(82, 8), 66, 98)
            prev_pct = np.clip(np.random.normal(83, 7), 68, 98)
            study_hrs = np.clip(np.random.normal(20, 5), 10, 35)
            assignment = np.clip(np.random.normal(92, 6), 76, 100)
            backlogs = 0

        # Weighted composite score
        score = (
            (0.25 * attendance) + 
            (0.30 * internal) + 
            (0.20 * prev_pct) + 
            (0.15 * (study_hrs / 30.0 * 100.0)) + 
            (0.10 * assignment) - 
            (backlogs * 5.0) +
            np.random.normal(0, 4)
        )

        final_pct = round(float(np.clip(score, 10.0, 98.0)), 1)
        result = 1 if final_pct >= 40.0 else 0

        rows.append({
            'attendance_pct': round(float(attendance), 2),
            'internal_marks_pct': round(float(internal), 2),
            'prev_percentage': round(float(prev_pct), 2),
            'study_hours': round(float(study_hrs), 2),
            'assignment_pct': round(float(assignment), 2),
            'backlogs': int(backlogs),
            'final_percentage': final_pct,
            'result': int(result)
        })

    df = pd.DataFrame(rows)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Dataset generated with {len(df)} rows at {output_path}.")
    print("Class result count (Pass=1, Fail=0):")
    print(df['result'].value_counts())
    print("Final percentage summary:")
    print(df['final_percentage'].describe())
    return df

if __name__ == '__main__':
    generate_student_dataset()
