"""Local dev server. Production: gunicorn -w 2 -b 0.0.0.0:5000 wsgi:app"""
from wsgi import app

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
