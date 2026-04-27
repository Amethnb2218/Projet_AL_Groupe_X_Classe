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
    return parsed.strftime("%d/%m/%Y a %Hh%M")


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY="change-me-in-production",
        DATABASE=str(Path(app.instance_path) / "news.sqlite"),
        ARTICLES_PER_PAGE=4,
    )

    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    database.init_app(app)
    app.jinja_env.filters["date_fr"] = format_date_fr
    app.register_blueprint(routes.bp)
    app.register_blueprint(api.bp)
    app.register_blueprint(soap.bp)

    return app
