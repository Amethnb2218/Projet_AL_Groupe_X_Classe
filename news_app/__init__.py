from __future__ import annotations

from datetime import datetime
from pathlib import Path

from flask import Flask

from . import api, database, routes, soap


def format_date_fr(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return value
    return parsed.strftime("%d/%m/%Y à %Hh%M")


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY="change-me-in-production",
        DATABASE=str(Path(app.instance_path) / "news.sqlite"),
        UPLOAD_FOLDER=str(Path(app.instance_path) / "uploads"),
        ALLOWED_IMAGE_EXTENSIONS={"png", "jpg", "jpeg", "webp", "gif"},
        ARTICLES_PER_PAGE=4,
        MAX_CONTENT_LENGTH=4 * 1024 * 1024,
    )

    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

    database.init_app(app)
    app.jinja_env.filters["date_fr"] = format_date_fr
    app.register_blueprint(routes.bp)
    app.register_blueprint(api.bp)
    app.register_blueprint(soap.bp)

    return app
