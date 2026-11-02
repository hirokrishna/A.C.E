from app import app
from models import db
from sqlalchemy import text, inspect

# Database migration script to add new columns and tables without data loss
def run_migrations():
    with app.app_context():
        # 1. Create all newly defined tables if they do not exist
        db.create_all()
        print("Ensured all new tables exist.")

        engine = db.engine
        dialect_name = engine.dialect.name
        print(f"Connected database dialect: {dialect_name}")

        # List of columns to add to existing tables: (table_name, column_name, pg_type_def, sqlite_type_def)
        columns_to_add = [
            # students
            ('students', 'phone', 'VARCHAR(15)', 'VARCHAR(15)'),
            ('students', 'mentor_id', 'INTEGER REFERENCES users(id)', 'INTEGER'),
            # predictions
            ('predictions', 'predicted_percentage', 'FLOAT', 'FLOAT'),
            ('predictions', 'predicted_grade', 'VARCHAR(3)', 'VARCHAR(3)'),
            # model_info
            ('model_info', 'model_type', "VARCHAR(15) DEFAULT 'classifier'", "VARCHAR(15) DEFAULT 'classifier'"),
            ('model_info', 'mae', 'FLOAT', 'FLOAT'),
            ('model_info', 'r2_score', 'FLOAT', 'FLOAT'),
            ('model_info', 'feature_importance', 'TEXT', 'TEXT'),
            ('model_info', 'confusion_matrix', 'VARCHAR(100)', 'VARCHAR(100)')
        ]

        if dialect_name == 'postgresql':
            with engine.connect() as conn:
                for table, column, pg_type, _ in columns_to_add:
                    try:
                        sql = f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {pg_type};"
                        conn.execute(text(sql))
                        conn.commit()
                        print(f"PostgreSQL: Ensured column {column} on {table}")
                    except Exception as e:
                        print(f"Notice on {table}.{column}: {e}")
        else:
            # SQLite fallback: inspect existing table columns first
            inspector = inspect(engine)
            with engine.connect() as conn:
                for table, column, _, sqlite_type in columns_to_add:
                    try:
                        existing_cols = [c['name'] for c in inspector.get_columns(table)]
                        if column not in existing_cols:
                            sql = f"ALTER TABLE {table} ADD COLUMN {column} {sqlite_type};"
                            conn.execute(text(sql))
                            conn.commit()
                            print(f"SQLite: Added column {column} to {table}")
                        else:
                            print(f"SQLite: Column {column} already exists on {table}")
                    except Exception as e:
                        print(f"Notice on {table}.{column}: {e}")

        print("Database migrations applied successfully!")

if __name__ == '__main__':
    run_migrations()

