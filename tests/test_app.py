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
        category = services.create_category("Technologie", "Articles sur le numérique.")
        editor = services.create_user("editor", "Éditeur", "editor", "editor123")
        article = services.create_article(
            "Architecture propre pour une rédaction",
            "Un article de test publié pour vérifier les parcours publics.",
            "Contenu complet de l'article utilisé par les tests.",
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
    assert "Aucun article publié".encode("utf-8") in response.data

    categories = client.get("/api/articles/grouped")
    assert categories.status_code == 200
    assert categories.json["categories"] == []


def test_frontend_uses_images_and_keeps_hero_titles_readable(client):
    response = client.get("/static/styles.css")
    assert response.status_code == 200
    assert b"african-journalist-fallback.png" in response.data
    assert b".hero-copy h1" in response.data
    assert b"hyphens: none" in response.data

    image = client.get("/static/images/african-journalist-fallback.png")
    assert image.status_code == 200
    assert image.mimetype == "image/png"

    script = client.get("/static/editor-preview.js")
    assert script.status_code == 200
    assert b"data-image-input" in script.data


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
    for article in response.json["articles"]:
        image = client.get(f"/static/images/articles/{article['slug']}.png")
        assert image.status_code == 200
        assert image.mimetype == "image/png"

    categories = client.get("/api/articles/grouped")
    assert len(categories.json["categories"]) == 5

    home = client.get("/")
    assert b"/static/images/articles/cybersouverainete-equipes-techniques-reprennent-main.png" in home.data


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
    assert "image_hidden" in json_response.json["articles"][0]

    xml_response = client.get("/api/articles?format=xml")
    assert xml_response.status_code == 200
    assert xml_response.mimetype == "application/xml"
    assert b"<articles>" in xml_response.data
    assert b"<image_hidden>false</image_hidden>" in xml_response.data


def test_rest_grouped_and_category_articles_support_xml(client, sample_content):
    grouped = client.get("/api/articles/grouped?format=xml")
    assert grouped.status_code == 200
    assert grouped.mimetype == "application/xml"
    assert b"<categories>" in grouped.data
    assert b"image_filename" in grouped.data

    category_id = sample_content["category"]["id"]
    category = client.get(f"/api/categories/{category_id}/articles?format=xml")
    assert category.status_code == 200
    assert category.mimetype == "application/xml"
    assert b"<category" in category.data
    assert b"<articles>" in category.data


def test_rest_articles_by_category(client, sample_content):
    category_id = sample_content["category"]["id"]
    response = client.get(f"/api/categories/{category_id}/articles")
    assert response.status_code == 200
    assert response.json["category"]["id"] == category_id
    assert response.json["articles"]


def test_editor_can_manage_articles_but_not_users(client, sample_content):
    login(client, "editor", "editor123")
    articles = client.get("/editor/articles")
    assert articles.status_code == 200
    assert b"table-thumb large" in articles.data
    assert b"admin-table" in articles.data
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
            "summary": "Résumé",
            "content": "Contenu",
            "category_id": "1",
            "published": "on",
            "image": (io.BytesIO(PNG_BYTES), "article.png"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"editor-preview.js" in response.data
    assert b"data-image-input" in response.data

    with app.app_context():
        article = services.get_article_by_slug("article-avec-image")
        assert article["image_filename"].endswith(".png")
        image_path = Path(app.config["UPLOAD_FOLDER"]) / article["image_filename"]
        assert image_path.exists()

    response = client.post(
        f"/editor/articles/{article['id']}/edit",
        data={
            "title": "Article avec image",
            "summary": "Résumé",
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
        assert updated["image_hidden"]
        assert not image_path.exists()


def test_admin_can_hide_seeded_article_image_and_restore_upload(client, app):
    runner = app.test_cli_runner()
    result = runner.invoke(args=["seed-content"])
    assert result.exit_code == 0
    login(client)

    with app.app_context():
        article = services.get_article_by_slug("cybersouverainete-equipes-techniques-reprennent-main")
        article_id = article["id"]
        category_id = article["category_id"]
        form_data = {
            "title": article["title"],
            "summary": article["summary"],
            "content": article["content"],
            "category_id": str(category_id),
            "published": "on",
        }

    edit_page = client.get(f"/editor/articles/{article_id}/edit")
    assert edit_page.status_code == 200
    assert b"Retirer l'image actuelle" in edit_page.data

    response = client.post(
        f"/editor/articles/{article_id}/edit",
        data={**form_data, "remove_image": "on"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    home = client.get("/")
    assert b"/static/images/articles/cybersouverainete-equipes-techniques-reprennent-main.png" not in home.data
    assert b"media-placeholder" in home.data

    with app.app_context():
        hidden = services.get_article(article_id)
        assert hidden["image_filename"] is None
        assert hidden["image_hidden"]

    response = client.post(
        f"/editor/articles/{article_id}/edit",
        data={**form_data, "image": (io.BytesIO(PNG_BYTES), "restauree.png")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        restored = services.get_article(article_id)
        assert restored["image_filename"].endswith(".png")
        assert not restored["image_hidden"]
        assert (Path(app.config["UPLOAD_FOLDER"]) / restored["image_filename"]).exists()


def test_admin_can_create_replace_and_remove_category_image(client, app):
    login(client)
    response = client.post(
        "/editor/categories",
        data={
            "name": "Rubrique imagee",
            "description": "Une rubrique avec visuel.",
            "image": (io.BytesIO(PNG_BYTES), "rubrique.png"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"editor-preview.js" in response.data
    assert b"data-image-input" in response.data

    with app.app_context():
        category = services.get_category_by_slug("rubrique-imagee")
        category_id = category["id"]
        assert category["image_filename"].endswith(".png")
        first_image = Path(app.config["UPLOAD_FOLDER"]) / category["image_filename"]
        assert first_image.exists()

    edit_page = client.get(f"/editor/categories/{category_id}/edit")
    assert edit_page.status_code == 200
    assert b"data-image-preview-img" in edit_page.data

    response = client.post(
        f"/editor/categories/{category_id}/edit",
        data={
            "name": "Rubrique imagee",
            "description": "Une rubrique avec visuel.",
            "image": (io.BytesIO(PNG_BYTES), "rubrique-remplacee.png"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        replaced = services.get_category(category_id)
        second_image = Path(app.config["UPLOAD_FOLDER"]) / replaced["image_filename"]
        assert second_image.exists()
        assert not first_image.exists()

    response = client.post(
        f"/editor/categories/{category_id}/edit",
        data={
            "name": "Rubrique imagee",
            "description": "Une rubrique avec visuel.",
            "remove_image": "on",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        updated = services.get_category(category_id)
        assert updated["image_filename"] is None
        assert not second_image.exists()


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


def test_soap_token_allows_full_user_management(client, sample_content, app):
    token = sample_content["token"]
    added = client.post(
        "/soap",
        data=soap(
            "addUser",
            {
                "token": token,
                "login": "soap-editor",
                "full_name": "Éditeur SOAP",
                "role": "editor",
                "password": "secret123",
            },
        ),
        content_type="text/xml",
    )
    assert added.status_code == 201
    assert b"<login>soap-editor</login>" in added.data

    with app.app_context():
        user = services.authenticate("soap-editor", "secret123")
        user_id = user["id"]

    updated = client.post(
        "/soap",
        data=soap(
            "updateUser",
            {
                "token": token,
                "id": str(user_id),
                "login": "soap-admin-test",
                "full_name": "Administrateur SOAP",
                "role": "admin",
                "password": "",
            },
        ),
        content_type="text/xml",
    )
    assert updated.status_code == 200
    assert b"<role>admin</role>" in updated.data

    deleted = client.post(
        "/soap",
        data=soap("deleteUser", {"token": token, "id": str(user_id)}),
        content_type="text/xml",
    )
    assert deleted.status_code == 200
    assert f"<deleted>{user_id}</deleted>".encode() in deleted.data


def test_admin_can_delete_user_with_articles(client, sample_content):
    login(client)
    editor_id = sample_content["editor"]["id"]
    response = client.post(f"/admin/users/{editor_id}/delete", follow_redirects=True)
    assert response.status_code == 200
    assert "Utilisateur supprimé".encode("utf-8") in response.data
    assert client.get("/articles/architecture-propre-pour-une-redaction").status_code == 200


def test_editor_can_delete_category_with_articles(client, sample_content):
    login(client, "editor", "editor123")
    category_id = sample_content["category"]["id"]
    response = client.post(f"/editor/categories/{category_id}/delete", follow_redirects=True)
    assert response.status_code == 200
    assert "Catégorie supprimée".encode("utf-8") in response.data
    assert client.get("/articles/architecture-propre-pour-une-redaction").status_code == 200
