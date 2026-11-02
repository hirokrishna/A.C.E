from flask import Flask, render_template
from config import Config

# Create Flask application
app = Flask(__name__)
app.config.from_object(Config)

# Initialize database
from models import db, User
db.init_app(app)

# Auto-create tables and seed initial data if running on a fresh deployment (e.g. Render)
with app.app_context():
    try:
        db.create_all()
        if not User.query.first():
            from seed import seed_database
            seed_database()
            print("Database automatically created and seeded.")
    except Exception as e:
        print("Startup database initialization notice:", e)

# Register blueprints
from routes.auth_routes import auth_bp
from routes.student_routes import student_bp
from routes.academic_routes import academic_bp
from routes.predict_routes import predict_bp
from routes.dashboard_routes import dashboard_bp
from routes.admin_routes import admin_bp

app.register_blueprint(auth_bp)
app.register_blueprint(student_bp)
app.register_blueprint(academic_bp)
app.register_blueprint(predict_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(admin_bp)

# Context processor for navbar notifications
from helpers import inject_unread_notifications
app.context_processor(inject_unread_notifications)

# Error handlers
@app.errorhandler(403)
def access_denied(error):
    return render_template('403.html'), 403

@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404

# Run development server
if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True, use_reloader=False)

