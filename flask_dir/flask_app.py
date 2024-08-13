from flask import Flask, Blueprint, session
from routesFolder.routes import routes_file
from routesFolder.oauth2 import oauth
import os

from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config.from_object("configFile.DevelopmentConfig")
app.config["SESSION_COOKIE_NAME"] = 'Spotify Sesh'
app.register_blueprint(routes_file)
app.register_blueprint(oauth)