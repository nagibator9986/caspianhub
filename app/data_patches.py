"""Разовое добавление нового контента в уже работающую базу.

Каждый патч выполняется один раз и только добавляет строки. Существующие записи
не меняются, а удалённое админом не появится снова при следующем деплое.
"""
from __future__ import annotations

import json
from pathlib import Path

from .extensions import db
from .models import (AppealDepartment, DataPatch, KnowledgeArticle, LibraryAsset, MenuItem,
                     PartnerOffer, SocialLink)

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"
STATIC_DIR = Path(__file__).resolve().parent / "static"


def _load(name: str) -> list[dict]:
    with (CONTENT_DIR / name).open(encoding="utf-8") as fh:
        return json.load(fh)


def _add_social() -> None:
    for position, row in enumerate(_load("_social.json"), start=1):
        db.session.add(SocialLink(position=position, is_active=True, **row))


def _add_offers() -> None:
    for position, row in enumerate(_load("_offers.json"), start=1):
        db.session.add(PartnerOffer(position=position, is_active=True, **row))


def _add_appeal_departments() -> None:
    for position, row in enumerate(_load("_appeals.json"), start=1):
        db.session.add(AppealDepartment(position=position, is_active=True, **row))


def _add_knowledge() -> None:
    for position, row in enumerate(_load("_knowledge.json"), start=1):
        db.session.add(KnowledgeArticle(position=position, is_active=True, **row))


def _add_library_logo() -> None:
    path = "img/ccu-logo.png"
    db.session.add(LibraryAsset(
        category="Логотипы колледжа", title_ru="Логотип Колледжа Каспийского университета",
        path=path, download_name="college-caspian-logo.png",
        size=(STATIC_DIR / path).stat().st_size, position=1, is_active=True,
    ))


def _add_menu_item() -> None:
    url = "/category/community"
    if MenuItem.query.filter_by(location="header", url=url).first():
        return
    # Новый пункт встаёт последним: порядок остальных пунктов меню не меняется.
    position = (db.session.query(db.func.max(MenuItem.position))
                .filter_by(location="header").scalar() or 0) + 1
    db.session.add(MenuItem(location="header", title_ru="Для студентов", title_kk="Студенттерге",
                            title_en="For students", url=url, icon="messages-square",
                            position=position, is_active=True, is_external=False))


PATCHES = (
    ("2026-11-social-links", _add_social),
    ("2026-11-partner-offers", _add_offers),
    ("2026-11-appeal-departments", _add_appeal_departments),
    ("2026-11-knowledge-articles", _add_knowledge),
    ("2026-11-library-logo", _add_library_logo),
    ("2026-11-menu-community", _add_menu_item),
)


def apply_patches() -> list[str]:
    applied = []
    for key, patch in PATCHES:
        if db.session.get(DataPatch, key):
            continue
        patch()
        db.session.add(DataPatch(key=key))
        db.session.commit()
        applied.append(key)
    return applied
