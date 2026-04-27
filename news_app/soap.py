from __future__ import annotations

import sqlite3
from xml.etree.ElementTree import Element, ParseError, SubElement, fromstring, tostring

from flask import Blueprint, Response, request

from . import services

bp = Blueprint("soap", __name__)

SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def first_child(element: Element):
    for child in list(element):
        return child
    return None


def child_text(element: Element, name: str, default: str = "") -> str:
    for child in list(element):
        if local_name(child.tag) == name:
            return child.text or default
    return default


def find_body(root: Element):
    for child in list(root):
        if local_name(child.tag) == "Body":
            return child
    return root


def to_response(response_node: Element, status_code: int = 200) -> Response:
    soap_root = Element(f"{{{SOAP_NS}}}Envelope")
    body = SubElement(soap_root, f"{{{SOAP_NS}}}Body")
    body.append(response_node)
    body_bytes = b'<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(soap_root, encoding="utf-8")
    return Response(body_bytes, status=status_code, mimetype="text/xml")


def success(operation: str):
    return Element(f"{operation}Response")


def failure(operation: str, message: str, status_code: int = 400) -> Response:
    response = success(operation)
    SubElement(response, "status").text = "error"
    SubElement(response, "message").text = message
    return to_response(response, status_code)


def add_user_node(parent: Element, user) -> None:
    node = SubElement(parent, "user", id=str(user["id"]))
    SubElement(node, "login").text = user["login"]
    SubElement(node, "full_name").text = user["full_name"]
    SubElement(node, "role").text = user["role"]
    SubElement(node, "created_at").text = user["created_at"]


def require_token(operation: str, request_node: Element):
    token = child_text(request_node, "token")
    if not services.is_valid_token(token):
        return failure(operation, "Jeton d'authentification invalide.", 401)
    return None


@bp.route("/soap", methods=("GET", "POST"))
def soap_endpoint():
    if request.method == "GET":
        if "wsdl" in request.args:
            return Response(WSDL, mimetype="text/xml")
        return Response(SOAP_HELP, mimetype="text/plain")

    try:
        root = fromstring(request.data)
    except ParseError:
        return failure("soap", "Requête XML invalide.", 400)

    body = find_body(root)
    operation_node = first_child(body)
    if operation_node is None:
        return failure("soap", "Opération SOAP manquante.", 400)

    operation = local_name(operation_node.tag)
    handlers = {
        "authenticateUser": handle_authenticate_user,
        "listUsers": handle_list_users,
        "addUser": handle_add_user,
        "updateUser": handle_update_user,
        "deleteUser": handle_delete_user,
    }
    handler = handlers.get(operation)
    if handler is None:
        return failure(operation, f"Opération inconnue : {operation}", 400)
    return handler(operation_node)


def handle_authenticate_user(node: Element) -> Response:
    user = services.authenticate(child_text(node, "login"), child_text(node, "password"))
    response = success("authenticateUser")
    if user is None:
        SubElement(response, "status").text = "error"
        SubElement(response, "message").text = "Identifiants incorrects."
        return to_response(response, 401)
    SubElement(response, "status").text = "success"
    add_user_node(response, user)
    SubElement(response, "is_admin").text = "true" if user["role"] == "admin" else "false"
    return to_response(response)


def handle_list_users(node: Element) -> Response:
    denied = require_token("listUsers", node)
    if denied:
        return denied
    response = success("listUsers")
    SubElement(response, "status").text = "success"
    users_node = SubElement(response, "users")
    for user in services.list_users():
        add_user_node(users_node, user)
    return to_response(response)


def handle_add_user(node: Element) -> Response:
    denied = require_token("addUser", node)
    if denied:
        return denied
    response = success("addUser")
    try:
        user = services.create_user(
            child_text(node, "login"),
            child_text(node, "full_name"),
            child_text(node, "role"),
            child_text(node, "password"),
        )
    except (sqlite3.IntegrityError, ValueError) as exc:
        return failure("addUser", str(exc), 400)
    SubElement(response, "status").text = "success"
    add_user_node(response, user)
    return to_response(response, 201)


def handle_update_user(node: Element) -> Response:
    denied = require_token("updateUser", node)
    if denied:
        return denied
    response = success("updateUser")
    try:
        user_id = int(child_text(node, "id"))
        user = services.update_user(
            user_id,
            child_text(node, "login"),
            child_text(node, "full_name"),
            child_text(node, "role"),
            child_text(node, "password") or None,
        )
    except (TypeError, ValueError, sqlite3.IntegrityError) as exc:
        return failure("updateUser", str(exc), 400)
    if user is None:
        return failure("updateUser", "Utilisateur introuvable.", 404)
    SubElement(response, "status").text = "success"
    add_user_node(response, user)
    return to_response(response)


def handle_delete_user(node: Element) -> Response:
    denied = require_token("deleteUser", node)
    if denied:
        return denied
    try:
        user_id = int(child_text(node, "id"))
        user = services.get_user(user_id)
        if user is None:
            return failure("deleteUser", "Utilisateur introuvable.", 404)
        if user["role"] == "admin" and services.count_admins() <= 1:
            return failure("deleteUser", "Impossible de supprimer le dernier administrateur.", 400)
        services.delete_user(user_id)
    except (TypeError, ValueError, sqlite3.IntegrityError) as exc:
        return failure("deleteUser", str(exc), 400)
    response = success("deleteUser")
    SubElement(response, "status").text = "success"
    SubElement(response, "deleted").text = str(user_id)
    return to_response(response)


SOAP_HELP = """Service SOAP disponible sur /soap

Opérations :
- authenticateUser(login, password)
- listUsers(token)
- addUser(token, login, full_name, role, password)
- updateUser(token, id, login, full_name, role, password optionnel)
- deleteUser(token, id)

Ajoutez ?wsdl à l'URL pour obtenir une description simplifiée.
"""

WSDL = """<?xml version="1.0" encoding="UTF-8"?>
<definitions name="NewsUserService"
  targetNamespace="urn:news-user-service"
  xmlns="http://schemas.xmlsoap.org/wsdl/"
  xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
  xmlns:tns="urn:news-user-service">
  <service name="NewsUserService">
    <documentation>Service SOAP de gestion des utilisateurs protégé par jeton.</documentation>
    <port name="NewsUserPort" binding="tns:NewsUserBinding">
      <soap:address location="/soap"/>
    </port>
  </service>
</definitions>
"""
