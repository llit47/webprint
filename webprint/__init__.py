from pathlib import Path

from flask import Flask

from .routes import register_routes


def create_app():
    base_dir = Path(__file__).resolve().parent.parent
    app = Flask(__name__, template_folder=str(base_dir / "templates"))
    register_routes(app)
    return app
