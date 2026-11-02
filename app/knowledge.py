"""Поиск по базе знаний: понимает формулировки, а не только точные слова.

Русские окончания отсекаются, синонимы подставляются, опечатки прощаются.
Внешних сервисов и ключей не требует.
"""
from __future__ import annotations

import re

from .models import Faq, KnowledgeArticle

WORD_RE = re.compile(r"[a-zа-яәғқңөұүһі0-9]+")

STOPWORDS = set("""
а без бы в вам вас ваш все где да для до его ее если есть же за и из или им как ко когда кто куда ли
меня мне мной можно мой на нам нас нет не ни но ну о об обратиться он она они от по под при про с со
так то у уже хочу чем что чтобы это эта этот я надо нужно нужен нужна получить взять найти посмотреть
""".split())

# Группы слов, которые студенты употребляют вместо друг друга (указаны основы).
SYNONYMS = (
    ("справк", "документ", "транскрипт"),
    ("пропуск", "пропуст", "отработ", "прогул", "болел", "болезн", "отсутств"),
    ("логотип", "лого", "эмблем", "символик", "брендбук"),
    ("практик", "стажировк"),
    ("журнал", "оценк", "успеваем", "smartnation", "смартнейшн", "снейшн"),
    ("расписан", "пар", "заняти"),
    ("парол", "логин", "вход", "войт"),
    ("общежити", "общаг", "заселен", "жиль"),
    ("скидк", "бонус", "промокод", "акци", "привилег"),
    ("соцсет", "инстаграм", "instagram", "телеграм", "telegram", "тикток", "tiktok", "ютуб", "youtube", "клуб"),
    ("фото", "видео", "ролик", "контент", "съемк"),
    ("ваканс", "работ", "трудоустройств", "подработк", "резюме"),
    ("директор", "прием"),
    ("обращен", "жалоб", "пожал", "предложен", "администрац"),
)

ENDINGS = sorted("""
иями ями ами ого его ому ему ыми ими ией ьей ует уют ешь ете ите ишь ать ять ить ыть ала ила ели али или
ая яя ое ее ые ие ой ей ий ый ом ем ам ям ах ях ую юю ов ев ию ия ье ья ью ть ла ли ло ут ют ит ет ны
а я о е и ы у ю ь й
""".split(), key=len, reverse=True)


def stem(word: str) -> str:
    if not re.search(r"[а-я]", word) or len(word) <= 3:
        return word
    for ending in ENDINGS:
        if word.endswith(ending) and len(word) - len(ending) >= 3:
            return word[:-len(ending)]
    return word


def tokens(text: str | None) -> list[str]:
    words = WORD_RE.findall((text or "").lower().replace("ё", "е"))
    return [stem(w) for w in words if w not in STOPWORDS]


def _same_root(word: str, root: str) -> bool:
    """Короткие основы вроде «пар» сравниваем целиком, иначе они совпадут с «паролем» и «партнёром»."""
    if len(root) < 4 or len(word) < 4:
        return word == root
    return word.startswith(root) or root.startswith(word)


def _related(token: str) -> set[str]:
    related = {token}
    for group in SYNONYMS:
        if any(_same_root(token, root) for root in group):
            related.update(group)
    return related


def _is_typo(a: str, b: str) -> bool:
    """Одна опечатка: лишняя, пропущенная или заменённая буква либо две переставленные.

    Только для основ от шести букв: на коротких «погод» и «повод» считались бы одним словом.
    """
    if min(len(a), len(b)) < 6 or abs(len(a) - len(b)) > 1 or a == b:
        return False
    i = 0
    while i < min(len(a), len(b)) and a[i] == b[i]:
        i += 1
    return (a[i + 1:] == b[i + 1:]                  # замена
            or a[i:] == b[i + 1:] or a[i + 1:] == b[i:]    # вставка или пропуск
            or (a[i:i + 2] == b[i:i + 2][::-1] and a[i + 2:] == b[i + 2:]))  # перестановка


def _word_score(token: str, words: list[str]) -> float:
    """1 — то же слово, 0.8 — однокоренное или синоним, 0.6 — похоже на опечатку."""
    best = 0.0
    related = _related(token)
    for word in words:
        if word == token:
            return 1.0
        if any(_same_root(word, root) for root in related):
            best = max(best, 0.8)
        elif _is_typo(token, word):
            best = max(best, 0.6)
    return best


def _score(query: list[str], weighted: list[tuple[list[str], float]]) -> float:
    total, matched = 0.0, 0
    for token in query:
        best = max((_word_score(token, words) * weight for words, weight in weighted), default=0.0)
        if best > 0:
            matched += 1
            total += best
    if not matched:
        return 0.0
    # Ответ, закрывающий все слова вопроса, важнее ответа с одним совпавшим словом.
    return total * matched / len(query)


def search(query: str, limit: int = 6) -> list[dict]:
    """Лучшие ответы: сперва типовые ситуации, затем обычные вопросы FAQ."""
    parsed = tokens(query)
    if not parsed:
        return []
    found: list[tuple[float, dict]] = []

    for item in KnowledgeArticle.query.filter_by(is_active=True).all():
        score = _score(parsed, [(tokens(item.question_ru), 3.0), (tokens(item.keywords), 3.0),
                                (tokens(item.short_answer_ru), 1.0), (tokens(item.steps_ru), 0.5)])
        if score:
            found.append((score, 1, {
                "title": item.tr("question"), "answer": item.tr("short_answer"),
                "steps": item.tr("steps"), "url": item.link_url or "",
                "label": item.tr("link_label") or "Открыть",
            }))

    for item in Faq.query.filter_by(is_active=True).all():
        score = _score(parsed, [(tokens(item.question_ru), 3.0), (tokens(item.answer_ru), 1.0)])
        if score:
            found.append((score, 0, {"title": item.tr("question"), "answer": item.tr("answer"),
                                     "steps": "", "url": "", "label": ""}))

    # При равной оценке типовая ситуация выше: в ней есть инструкция и ссылка.
    found.sort(key=lambda row: row[:2], reverse=True)
    if not found:
        return []
    # Отсекаем случайные совпадения: только то, что близко к лучшему ответу.
    threshold = max(found[0][0] * 0.45, 0.6)
    return [row for score, _, row in found if score >= threshold][:limit]
