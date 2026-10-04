"""ACEest Fitness & Gym - Flask application factory and entry point."""

import os

from flask import Flask, jsonify, render_template
from werkzeug.exceptions import HTTPException

import api
import fitness
from validators import ValidationError

__version__ = "1.0.0"


def create_app(test_config=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_mapping(APP_VERSION=__version__)
    if test_config:
        app.config.update(test_config)

    app.register_blueprint(api.bp)
    register_error_handlers(app)

    @app.get("/")
    def index():
        return render_template("index.html",
                               programs=fitness.list_programs(),
                               version=app.config["APP_VERSION"])

    @app.get("/health")
    def health():
        return jsonify(status="ok", service="aceest-fitness",
                       version=app.config["APP_VERSION"])

    return app


def register_error_handlers(app):
    """Return JSON errors instead of HTML pages."""

    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        return jsonify(error=str(error)), 400

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        return jsonify(error=error.description), error.code


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    create_app().run(host="0.0.0.0", port=port)
