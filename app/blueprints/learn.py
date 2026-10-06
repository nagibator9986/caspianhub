"""Мини-курсы: уроки, прогресс, тесты, сертификаты."""
from __future__ import annotations

import json

from flask import (Blueprint, abort, flash, jsonify, redirect,
                   render_template, request, url_for)
from flask_login import current_user, login_required

from ..extensions import db
from ..models import (Certificate, Course, Lesson, LessonProgress, Quiz,
                      QuizAttempt, utcnow)

bp = Blueprint("learn", __name__)


def _get_course(slug: str) -> Course:
    course = Course.query.filter_by(slug=slug).first_or_404()
    if not course.is_published and not (current_user.is_authenticated and current_user.is_staff):
        abort(404)
    return course


def _flat_lessons(course: Course) -> list[Lesson]:
    return course.lessons


@bp.route("/<slug>")
def course_overview(slug: str):
    course = _get_course(slug)
    progress = course.progress_for(current_user)
    lessons = _flat_lessons(course)
    first = lessons[0] if lessons else None

    next_lesson = first
    if current_user.is_authenticated:
        next_lesson = next((l for l in lessons if not l.is_done_by(current_user)), None) or first

    quiz = course.quiz
    best = quiz.best_attempt(current_user) if quiz else None
    certificate = None
    if current_user.is_authenticated:
        certificate = Certificate.query.filter_by(
            user_id=current_user.id, course_id=course.id).first()

    return render_template("learn/course.html", course=course, progress=progress,
                           lessons=lessons, next_lesson=next_lesson,
                           quiz=quiz, best=best, certificate=certificate)


@bp.route("/<slug>/lesson/<int:lesson_id>")
def lesson(slug: str, lesson_id: int):
    course = _get_course(slug)
    item = db.session.get(Lesson, lesson_id)
    if not item or item.course.id != course.id:
        abort(404)

    lessons = _flat_lessons(course)
    index = lessons.index(item)
    prev_lesson = lessons[index - 1] if index > 0 else None
    next_lesson = lessons[index + 1] if index < len(lessons) - 1 else None

    return render_template("learn/lesson.html", course=course, lesson=item,
                           lessons=lessons, index=index,
                           prev_lesson=prev_lesson, next_lesson=next_lesson,
                           progress=course.progress_for(current_user))


@bp.route("/lesson/<int:lesson_id>/complete", methods=["POST"])
def complete_lesson(lesson_id: int):
    if not current_user.is_authenticated:
        return jsonify({"error": "auth_required"}), 401

    item = db.session.get(Lesson, lesson_id)
    if not item:
        return jsonify({"error": "not_found"}), 404

    row = LessonProgress.query.filter_by(user_id=current_user.id, lesson_id=item.id).first()
    if not row:
        row = LessonProgress(user_id=current_user.id, lesson_id=item.id)
        db.session.add(row)
    row.completed = True
    row.completed_at = utcnow()
    db.session.commit()

    course = item.course
    progress = course.progress_for(current_user)
    lessons = _flat_lessons(course)
    index = lessons.index(item)
    next_lesson = lessons[index + 1] if index < len(lessons) - 1 else None

    if next_lesson:
        next_url = url_for("learn.lesson", slug=course.slug, lesson_id=next_lesson.id)
    elif course.quiz:
        next_url = url_for("learn.quiz", slug=course.slug)
    else:
        next_url = url_for("learn.course_overview", slug=course.slug)

    return jsonify({
        "ok": True,
        "progress": progress,
        "completed_course": progress >= 100,
        "next_url": next_url,
    })


@bp.route("/<slug>/quiz", methods=["GET", "POST"])
@login_required
def quiz(slug: str):
    course = _get_course(slug)
    quiz_obj = course.quiz
    if not quiz_obj or not quiz_obj.questions:
        flash("К этому курсу пока нет теста.", "info")
        return redirect(url_for("learn.course_overview", slug=course.slug))

    if request.method == "POST":
        answers, correct = {}, 0
        for question in quiz_obj.questions:
            chosen = request.form.get(f"q{question.id}", type=int)
            answers[str(question.id)] = chosen
            option = next((o for o in question.options if o.id == chosen), None)
            if option and option.is_correct:
                correct += 1

        total = len(quiz_obj.questions)
        score = int(round(correct * 100 / total)) if total else 0
        passed = score >= (quiz_obj.pass_score or 70)

        attempt = QuizAttempt(quiz_id=quiz_obj.id, user_id=current_user.id, score=score,
                              correct_count=correct, total_count=total, passed=passed,
                              answers_json=json.dumps(answers))
        db.session.add(attempt)

        if passed and course.certificate_enabled:
            existing = Certificate.query.filter_by(
                user_id=current_user.id, course_id=course.id).first()
            if not existing:
                db.session.add(Certificate(user_id=current_user.id, course_id=course.id,
                                           code=Certificate.new_code(), score=score))
            elif score > (existing.score or 0):
                existing.score = score

        db.session.commit()
        return redirect(url_for("learn.quiz_result", slug=course.slug, attempt_id=attempt.id))

    best = quiz_obj.best_attempt(current_user)
    return render_template("learn/quiz.html", course=course, quiz=quiz_obj, best=best)


@bp.route("/<slug>/quiz/result/<int:attempt_id>")
@login_required
def quiz_result(slug: str, attempt_id: int):
    course = _get_course(slug)
    attempt = db.session.get(QuizAttempt, attempt_id)
    if not attempt or attempt.user_id != current_user.id:
        abort(404)

    try:
        answers = json.loads(attempt.answers_json or "{}")
    except json.JSONDecodeError:
        answers = {}

    certificate = Certificate.query.filter_by(
        user_id=current_user.id, course_id=course.id).first()

    return render_template("learn/quiz_result.html", course=course, quiz=attempt.quiz,
                           attempt=attempt, answers=answers, certificate=certificate)


@bp.route("/certificate/<code>")
def certificate(code: str):
    cert = Certificate.query.filter_by(code=code).first_or_404()
    return render_template("learn/certificate.html", cert=cert)
