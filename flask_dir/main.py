from flask import Flask, Blueprint, session
# import redis
# from flask_redis import FlaskRedis
# in the meantime
from routesFolder.routes import routes_file
import os


app = Flask(__name__)
# redis_client = FlaskRedis(app)
app.config.from_object("configFile.DevelopmentConfig")
app.config["SESSION_COOKIE_NAME"] = 'Spotify Sesh'
app.register_blueprint(routes_file)