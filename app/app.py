# app/app.py — objeto WSGI para servidores (gunicorn app.app:app).
# La lógica vive en la fábrica app/__init__.py:create_app.
from app import create_app

app = create_app()

if __name__ == "__main__":
    import config
    app.run(host=config.HOST, port=config.PORT)
