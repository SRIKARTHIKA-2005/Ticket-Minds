import os
from flask import Flask, send_from_directory
from backend.config.Config import Config  # Wait, let's import it case-safely as Config
from backend.config.config import Config
from backend.database.db_mgr import init_db
from backend.routes.auth import auth_bp
from backend.routes.tickets import tickets_bp
from backend.routes.messages import messages_bp

# 1. Initialize Flask App
# We configure it to serve static files from the '../frontend' folder.
# 'static_url_path=""' maps the root URL to the static folder, so '/css/styles.css' translates to '../frontend/css/styles.css'
app = Flask(__name__, static_folder='../frontend', static_url_path='')
app.config.from_object(Config)

# 2. Initialize the SQLite Database
init_db()

# 3. Register Blueprints
app.register_blueprint(auth_bp, url_path='/api/auth') # Wait, register_blueprint uses url_prefix instead of url_path in Flask
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(tickets_bp, url_prefix='/api/tickets')
app.register_blueprint(messages_bp, url_prefix='/api/messages')

# 4. Frontend Route Definitions
@app.route('/')
def landing_page():
    return app.send_static_file('html/index.html')

@app.route('/login')
def login_page():
    return app.send_static_file('html/login.html')

@app.route('/register')
def register_page():
    return app.send_static_file('html/register.html')

@app.route('/dashboard/user')
def user_dashboard_page():
    return app.send_static_file('html/user_dashboard.html')

@app.route('/dashboard/engineer')
def engineer_dashboard_page():
    return app.send_static_file('html/engineer_dashboard.html')

# 5. Handle direct favicon requests (prevents 404 logs)
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, '../frontend'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

if __name__ == '__main__':
    # Run the server on port 5000
    # Enable debug mode for developer friendliness
    app.run(host='0.0.0.0', port=5000, debug=True)
