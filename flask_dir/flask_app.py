from flask import Flask, Blueprint, session
from routesFolder.routes import routes_file
import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
app = Flask(__name__)
app.config.from_object("configFile.DevelopmentConfig")
app.config["SESSION_COOKIE_NAME"] = 'Spotify Sesh'
app.register_blueprint(routes_file)