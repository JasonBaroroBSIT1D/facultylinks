"""Local dev server. Production: gunicorn -w 2 -b 0.0.0.0:5000 wsgi:app"""
import os

from app.config import load_backend_env
from wsgi import app

if __name__ == "__main__":
    load_backend_env()
    host = os.environ.get("FLASK_RUN_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_RUN_PORT", "5000"))
    app.run(host=host, port=port, debug=True)
