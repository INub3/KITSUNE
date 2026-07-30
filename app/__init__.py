# app/__init__.py — fábrica de la aplicación Kitsune.
from flask import Flask, redirect
import config


def create_app():
    app = Flask(__name__)  # templates -> app/templates, static -> app/static
    app.secret_key = config.SECRET_KEY

    # Crea el esquema y siembra datos por defecto en el primer arranque.
    from .db import init_db
    init_db()

    # Blueprints: tracking (público) + consola de administración (solo túnel SSH).
    from .views import tracking, dashboard, profiles, templates, users, campaigns
    app.register_blueprint(tracking.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(profiles.bp)
    app.register_blueprint(templates.bp)
    app.register_blueprint(users.bp)
    app.register_blueprint(campaigns.bp)

    @app.route("/")
    def _root():
        return redirect("/dashboard")

    return app
