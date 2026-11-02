import os
import sys
import json

# Ensure root directory is in sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, confusion_matrix,
    r2_score, mean_absolute_error
)

from models import db, ModelInfo

FEATURE_COLUMNS = [
    'attendance_pct',
    'internal_marks_pct',
    'prev_percentage',
    'study_hours',
    'assignment_pct',
    'backlogs'
]

# Train both classification and regression models and save the best of each
def train_and_save_model(csv_path='data/students_dataset.csv', 
                         clf_save_path='ml/model.pkl', 
                         reg_save_path='ml/model_reg.pkl'):
    print(f"Loading dataset from {csv_path}...")
    df = pd.read_csv(csv_path)

    required_cols = set(FEATURE_COLUMNS + ['result', 'final_percentage'])
    if not required_cols.issubset(df.columns):
        missing = required_cols - set(df.columns)
        raise ValueError(f"Missing required columns in dataset: {missing}")

    X = df[FEATURE_COLUMNS]
    y_class = df['result']
    y_reg = df['final_percentage']

    # 80/20 train-test split
    X_train, X_test, y_train_class, y_test_class = train_test_split(
        X, y_class, test_size=0.20, random_state=42, stratify=y_class
    )
    # Use matching index for regression split
    y_train_reg = y_reg.loc[X_train.index]
    y_test_reg = y_reg.loc[X_test.index]

    # ----------------------------------------------------
    # 1. Compare Classifiers (Pass/Fail)
    # ----------------------------------------------------
    classifiers = {
        'LogisticRegression': LogisticRegression(max_iter=1000, random_state=42),
        'DecisionTree': DecisionTreeClassifier(max_depth=5, random_state=42),
        'RandomForest': RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42)
    }

    best_clf = None
    best_clf_name = ""
    best_clf_f1 = -1.0
    all_clf_metrics = []
    rf_feature_importances = None
    best_cm_str = ""

    print("\n--- Comparing Classification Models ---")
    for name, clf in classifiers.items():
        clf.fit(X_train, y_train_class)
        y_pred = clf.predict(X_test)

        acc = float(accuracy_score(y_test_class, y_pred))
        prec = float(precision_score(y_test_class, y_pred, zero_division=0))
        rec = float(recall_score(y_test_class, y_pred, zero_division=0))
        f1 = float(f1_score(y_test_class, y_pred, zero_division=0))
        cm = confusion_matrix(y_test_class, y_pred).tolist()

        if name == 'RandomForest':
            # Save feature importances dictionary
            rf_feature_importances = {
                feat: round(float(imp), 4) 
                for feat, imp in zip(FEATURE_COLUMNS, clf.feature_importances_)
            }

        print(f"Classifier {name}: Accuracy={acc:.4f}, Precision={prec:.4f}, Recall={rec:.4f}, F1={f1:.4f}")

        is_best = False
        if f1 > best_clf_f1:
            best_clf_f1 = f1
            best_clf = clf
            best_clf_name = name
            best_cm_str = json.dumps(cm)

        all_clf_metrics.append({
            'name': name,
            'accuracy': acc,
            'precision': prec,
            'recall': rec,
            'f1': f1,
            'confusion_matrix': json.dumps(cm)
        })

    print(f"--> Best Classifier Selected: {best_clf_name} (F1: {best_clf_f1:.4f})")

    # ----------------------------------------------------
    # 2. Compare Regressors (Predicted Final Percentage)
    # ----------------------------------------------------
    regressors = {
        'LinearRegression': LinearRegression(),
        'RandomForestRegressor': RandomForestRegressor(n_estimators=100, max_depth=6, random_state=42)
    }

    best_reg = None
    best_reg_name = ""
    best_reg_r2 = -999.0
    all_reg_metrics = []

    print("\n--- Comparing Regression Models ---")
    for name, reg in regressors.items():
        reg.fit(X_train, y_train_reg)
        y_pred_reg = reg.predict(X_test)

        r2 = float(r2_score(y_test_reg, y_pred_reg))
        mae = float(mean_absolute_error(y_test_reg, y_pred_reg))

        print(f"Regressor {name}: R2={r2:.4f}, MAE={mae:.4f}")

        if r2 > best_reg_r2:
            best_reg_r2 = r2
            best_reg = reg
            best_reg_name = name

        all_reg_metrics.append({
            'name': name,
            'r2': r2,
            'mae': mae
        })

    print(f"--> Best Regressor Selected: {best_reg_name} (R2: {best_reg_r2:.4f})")

    # Save models to disk
    os.makedirs(os.path.dirname(clf_save_path), exist_ok=True)
    joblib.dump(best_clf, clf_save_path)
    joblib.dump(best_reg, reg_save_path)
    print(f"Saved classifier to {clf_save_path}")
    print(f"Saved regressor to {reg_save_path}")

    # ----------------------------------------------------
    # 3. Store metrics in database
    # ----------------------------------------------------
    from flask import has_app_context

    def save_records():
        # Deactivate previous active models
        ModelInfo.query.filter_by(is_active=True).update({'is_active': False})

        # Save all compared classifiers
        for m in all_clf_metrics:
            is_active = (m['name'] == best_clf_name)
            record = ModelInfo(
                model_name=m['name'],
                model_type='classifier',
                accuracy=m['accuracy'],
                precision_score=m['precision'],
                recall_score=m['recall'],
                f1_score=m['f1'],
                confusion_matrix=m['confusion_matrix'],
                feature_importance=json.dumps(rf_feature_importances) if rf_feature_importances else None,
                dataset_rows=len(df),
                is_active=is_active
            )
            db.session.add(record)

        # Save all compared regressors
        for r in all_reg_metrics:
            is_active = (r['name'] == best_reg_name)
            record = ModelInfo(
                model_name=r['name'],
                model_type='regressor',
                r2_score=r['r2'],
                mae=r['mae'],
                dataset_rows=len(df),
                is_active=is_active
            )
            db.session.add(record)

        db.session.commit()
        print("Updated model_info table with all model metrics.")

    if has_app_context():
        save_records()
    else:
        from app import app
        with app.app_context():
            save_records()

    return {
        'best_classifier': best_clf_name,
        'best_regressor': best_reg_name,
        'f1': best_clf_f1,
        'r2': best_reg_r2
    }

if __name__ == '__main__':
    train_and_save_model()
