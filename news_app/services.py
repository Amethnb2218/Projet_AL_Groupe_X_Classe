from __future__ import annotations

import re
import secrets
import unicodedata

from werkzeug.security import check_password_hash, generate_password_hash

from .database import get_db, utc_now


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower()
    return slug or "element"


def unique_slug(table: str, value: str, ignore_id: int | None = None) -> str:
    db = get_db()
    base = slugify(value)
    candidate = base
    index = 2
    while True:
        params: list[object] = [candidate]
        condition = "slug = ?"
        if ignore_id is not None:
            condition += " AND id <> ?"
            params.append(ignore_id)
        row = db.execute(f"SELECT id FROM {table} WHERE {condition}", params).fetchone()
        if row is None:
            return candidate
        candidate = f"{base}-{index}"
        index += 1


def authenticate(login: str, password: str):
    user = get_db().execute("SELECT * FROM users WHERE login = ?", (login,)).fetchone()
    if user and check_password_hash(user["password_hash"], password):
        return user
    return None


def list_users():
    return get_db().execute(
        "SELECT id, login, full_name, role, created_at FROM users ORDER BY login"
    ).fetchall()


def get_user(user_id: int):
    return get_db().execute(
        "SELECT id, login, full_name, role, created_at FROM users WHERE id = ?", (user_id,)
    ).fetchone()


def create_user(login: str, full_name: str, role: str, password: str):
    if role not in {"editor", "admin"}:
        raise ValueError("Le rôle doit être editor ou admin.")
    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO users (login, full_name, role, password_hash, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (login.strip(), full_name.strip(), role, generate_password_hash(password), utc_now()),
    )
    db.commit()
    return get_user(cursor.lastrowid)


def update_user(user_id: int, login: str, full_name: str, role: str, password: str | None = None):
    if role not in {"editor", "admin"}:
        raise ValueError("Le rôle doit être editor ou admin.")
    db = get_db()
    if password:
        db.execute(
            """
            UPDATE users
            SET login = ?, full_name = ?, role = ?, password_hash = ?
            WHERE id = ?
            """,
            (login.strip(), full_name.strip(), role, generate_password_hash(password), user_id),
        )
    else:
        db.execute(
            "UPDATE users SET login = ?, full_name = ?, role = ? WHERE id = ?",
            (login.strip(), full_name.strip(), role, user_id),
        )
    db.commit()
    return get_user(user_id)


def delete_user(user_id: int) -> None:
    db = get_db()
    db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()


def count_admins() -> int:
    return get_db().execute("SELECT COUNT(*) AS total FROM users WHERE role = 'admin'").fetchone()[
        "total"
    ]


def list_categories():
    return get_db().execute("SELECT * FROM categories ORDER BY name").fetchall()


def get_category(category_id: int):
    return get_db().execute("SELECT * FROM categories WHERE id = ?", (category_id,)).fetchone()


def get_category_by_slug(slug: str):
    return get_db().execute("SELECT * FROM categories WHERE slug = ?", (slug,)).fetchone()


def create_category(name: str, description: str):
    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO categories (name, slug, description, image_filename, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (name.strip(), unique_slug("categories", name), description.strip(), None, utc_now()),
    )
    db.commit()
    return get_category(cursor.lastrowid)


def update_category(category_id: int, name: str, description: str):
    db = get_db()
    db.execute(
        "UPDATE categories SET name = ?, slug = ?, description = ? WHERE id = ?",
        (name.strip(), unique_slug("categories", name, category_id), description.strip(), category_id),
    )
    db.commit()
    return get_category(category_id)


def set_category_image(category_id: int, image_filename: str | None):
    db = get_db()
    db.execute(
        "UPDATE categories SET image_filename = ? WHERE id = ?",
        (image_filename, category_id),
    )
    db.commit()
    return get_category(category_id)


def delete_category(category_id: int) -> None:
    db = get_db()
    db.execute("DELETE FROM categories WHERE id = ?", (category_id,))
    db.commit()


def list_articles(limit: int | None = None, offset: int = 0, category_id: int | None = None):
    params: list[object] = []
    where = "WHERE a.published = 1"
    if category_id is not None:
        where += " AND a.category_id = ?"
        params.append(category_id)
    sql = f"""
        SELECT
            a.*,
            COALESCE(c.name, 'Sans catégorie') AS category_name,
            c.slug AS category_slug,
            COALESCE(u.full_name, 'Utilisateur supprimé') AS author_name
        FROM articles a
        LEFT JOIN categories c ON c.id = a.category_id
        LEFT JOIN users u ON u.id = a.author_id
        {where}
        ORDER BY a.created_at DESC, a.id DESC
    """
    if limit is not None:
        sql += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
    return get_db().execute(sql, params).fetchall()


