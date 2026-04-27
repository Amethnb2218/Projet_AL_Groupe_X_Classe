from __future__ import annotations

import sqlite3
import uuid
from functools import wraps
from pathlib import Path

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.utils import secure_filename

from .database import get_db
from . import services

bp = Blueprint("web", __name__)


def allowed_image(filename: str) -> bool:
    if "." not in filename:
        return False
    extension = filename.rsplit(".", 1)[1].lower()
    return extension in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]


def save_article_image(file_storage) -> str | None:
    if file_storage is None or not file_storage.filename:
        return None
    original_name = secure_filename(file_storage.filename)
    if not allowed_image(original_name):
        raise ValueError("Format d'image non autorisé. Utilisez PNG, JPG, JPEG, WEBP ou GIF.")
    extension = original_name.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{extension}"
    destination = Path(current_app.config["UPLOAD_FOLDER"]) / filename
    file_storage.save(destination)
    return filename


def delete_article_image(filename: str | None) -> None:
    if not filename:
        return
    upload_dir = Path(current_app.config["UPLOAD_FOLDER"]).resolve()
    image_path = (upload_dir / filename).resolve()
    if image_path.parent == upload_dir and image_path.exists():
        image_path.unlink()


def article_image_url(article) -> str:
    filename = None
    if article is not None and "image_filename" in article.keys():
        filename = article["image_filename"]
    if filename:
        return url_for("web.uploaded_file", filename=filename)
    return url_for("static", filename="images/african-journalist-fallback.png")


@bp.before_app_request
def load_logged_in_user() -> None:
    user_id = session.get("user_id")
    g.user = None
    if user_id is not None:
        g.user = get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for("web.login", next=request.path))
        return view(**kwargs)

    return wrapped_view


def role_required(*roles: str):
    def decorator(view):
        @wraps(view)
        def wrapped_view(**kwargs):
            if g.user is None:
                return redirect(url_for("web.login", next=request.path))
            if g.user["role"] not in roles:
                abort(403)
            return view(**kwargs)

        return wrapped_view

    return decorator


@bp.context_processor
def inject_categories():
    try:
        return {"nav_categories": services.list_categories(), "article_image_url": article_image_url}
    except sqlite3.OperationalError:
        return {"nav_categories": [], "article_image_url": article_image_url}


@bp.route("/uploads/<path:filename>")
def uploaded_file(filename: str):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)


@bp.route("/")
def home():
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = current_app.config["ARTICLES_PER_PAGE"]
    total = services.count_articles()
    articles = services.list_articles(limit=per_page, offset=(page - 1) * per_page)
    return render_template(
        "home.html",
        articles=articles,
        page=page,
        total=total,
        per_page=per_page,
        has_previous=page > 1,
        has_next=page * per_page < total,
    )


@bp.route("/articles/<slug>")
def article_detail(slug: str):
    article = services.get_article_by_slug(slug)
    if article is None:
        abort(404)
    return render_template("article_detail.html", article=article)


@bp.route("/categories")
def categories():
    return render_template("categories.html", categories=services.list_categories())


@bp.route("/categories/<slug>")
def category_detail(slug: str):
    category = services.get_category_by_slug(slug)
    if category is None:
        abort(404)
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = current_app.config["ARTICLES_PER_PAGE"]
    total = services.count_articles(category["id"])
    articles = services.list_articles(per_page, (page - 1) * per_page, category["id"])
    return render_template(
        "category_detail.html",
        category=category,
        articles=articles,
        page=page,
        total=total,
        per_page=per_page,
        has_previous=page > 1,
        has_next=page * per_page < total,
    )


@bp.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        user = services.authenticate(request.form["login"], request.form["password"])
        if user is None:
            flash("Login ou mot de passe incorrect.", "error")
        else:
            session.clear()
            session["user_id"] = user["id"]
            flash("Connexion réussie.", "success")
            return redirect(request.args.get("next") or url_for("web.home"))
    return render_template("login.html")


@bp.route("/logout", methods=("POST",))
def logout():
    session.clear()
    flash("Vous êtes déconnecté.", "success")
    return redirect(url_for("web.home"))


@bp.route("/editor/articles")
@role_required("editor", "admin")
def manage_articles():
    return render_template("manage_articles.html", articles=services.list_all_articles_for_admin())


@bp.route("/editor/articles/new", methods=("GET", "POST"))
@role_required("editor", "admin")
def new_article():
    if request.method == "POST":
        saved_image = None
        try:
            saved_image = save_article_image(request.files.get("image"))
            article = services.create_article(
                request.form["title"],
                request.form["summary"],
                request.form["content"],
                request.form.get("category_id", type=int),
                g.user["id"],
                request.form.get("published") == "on",
            )
            if saved_image:
                services.set_article_image(article["id"], saved_image)
            flash("Article ajouté.", "success")
            return redirect(url_for("web.edit_article", article_id=article["id"]))
        except (sqlite3.IntegrityError, ValueError) as exc:
            delete_article_image(saved_image)
            flash(f"Impossible d'ajouter l'article : {exc}", "error")
    return render_template("article_form.html", article=None, categories=services.list_categories())


