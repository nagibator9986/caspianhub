"""JSON-эндпоинты: живой поиск, избранное, учёт переходов."""
from __future__ import annotations

from flask import Blueprint, g, jsonify, request
from flask_login import current_user
from sqlalchemy import or_

from ..extensions import csrf, db
from ..models import Course, Favorite, Service, ServiceEvent

bp = Blueprint("api", __name__)


@bp.route("/search")
def search():
    q = (request.args.get("q") or "").strip()
    if len(q) < 2:
        return jsonify({"results": []})

    like = f"%{q}%"
    services = (Service.query.filter(
        Service.is_published.is_(True),
        or_(Service.name_ru.ilike(like), Service.name_kk.ilike(like),
            Service.name_en.ilike(like), Service.tagline_ru.ilike(like),
            Service.description_ru.ilike(like), Service.benefits_ru.ilike(like)),
    ).order_by(Service.is_featured.desc(), Service.position).limit(8).all())

    from flask import url_for

    return jsonify({"results": [{
        "name": s.tr("name"),
        "tagline": s.tr("tagline"),
        "category": s.category.tr("name") if s.category else "",
        "icon": s.icon,
        "color": s.color,
        "url": url_for("public.service_detail", slug=s.slug),
        "has_course": s.has_course,
    } for s in services]})


@bp.route("/favorite/<int:service_id>", methods=["POST"])
def toggle_favorite(service_id: int):
    if not current_user.is_authenticated:
        return jsonify({"error": "auth_required"}), 401

    service = db.session.get(Service, service_id)
    if not service:
        return jsonify({"error": "not_found"}), 404

    row = Favorite.query.filter_by(user_id=current_user.id, service_id=service_id).first()
    if row:
        db.session.delete(row)
        favorited = False
    else:
        db.session.add(Favorite(user_id=current_user.id, service_id=service_id))
        favorited = True
    db.session.commit()
    return jsonify({"ok": True, "favorited": favorited})


@bp.route("/track/<int:service_id>", methods=["POST"])
@csrf.exempt          # вызывается через navigator.sendBeacon при уходе на внешний сайт
def track(service_id: int):
    service = db.session.get(Service, service_id)
    if not service:
        return jsonify({"error": "not_found"}), 404
    service.clicks = (service.clicks or 0) + 1
    db.session.add(ServiceEvent(
        service_id=service.id, kind="click",
        user_id=current_user.id if current_user.is_authenticated else None,
    ))
    db.session.commit()
    return jsonify({"ok": True})


@bp.route("/stats")
def stats():
    return jsonify({
        "services": Service.query.filter_by(is_published=True).count(),
        "courses": Course.query.filter_by(is_published=True).count(),
        "lessons": sum(c.lesson_count for c in Course.query.filter_by(is_published=True).all()),
    })
