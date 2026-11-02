from flask import Flask, render_template
from config import Config

# Create Flask application
app = Flask(__name__)
app.config.from_object(Config)

# Initialize database
from models import db
db.init_app(app)

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

