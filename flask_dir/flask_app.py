# flask_app.py

from flask import Flask
from routesFolder.routes import routes_file
from routesFolder.oauth2 import oauth
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

def create_app():
    """
    Create and configure the Flask application.

    Returns:
        Flask: The configured Flask application instance.
    """
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object("configFile.DevelopmentConfig")
    app.config["SESSION_COOKIE_NAME"] = 'Spotify Sesh'
    
    # Register blueprints
    app.register_blueprint(routes_file)
    app.register_blueprint(oauth)
    
    return app

# Create the Flask application instance
app = create_app()

if __name__ == "__main__":
    app.run(debug=True)