import os

from flask import Flask, request

from app.config import config_by_name, load_backend_env
from app.extensions import cors, db, migrate
from app.cli import register_cli
from app.routes.auth import bp as auth_bp
from app.routes.documents import bp as documents_bp
from app.routes.faculty_portal import bp as faculty_portal_bp
from app.routes.health import bp as health_bp
from app.routes.portal import bp as portal_bp


def create_app() -> Flask:
    load_backend_env()
    env = os.environ.get("FLASK_ENV", "development")
    app = Flask(__name__)
    app.config.from_object(config_by_name.get(env, config_by_name["development"]))
    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        raise RuntimeError(
            "DATABASE_URL is required (Supabase PostgreSQL). Copy backend/.env.example to .env "
            "and set your Supabase connection string. SQLite fallback is disabled."
        )

    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        supports_credentials=True,
    )

    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(portal_bp)
    app.register_blueprint(faculty_portal_bp)

    register_cli(app)

    @app.after_request
    def _no_store_authenticated_api(response):
        path = request.path or ""
        if path.startswith("/api/auth") or path == "/api/portal/state":
            response.headers["Cache-Control"] = "no-store, private"
        return response

    return app
