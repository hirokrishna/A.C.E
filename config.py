import os
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

# Settings for the Flask application
class Config:
    # Secret key for session security
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'default-secret-key-for-dev'

    # Database connection string
    db_url = os.environ.get('DATABASE_URL') or 'sqlite:///local.db'

    # Fix postgres:// prefix for SQLAlchemy if needed
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)

    SQLALCHEMY_DATABASE_URI = db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

