import os
import joblib
import pandas as pd

# Paths to saved models
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'model.pkl')
REG_MODEL_PATH = os.path.join(os.path.dirname(__file__), 'model_reg.pkl')

# Cached models
_model_clf = None
_model_reg = None

# Weight constants for target calculator
INTERNAL_WEIGHT = 0.4
FINAL_WEIGHT = 0.6

# Load classifier model
def get_classifier():
    global _model_clf
    if _model_clf is None:
        if os.path.exists(MODEL_PATH):
            _model_clf = joblib.load(MODEL_PATH)
        else:
            raise FileNotFoundError(f"Classifier model not found at {MODEL_PATH}")
    return _model_clf

# Load regression model
def get_regressor():
    global _model_reg
    if _model_reg is None:
        if os.path.exists(REG_MODEL_PATH):
            _model_reg = joblib.load(REG_MODEL_PATH)
        else:
            raise FileNotFoundError(f"Regressor model not found at {REG_MODEL_PATH}")
    return _model_reg

# Reload models after retraining
def reload_model():
    global _model_clf, _model_reg
    _model_clf = None
    _model_reg = None
    return get_classifier(), get_regressor()

# Convert numerical percentage to letter grade
def calculate_grade(percentage):
    if percentage >= 80.0:
        return 'A+'
    elif percentage >= 70.0:
        return 'A'
    elif percentage >= 60.0:
        return 'B'
    elif percentage >= 50.0:
        return 'C'
    elif percentage >= 40.0:
        return 'D'
    else:
        return 'F'

# Target score calculator: (target - 0.4*internal) / 0.6
def required_final_marks(internal_pct, target_pct):
    return (float(target_pct) - (INTERNAL_WEIGHT * float(internal_pct))) / FINAL_WEIGHT

# Rule-based suggestions generator
def generate_suggestions(features):
    suggestions = []
    
    if features.get('attendance_pct', 0) < 75.0:
        suggestions.append("Attend more classes regularly to keep attendance above 75%.")
        
    if features.get('study_hours', 0) < 10.0:
        suggestions.append("Increase weekly self-study time to at least 10-15 hours.")
        
    if features.get('assignment_pct', 0) < 70.0:
        suggestions.append("Submit assignments on time to improve internal marks.")
        
    if features.get('backlogs', 0) > 0:
        suggestions.append("Focus on clearing pending backlogs in the upcoming exam.")
        
    if features.get('internal_marks_pct', 0) < 40.0:
        suggestions.append("Attend remedial classes and improve test preparation.")
        
    if not suggestions:
        suggestions.append("Maintain your current good study routine.")
        
    return suggestions

# Rule-based reasons generator explaining prediction
def identify_reasons(features):
    reasons = []

    if features.get('attendance_pct', 0) < 75.0:
        reasons.append(f"Attendance is low ({features.get('attendance_pct', 0)}% < 75%)")
    else:
        reasons.append(f"Good attendance record ({features.get('attendance_pct', 0)}%)")

    if features.get('internal_marks_pct', 0) < 40.0:
        reasons.append(f"Low internal marks ({features.get('internal_marks_pct', 0)}%)")

    if features.get('study_hours', 0) < 10.0:
        reasons.append(f"Low weekly study hours ({features.get('study_hours', 0)} hrs/week)")

    if features.get('assignment_pct', 0) < 70.0:
        reasons.append(f"Assignment completion below target ({features.get('assignment_pct', 0)}%)")

    if features.get('backlogs', 0) > 0:
        reasons.append(f"Student has {features.get('backlogs', 0)} active backlog(s)")

    return reasons

# Run prediction for a single student's features dictionary
def predict_student(features_dict):
    clf = get_classifier()
    reg = get_regressor()

    # Input DataFrame
    input_data = pd.DataFrame([{
        'attendance_pct': float(features_dict.get('attendance_pct', 0.0)),
        'internal_marks_pct': float(features_dict.get('internal_marks_pct', 0.0)),
        'prev_percentage': float(features_dict.get('prev_percentage', 0.0)),
        'study_hours': float(features_dict.get('study_hours', 0.0)),
        'assignment_pct': float(features_dict.get('assignment_pct', 0.0)),
        'backlogs': int(features_dict.get('backlogs', 0))
    }])

    # 1. Classification
    probabilities = clf.predict_proba(input_data)[0]
    pass_prob = float(probabilities[1])
    result = "PASS" if pass_prob >= 0.50 else "FAIL"

    # Risk level rules
    if pass_prob >= 0.70:
        risk_level = "Low"
    elif pass_prob >= 0.40:
        risk_level = "Medium"
    else:
        risk_level = "High"

    # 2. Regression
    pred_raw_pct = float(reg.predict(input_data)[0])
    pred_pct = round(max(0.0, min(100.0, pred_raw_pct)), 1)
    grade = calculate_grade(pred_pct)

    reasons = identify_reasons(features_dict)
    suggestions = generate_suggestions(features_dict)

    return {
        'result': result,
        'pass_probability': round(pass_prob, 4),
        'predicted_percentage': pred_pct,
        'predicted_grade': grade,
        'risk_level': risk_level,
        'reasons': reasons,
        'suggestions': suggestions
    }
