from flask import Flask
from config import DB_PATH


def create_app():
    app = Flask(__name__)
    app.config["DB_PATH"] = DB_PATH

    return app