def list_all_articles_for_admin():
    return get_db().execute(
        """
        SELECT
            a.*,
            COALESCE(c.name, 'Sans catégorie') AS category_name,
            c.slug AS category_slug,
            COALESCE(u.full_name, 'Utilisateur supprimé') AS author_name
        FROM articles a
        LEFT JOIN categories c ON c.id = a.category_id
        LEFT JOIN users u ON u.id = a.author_id
        ORDER BY a.created_at DESC, a.id DESC
        """
    ).fetchall()


def count_articles(category_id: int | None = None) -> int:
    params: list[object] = []
    where = "WHERE published = 1"
    if category_id is not None:
        where += " AND category_id = ?"
        params.append(category_id)
    return get_db().execute(f"SELECT COUNT(*) AS total FROM articles {where}", params).fetchone()[
        "total"
    ]


def get_article(article_id: int):
    return get_db().execute(
        """
        SELECT
            a.*,
            COALESCE(c.name, 'Sans catégorie') AS category_name,
            c.slug AS category_slug,
            COALESCE(u.full_name, 'Utilisateur supprimé') AS author_name
        FROM articles a
        LEFT JOIN categories c ON c.id = a.category_id
        LEFT JOIN users u ON u.id = a.author_id
        WHERE a.id = ?
        """,
        (article_id,),
    ).fetchone()


def get_article_by_slug(slug: str):
    return get_db().execute(
        """
        SELECT
            a.*,
            COALESCE(c.name, 'Sans catégorie') AS category_name,
            c.slug AS category_slug,
            COALESCE(u.full_name, 'Utilisateur supprimé') AS author_name
        FROM articles a
        LEFT JOIN categories c ON c.id = a.category_id
        LEFT JOIN users u ON u.id = a.author_id
        WHERE a.slug = ? AND a.published = 1
        """,
        (slug,),
    ).fetchone()


def create_article(title: str, summary: str, content: str, category_id: int, author_id: int, published: bool):
    if get_category(category_id) is None:
        raise ValueError("Veuillez créer une catégorie avant d'ajouter un article.")
    db = get_db()
    now = utc_now()
    cursor = db.execute(
        """
        INSERT INTO articles
            (title, slug, summary, content, image_filename, category_id, author_id, published, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            title.strip(),
            unique_slug("articles", title),
            summary.strip(),
            content.strip(),
            None,
            category_id,
            author_id,
            1 if published else 0,
            now,
            now,
        ),
    )
    db.commit()
    return get_article(cursor.lastrowid)


def update_article(
    article_id: int,
    title: str,
    summary: str,
    content: str,
    category_id: int,
    published: bool,
):
    if get_category(category_id) is None:
        raise ValueError("Veuillez choisir une catégorie existante.")
    db = get_db()
    db.execute(
        """
        UPDATE articles
        SET title = ?, slug = ?, summary = ?, content = ?, category_id = ?, published = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            title.strip(),
            unique_slug("articles", title, article_id),
            summary.strip(),
            content.strip(),
            category_id,
            1 if published else 0,
            utc_now(),
            article_id,
        ),
    )
    db.commit()
    return get_article(article_id)


def set_article_image(article_id: int, image_filename: str | None):
    db = get_db()
    db.execute(
        "UPDATE articles SET image_filename = ?, updated_at = ? WHERE id = ?",
        (image_filename, utc_now(), article_id),
    )
    db.commit()
    return get_article(article_id)


def delete_article(article_id: int) -> None:
    db = get_db()
    db.execute("DELETE FROM articles WHERE id = ?", (article_id,))
    db.commit()


def article_to_dict(article) -> dict:
    return {
        "id": article["id"],
        "title": article["title"],
        "slug": article["slug"],
        "summary": article["summary"],
        "content": article["content"],
        "image_filename": article["image_filename"],
        "published": bool(article["published"]),
        "created_at": article["created_at"],
        "updated_at": article["updated_at"],
        "category": {
            "id": article["category_id"],
            "name": article["category_name"],
            "slug": article["category_slug"] if "category_slug" in article.keys() else None,
        },
        "author": article["author_name"],
    }


def list_active_tokens():
    return get_db().execute(
        """
        SELECT t.*, u.login AS creator_login
        FROM api_tokens t
        JOIN users u ON u.id = t.created_by
        WHERE t.revoked_at IS NULL
        ORDER BY t.created_at DESC
        """
    ).fetchall()


def create_token(label: str, created_by: int):
    token = secrets.token_urlsafe(32)
    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO api_tokens (label, token, created_by, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (label.strip() or "Jeton sans libellé", token, created_by, utc_now()),
    )
    db.commit()
    return db.execute("SELECT * FROM api_tokens WHERE id = ?", (cursor.lastrowid,)).fetchone()


def revoke_token(token_id: int) -> None:
    db = get_db()
    db.execute("UPDATE api_tokens SET revoked_at = ? WHERE id = ?", (utc_now(), token_id))
    db.commit()


def is_valid_token(token: str | None) -> bool:
    if not token:
        return False
    row = get_db().execute(
        "SELECT id FROM api_tokens WHERE token = ? AND revoked_at IS NULL", (token.strip(),)
    ).fetchone()
    return row is not None
