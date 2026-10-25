import os
import sys

import pytest

FLASK_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "flask_dir")
sys.path.insert(0, FLASK_DIR)

# Fake credentials so nothing ever talks to a real Spotify app
os.environ["CLIENT_ID"] = "test-client-id"
os.environ["CLIENT_SECRET"] = "test-client-secret"
os.environ["CURRENT_URL"] = "http://127.0.0.1:5000/"


@pytest.fixture
def app():
    from flask_app import app
    app.config.update(TESTING=True)
    return app


@pytest.fixture
def client(app):
    return app.test_client()
