"""Точка входа: python run.py"""
import os

from app import create_app
from app.extensions import db

app = create_app(os.environ.get("FLASK_ENV", "default"))


@app.shell_context_processor
def shell_context():
    from app import models
    return {"db": db, **{name: getattr(models, name) for name in dir(models) if name[0].isupper()}}


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
