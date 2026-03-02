from flask import Flask
from flask_cors import CORS
from database.extensions import db
from database.models import User
from routes.auth_routes import auth_bp

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///project.db'

db.init_app(app)

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')

with app.app_context():
    db.create_all()


@app.route('/')
def hello_world():  # put application's code here
    return 'Hello World!'


if __name__ == '__main__':
    app.run()
