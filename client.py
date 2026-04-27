from __future__ import annotations

import getpass
from xml.etree.ElementTree import Element, ParseError, SubElement, fromstring, tostring

import requests


SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def soap_payload(operation: str, **fields: str) -> bytes:
    envelope = Element(f"{{{SOAP_NS}}}Envelope")
    body = SubElement(envelope, f"{{{SOAP_NS}}}Body")
    op = SubElement(body, operation)
    for key, value in fields.items():
        if value is not None:
            SubElement(op, key).text = str(value)
    return tostring(envelope, encoding="utf-8", xml_declaration=True)


def find_first(root, name: str):
    for element in root.iter():
        if local_name(element.tag) == name:
            return element
    return None


def find_text(root, name: str, default: str = "") -> str:
    element = find_first(root, name)
    return element.text if element is not None and element.text is not None else default


def call_soap(base_url: str, operation: str, **fields: str):
    response = requests.post(
        base_url.rstrip("/") + "/soap",
        data=soap_payload(operation, **fields),
        headers={"Content-Type": "text/xml; charset=utf-8"},
        timeout=15,
    )
    try:
        root = fromstring(response.content)
    except ParseError as exc:
        raise RuntimeError(f"Reponse SOAP illisible: {exc}") from exc
    status = find_text(root, "status")
    if response.status_code >= 400 or status == "error":
        raise RuntimeError(find_text(root, "message", f"Erreur HTTP {response.status_code}"))
    return root


def users_from_response(root):
    users = []
    for node in root.iter():
        if local_name(node.tag) == "user":
            users.append(
                {
                    "id": node.attrib.get("id", ""),
                    "login": find_text(node, "login"),
                    "full_name": find_text(node, "full_name"),
                    "role": find_text(node, "role"),
                    "created_at": find_text(node, "created_at"),
                }
            )
    return users


def print_users(users) -> None:
    if not users:
        print("Aucun utilisateur.")
        return
    print("\nID | Login | Nom complet | Role")
    print("-" * 44)
    for user in users:
        print(f"{user['id']} | {user['login']} | {user['full_name']} | {user['role']}")


def prompt_role() -> str:
    role = input("Role (editor/admin) [editor]: ").strip() or "editor"
    if role not in {"editor", "admin"}:
        print("Role invalide, valeur editor utilisee.")
        return "editor"
    return role


def main() -> None:
    print("Client d'administration des utilisateurs - AL News")
    base_url = input("URL du site [http://127.0.0.1:5000]: ").strip() or "http://127.0.0.1:5000"
    login = input("Login: ").strip()
    password = getpass.getpass("Mot de passe: ")

    try:
        auth = call_soap(base_url, "authenticateUser", login=login, password=password)
    except RuntimeError as exc:
        print(f"Authentification refusee: {exc}")
        return

    role = find_text(auth, "role")
    if role != "admin":
        print("Acces refuse: seul un administrateur peut gerer les utilisateurs.")
        return

    token = getpass.getpass("Jeton SOAP administrateur: ").strip()
    print("Authentification reussie.")

    while True:
        print("\n1. Lister les utilisateurs")
        print("2. Ajouter un utilisateur")
        print("3. Modifier un utilisateur")
        print("4. Supprimer un utilisateur")
        print("0. Quitter")
        choice = input("Choix: ").strip()

        try:
            if choice == "1":
                root = call_soap(base_url, "listUsers", token=token)
                print_users(users_from_response(root))
            elif choice == "2":
                fields = {
                    "token": token,
                    "login": input("Login: ").strip(),
                    "full_name": input("Nom complet: ").strip(),
                    "role": prompt_role(),
                    "password": getpass.getpass("Mot de passe: "),
                }
                root = call_soap(base_url, "addUser", **fields)
                print_users(users_from_response(root))
            elif choice == "3":
                fields = {
                    "token": token,
                    "id": input("ID utilisateur: ").strip(),
                    "login": input("Nouveau login: ").strip(),
                    "full_name": input("Nouveau nom complet: ").strip(),
                    "role": prompt_role(),
                    "password": getpass.getpass("Nouveau mot de passe (vide = inchange): "),
                }
                root = call_soap(base_url, "updateUser", **fields)
                print_users(users_from_response(root))
            elif choice == "4":
                user_id = input("ID utilisateur a supprimer: ").strip()
                call_soap(base_url, "deleteUser", token=token, id=user_id)
                print("Utilisateur supprime.")
            elif choice == "0":
                break
            else:
                print("Choix invalide.")
        except RuntimeError as exc:
            print(f"Erreur: {exc}")


if __name__ == "__main__":
    main()
