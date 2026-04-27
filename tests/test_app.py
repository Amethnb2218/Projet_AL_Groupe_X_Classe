from __future__ import annotations

import pytest

from news_app import create_app
from news_app.database import init_db


@pytest.fixture()
def app(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.sqlite")})
    with app.app_context():
        init_db()
    return app


@pytest.fixture()
def client(app):
    return app.test_client()


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


def test_home_lists_articles_and_pagination(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Derniers articles" in response.data
    assert b"Suivant" in response.data


def test_article_detail_from_title_link(client):
    response = client.get("/articles/architecture-logicielle-medias")
    assert response.status_code == 200
    assert b"architecture logicielle" in response.data.lower()


def test_rest_articles_json_and_xml(client):
    json_response = client.get("/api/articles")
    assert json_response.status_code == 200
    assert json_response.json["articles"]

    xml_response = client.get("/api/articles?format=xml")
    assert xml_response.status_code == 200
    assert xml_response.mimetype == "application/xml"
    assert b"<articles>" in xml_response.data


def test_rest_articles_by_category(client):
    response = client.get("/api/categories/1/articles")
    assert response.status_code == 200
    assert response.json["category"]["id"] == 1
    assert response.json["articles"]


def test_editor_can_manage_articles_but_not_users(client):
    login(client, "editor", "editor123")
    assert client.get("/editor/articles").status_code == 200
    assert client.get("/admin/users").status_code == 403


def test_admin_pages_require_login(client):
    response = client.get("/admin/users")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_soap_auth_and_list_users(client):
    auth_response = client.post(
        "/soap",
        data=soap("authenticateUser", {"login": "admin", "password": "admin123"}),
        content_type="text/xml",
    )
    assert auth_response.status_code == 200
    assert b"<role>admin</role>" in auth_response.data

    users_response = client.post(
        "/soap",
        data=soap("listUsers", {"token": "DEMO-ADMIN-TOKEN"}),
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


def test_admin_can_delete_user_with_articles(client):
    login(client)
    response = client.post("/admin/users/2/delete", follow_redirects=True)
    assert response.status_code == 200
    assert b"Utilisateur supprime" in response.data
    assert client.get("/articles/api-redactions").status_code == 200


def test_editor_can_delete_category_with_articles(client):
    login(client, "editor", "editor123")
    response = client.post("/editor/categories/1/delete", follow_redirects=True)
    assert response.status_code == 200
    assert b"Categorie supprimee" in response.data
    assert client.get("/articles/api-redactions").status_code == 200
