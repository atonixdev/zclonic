from flask import Flask
from routes import main  

def create_app():
    app = Flask(__name__)
    
    # Load configuration from config.py
    app.config.from_pyfile('config.py')

    # Register your blueprint
    app.register_blueprint(main)

    return app