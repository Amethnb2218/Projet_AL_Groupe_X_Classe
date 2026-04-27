from __future__ import annotations

from xml.etree.ElementTree import Element, SubElement, tostring

from flask import Blueprint, Response, jsonify, request

from . import services

bp = Blueprint("api", __name__, url_prefix="/api")


def xml_response(root: Element) -> Response:
    body = b'<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(root, encoding="utf-8")
    return Response(body, mimetype="application/xml")


def prefers_xml() -> bool:
    explicit_format = request.args.get("format", "json").lower()
    if explicit_format == "xml":
        return True
    if explicit_format == "json":
        return False
    return request.accept_mimetypes.best == "application/xml"


def append_article(parent: Element, article) -> None:
    data = services.article_to_dict(article)
    item = SubElement(parent, "article", id=str(data["id"]))
    for key in ("title", "slug", "summary", "content", "created_at", "updated_at"):
        SubElement(item, key).text = str(data[key])
    SubElement(item, "image_filename").text = data["image_filename"] or ""
    SubElement(item, "published").text = "true" if data["published"] else "false"
    category = SubElement(item, "category", id=str(data["category"]["id"]))
    SubElement(category, "name").text = data["category"]["name"]
    if data["category"]["slug"]:
        SubElement(category, "slug").text = data["category"]["slug"]
    SubElement(item, "author").text = data["author"]


@bp.route("/articles")
def articles():
    rows = services.list_articles()
    if prefers_xml():
        root = Element("articles")
        for row in rows:
            append_article(root, row)
        return xml_response(root)
    return jsonify({"articles": [services.article_to_dict(row) for row in rows]})


@bp.route("/articles/grouped")
def grouped_articles():
    categories = []
    for category in services.list_categories():
        article_rows = services.list_articles(category_id=category["id"])
        categories.append(
            {
                "id": category["id"],
                "name": category["name"],
                "slug": category["slug"],
                "description": category["description"],
                "articles": [services.article_to_dict(row) for row in article_rows],
            }
        )

    if prefers_xml():
        root = Element("categories")
        for category in categories:
            category_node = SubElement(root, "category", id=str(category["id"]))
            SubElement(category_node, "name").text = category["name"]
            SubElement(category_node, "slug").text = category["slug"]
            SubElement(category_node, "description").text = category["description"]
            articles_node = SubElement(category_node, "articles")
            for article in category["articles"]:
                item = SubElement(articles_node, "article", id=str(article["id"]))
                SubElement(item, "title").text = article["title"]
                SubElement(item, "slug").text = article["slug"]
                SubElement(item, "summary").text = article["summary"]
                SubElement(item, "image_filename").text = article["image_filename"] or ""
        return xml_response(root)

    return jsonify({"categories": categories})


@bp.route("/categories/<int:category_id>/articles")
def category_articles(category_id: int):
    category = services.get_category(category_id)
    if category is None:
        return jsonify({"error": "Categorie introuvable."}), 404
    rows = services.list_articles(category_id=category_id)
    if prefers_xml():
        root = Element("category", id=str(category["id"]))
        SubElement(root, "name").text = category["name"]
        SubElement(root, "slug").text = category["slug"]
        articles_node = SubElement(root, "articles")
        for row in rows:
            append_article(articles_node, row)
        return xml_response(root)
    return jsonify(
        {
            "category": {
                "id": category["id"],
                "name": category["name"],
                "slug": category["slug"],
                "description": category["description"],
            },
            "articles": [services.article_to_dict(row) for row in rows],
        }
    )
