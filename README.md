# Projet d'architecture logicielle - site d'actualite

Ce depot realise les exigences du PDF : site web d'actualite, profils visiteur/editeur/administrateur, services REST, service SOAP protege par jeton et client Python de gestion des utilisateurs.

## Installation

```powershell
python -m pip install -r requirements.txt
flask --app app init-db
flask --app app run
```

Le site sera disponible sur `http://127.0.0.1:5000`.

Commandes equivalentes avec npm :

```powershell
npm run setup
npm run dev
```

Comptes de demonstration :

- Administrateur : `admin` / `admin123`
- Editeur : `editor` / `editor123`

Jeton SOAP de demonstration : `DEMO-ADMIN-TOKEN`

## Fonctionnalites web

- Accueil avec les derniers articles et pagination `Precedent` / `Suivant`.
- Consultation du detail d'un article en cliquant sur son titre.
- Consultation des articles par categorie.
- Connexion des editeurs et administrateurs.
- Gestion des articles et categories par les editeurs.
- Gestion des utilisateurs et des jetons SOAP par les administrateurs.

## Services REST

Les endpoints retournent du JSON par defaut et du XML avec `?format=xml`.

- `GET /api/articles`
- `GET /api/articles/grouped`
- `GET /api/categories/<id>/articles`

Exemple :

```powershell
curl "http://127.0.0.1:5000/api/articles?format=xml"
```

## Service SOAP

Endpoint : `POST /soap`

Operations :

- `authenticateUser(login, password)`
- `listUsers(token)`
- `addUser(token, login, full_name, role, password)`
- `updateUser(token, id, login, full_name, role, password optionnel)`
- `deleteUser(token, id)`

Une description simplifiee est disponible sur `GET /soap?wsdl`.

Exemple de requete :

```xml
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <listUsers>
      <token>DEMO-ADMIN-TOKEN</token>
    </listUsers>
  </soap:Body>
</soap:Envelope>
```

## Client Python

Lancez le serveur Flask, puis :

```powershell
python client.py
```

Le client demande le login/mot de passe, verifie que l'utilisateur est administrateur via SOAP, puis demande un jeton SOAP pour lister, ajouter, modifier ou supprimer les utilisateurs.

## Tests

```powershell
pytest
```
