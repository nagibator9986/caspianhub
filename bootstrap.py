"""Подготовка базы при старте контейнера (Railway).

Создаёт таблицы и заливает демо-контент, только если база пустая —
повторные деплои данные не трогают. Если заданы ADMIN_EMAIL и
ADMIN_PASSWORD, создаёт/обновляет администратора с этими данными.
"""
import os

from app import create_app
from app.extensions import db
from app.models import Setting, User

app = create_app(os.environ.get("FLASK_ENV", "production"))

with app.app_context():
    db.create_all()
    if Setting.query.count() == 0:
        from seed import run_seed

        print("База пустая — заливаю контент…")
        run_seed()
    else:
        print("База уже наполнена — пропускаю сид.")

    email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    password = os.environ.get("ADMIN_PASSWORD", "")
    if email and password:
        admin = User.query.filter_by(email=email).first()
        if admin is None:
            admin = User(email=email, full_name="Администратор", role="admin")
            db.session.add(admin)
        admin.role = "admin"
        admin.set_password(password)
        db.session.commit()
        print(f"Администратор {email} готов.")