@bp.route("/editor/articles/<int:article_id>/edit", methods=("GET", "POST"))
@role_required("editor", "admin")
def edit_article(article_id: int):
    article = services.get_article(article_id)
    if article is None:
        abort(404)
    if request.method == "POST":
        saved_image = None
        try:
            saved_image = save_article_image(request.files.get("image"))
            services.update_article(
                article_id,
                request.form["title"],
                request.form["summary"],
                request.form["content"],
                request.form.get("category_id", type=int),
                request.form.get("published") == "on",
            )
            if saved_image:
                delete_article_image(article["image_filename"])
                services.set_article_image(article_id, saved_image)
            elif request.form.get("remove_image") == "on":
                delete_article_image(article["image_filename"])
                services.set_article_image(article_id, None)
            flash("Article modifié.", "success")
            return redirect(url_for("web.manage_articles"))
        except (sqlite3.IntegrityError, ValueError) as exc:
            delete_article_image(saved_image)
            flash(f"Impossible de modifier l'article : {exc}", "error")
    return render_template("article_form.html", article=article, categories=services.list_categories())


@bp.route("/editor/articles/<int:article_id>/delete", methods=("POST",))
@role_required("editor", "admin")
def delete_article(article_id: int):
    article = services.get_article(article_id)
    if article:
        delete_article_image(article["image_filename"])
    services.delete_article(article_id)
    flash("Article supprimé.", "success")
    return redirect(url_for("web.manage_articles"))


@bp.route("/editor/categories", methods=("GET", "POST"))
@role_required("editor", "admin")
def manage_categories():
    if request.method == "POST":
        try:
            services.create_category(request.form["name"], request.form.get("description", ""))
            flash("Catégorie ajoutée.", "success")
        except sqlite3.IntegrityError as exc:
            flash(f"Impossible d'ajouter la catégorie : {exc}", "error")
        return redirect(url_for("web.manage_categories"))
    return render_template("manage_categories.html", categories=services.list_categories())


@bp.route("/editor/categories/<int:category_id>/edit", methods=("GET", "POST"))
@role_required("editor", "admin")
def edit_category(category_id: int):
    category = services.get_category(category_id)
    if category is None:
        abort(404)
    if request.method == "POST":
        try:
            services.update_category(category_id, request.form["name"], request.form.get("description", ""))
            flash("Catégorie modifiée.", "success")
            return redirect(url_for("web.manage_categories"))
        except sqlite3.IntegrityError as exc:
            flash(f"Impossible de modifier la catégorie : {exc}", "error")
    return render_template("category_form.html", category=category)


@bp.route("/editor/categories/<int:category_id>/delete", methods=("POST",))
@role_required("editor", "admin")
def delete_category(category_id: int):
    try:
        services.delete_category(category_id)
        flash("Catégorie supprimée.", "success")
    except sqlite3.IntegrityError:
        flash("Cette catégorie contient encore des articles.", "error")
    return redirect(url_for("web.manage_categories"))


@bp.route("/admin/users", methods=("GET", "POST"))
@role_required("admin")
def manage_users():
    if request.method == "POST":
        try:
            services.create_user(
                request.form["login"],
                request.form["full_name"],
                request.form["role"],
                request.form["password"],
            )
            flash("Utilisateur ajouté.", "success")
        except (sqlite3.IntegrityError, ValueError) as exc:
            flash(f"Impossible d'ajouter l'utilisateur : {exc}", "error")
        return redirect(url_for("web.manage_users"))
    return render_template("manage_users.html", users=services.list_users())


@bp.route("/admin/users/<int:user_id>/edit", methods=("GET", "POST"))
@role_required("admin")
def edit_user(user_id: int):
    user = services.get_user(user_id)
    if user is None:
        abort(404)
    if request.method == "POST":
        if user["role"] == "admin" and request.form["role"] != "admin" and services.count_admins() <= 1:
            flash("Impossible de retirer le dernier administrateur.", "error")
        else:
            try:
                services.update_user(
                    user_id,
                    request.form["login"],
                    request.form["full_name"],
                    request.form["role"],
                    request.form.get("password") or None,
                )
                flash("Utilisateur modifié.", "success")
                return redirect(url_for("web.manage_users"))
            except (sqlite3.IntegrityError, ValueError) as exc:
                flash(f"Impossible de modifier l'utilisateur : {exc}", "error")
    return render_template("user_form.html", user=user)


@bp.route("/admin/users/<int:user_id>/delete", methods=("POST",))
@role_required("admin")
def delete_user(user_id: int):
    if user_id == g.user["id"]:
        flash("Vous ne pouvez pas supprimer votre propre compte.", "error")
    else:
        user = services.get_user(user_id)
        if user and user["role"] == "admin" and services.count_admins() <= 1:
            flash("Impossible de supprimer le dernier administrateur.", "error")
        else:
            try:
                services.delete_user(user_id)
                flash("Utilisateur supprimé.", "success")
            except sqlite3.IntegrityError:
                flash("Cet utilisateur est lié à des articles ou jetons.", "error")
    return redirect(url_for("web.manage_users"))


@bp.route("/admin/tokens", methods=("GET", "POST"))
@role_required("admin")
def manage_tokens():
    created_token = None
    if request.method == "POST":
        created_token = services.create_token(request.form.get("label", ""), g.user["id"])
        flash("Jeton créé. Copiez-le maintenant, il donne accès au service SOAP.", "success")
    return render_template(
        "manage_tokens.html",
        tokens=services.list_active_tokens(),
        created_token=created_token,
    )


@bp.route("/admin/tokens/<int:token_id>/delete", methods=("POST",))
@role_required("admin")
def delete_token(token_id: int):
    services.revoke_token(token_id)
    flash("Jeton supprimé.", "success")
    return redirect(url_for("web.manage_tokens"))
