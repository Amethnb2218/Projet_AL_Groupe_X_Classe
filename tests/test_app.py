from __future__ import annotations

import base64
import io
from pathlib import Path

import pytest

from news_app import create_app
from news_app import services
from news_app.database import init_db


PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


@pytest.fixture()
def app(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "DATABASE": str(tmp_path / "test.sqlite"),
            "UPLOAD_FOLDER": str(tmp_path / "uploads"),
        }
    )
    with app.app_context():
        init_db()
    return app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def sample_content(app):
    with app.app_context():
        category = services.create_category("Technologie", "Articles sur le numerique.")
        editor = services.create_user("editor", "Editeur", "editor", "editor123")
        article = services.create_article(
            "Architecture propre pour une redaction",
            "Un article de test publie pour verifier les parcours publics.",
            "Contenu complet de l'article utilise par les tests.",
            category["id"],
            editor["id"],
            True,
        )
        token = services.create_token("Jeton de test", 1)["token"]
        return {"category": category, "editor": editor, "article": article, "token": token}


def soap(operation: str, fields: dict[str, str]) -> str:
    items = "".join(f"<{key}>{value}</{key}>" for key, value in fields.items())
    return f"""
    <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
      <soap:Body>
        <{operation}>{items}</{operation}>
      </soap:Body>
    </soap:Envelope>
    """


def login(client, login_name="admin", password="admin123"):
    return client.post("/login", data={"login": login_name, "password": password}, follow_redirects=True)


def test_initial_database_contains_only_required_admin(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Aucun article publie" in response.data

    categories = client.get("/api/articles/grouped")
    assert categories.status_code == 200
    assert categories.json["categories"] == []


def test_frontend_uses_african_fallback_image_and_wraps_long_titles(client):
    response = client.get("/static/styles.css")
    assert response.status_code == 200
    assert b"african-journalist-fallback.png" in response.data
    assert b"overflow-wrap: anywhere" in response.data

    image = client.get("/static/images/african-journalist-fallback.png")
    assert image.status_code == 200
    assert image.mimetype == "image/png"


def test_seed_content_command_adds_editorial_articles(app, client):
    runner = app.test_cli_runner()
    result = runner.invoke(args=["seed-content"])
    assert result.exit_code == 0

    response = client.get("/api/articles")
    assert response.status_code == 200
    assert len(response.json["articles"]) == 8
    assert any(
        article["slug"] == "cybersouverainete-equipes-techniques-reprennent-main"
        for article in response.json["articles"]
    )

    categories = client.get("/api/articles/grouped")
    assert len(categories.json["categories"]) == 5


def test_home_lists_created_articles_and_pagination(client, sample_content):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Architecture propre" in response.data
    assert b"Suivant" in response.data


def test_article_detail_from_title_link(client, sample_content):
    response = client.get("/articles/architecture-propre-pour-une-redaction")
    assert response.status_code == 200
    assert b"architecture propre" in response.data.lower()


def test_rest_articles_json_and_xml(client, sample_content):
    json_response = client.get("/api/articles")
    assert json_response.status_code == 200
    assert json_response.json["articles"]
    assert "image_filename" in json_response.json["articles"][0]

    xml_response = client.get("/api/articles?format=xml")
    assert xml_response.status_code == 200
    assert xml_response.mimetype == "application/xml"
    assert b"<articles>" in xml_response.data


def test_rest_articles_by_category(client, sample_content):
    category_id = sample_content["category"]["id"]
    response = client.get(f"/api/categories/{category_id}/articles")
    assert response.status_code == 200
    assert response.json["category"]["id"] == category_id
    assert response.json["articles"]


def test_editor_can_manage_articles_but_not_users(client, sample_content):
    login(client, "editor", "editor123")
    assert client.get("/editor/articles").status_code == 200
    assert client.get("/admin/users").status_code == 403


def test_admin_pages_require_login(client):
    response = client.get("/admin/users")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_admin_can_create_replace_and_remove_article_image(client, app):
    login(client)
    client.post(
        "/editor/categories",
        data={"name": "Culture", "description": "Rubrique culturelle."},
        follow_redirects=True,
    )

    response = client.post(
        "/editor/articles/new",
        data={
            "title": "Article avec image",
            "summary": "Resume",
            "content": "Contenu",
            "category_id": "1",
            "published": "on",
            "image": (io.BytesIO(PNG_BYTES), "article.png"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200

    with app.app_context():
        article = services.get_article_by_slug("article-avec-image")
        assert article["image_filename"].endswith(".png")
        image_path = Path(app.config["UPLOAD_FOLDER"]) / article["image_filename"]
        assert image_path.exists()

    response = client.post(
        f"/editor/articles/{article['id']}/edit",
        data={
            "title": "Article avec image",
            "summary": "Resume",
            "content": "Contenu",
            "category_id": "1",
            "published": "on",
            "remove_image": "on",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        updated = services.get_article(article["id"])
        assert updated["image_filename"] is None
        assert not image_path.exists()


def test_soap_auth_and_list_users(client, sample_content):
    auth_response = client.post(
        "/soap",
        data=soap("authenticateUser", {"login": "admin", "password": "admin123"}),
        content_type="text/xml",
    )
    assert auth_response.status_code == 200
    assert b"<role>admin</role>" in auth_response.data

    users_response = client.post(
        "/soap",
        data=soap("listUsers", {"token": sample_content["token"]}),
        content_type="text/xml",
    )
    assert users_response.status_code == 200
    assert b"<login>admin</login>" in users_response.data


def test_soap_rejects_invalid_token(client):
    response = client.post(
        "/soap",
        data=soap("listUsers", {"token": "BAD"}),
        content_type="text/xml",
    )
    assert response.status_code == 401
    assert b"Jeton" in response.data


def test_admin_can_delete_user_with_articles(client, sample_content):
    login(client)
    editor_id = sample_content["editor"]["id"]
    response = client.post(f"/admin/users/{editor_id}/delete", follow_redirects=True)
    assert response.status_code == 200
    assert b"Utilisateur supprime" in response.data
    assert client.get("/articles/architecture-propre-pour-une-redaction").status_code == 200


def test_editor_can_delete_category_with_articles(client, sample_content):
    login(client, "editor", "editor123")
    category_id = sample_content["category"]["id"]
    response = client.post(f"/editor/categories/{category_id}/delete", follow_redirects=True)
    assert response.status_code == 200
    assert b"Categorie supprimee" in response.data
    assert client.get("/articles/architecture-propre-pour-une-redaction").status_code == 200
