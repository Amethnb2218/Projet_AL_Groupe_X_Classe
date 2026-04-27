# Projet d'architecture logicielle - site d'actualite

Ce depot realise le cahier des charges du PDF : site web d'actualite, profils visiteur/editeur/administrateur, services REST, service SOAP protege par jeton et client Python de gestion des utilisateurs.

Le projet ne precharge pas de fausses actualites, categories, editeurs ou jetons. Apres initialisation, seul le compte administrateur initial existe afin de pouvoir creer les donnees depuis l'interface, comme dans un vrai back-office.

## Installation

```powershell
python -m pip install -r requirements.txt
flask --app app init-db
flask --app app run
```

Commandes equivalentes avec npm :

```powershell
npm run setup
npm run dev
```

Le site sera disponible sur `http://127.0.0.1:5000`.

Compte initial :

- Administrateur : `admin` / `admin123`

## Parcours attendu

1. Connectez-vous avec le compte administrateur initial.
2. Creez les editeurs dans `Utilisateurs`.
3. Creez les categories dans `Gestion categories`.
4. Creez les articles dans `Articles`, avec possibilite d'ajouter, remplacer ou retirer une image.
5. Generez les jetons SOAP dans `Jetons` avant d'utiliser les operations SOAP protegees.

## Fonctionnalites web

- Accueil avec les derniers articles et pagination `Precedent` / `Suivant`.
- Consultation du detail d'un article en cliquant sur son titre.
- Consultation des articles par categorie.
- Gestion des articles et categories par les editeurs.
- Gestion des utilisateurs par les administrateurs.
- Generation et suppression des jetons SOAP par les administrateurs.
- Upload, changement et suppression d'image pour chaque article.

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
      <token>JETON_GENERE_DANS_L_ADMINISTRATION</token>
    </listUsers>
  </soap:Body>
</soap:Envelope>
```

## Client Python

Lancez le serveur Flask, puis :

```powershell
python client.py
```

Le client demande le login/mot de passe, verifie que l'utilisateur est administrateur via SOAP, puis demande un jeton SOAP genere dans l'administration pour lister, ajouter, modifier ou supprimer les utilisateurs.

## Tests

```powershell
pytest
```
