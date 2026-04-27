# Projet d'architecture logicielle - site d'actualité

Ce dépôt réalise le cahier des charges du PDF : site web d'actualité, profils visiteur/éditeur/administrateur, services REST, service SOAP protégé par jeton et client Python de gestion des utilisateurs.

Le projet ne précharge pas de fausses actualités, catégories, éditeurs ou jetons. Après initialisation, seul le compte administrateur initial existe afin de pouvoir créer les données depuis l'interface, comme dans un vrai back-office.

## Installation

```powershell
python -m pip install -r requirements.txt
flask --app app init-db
flask --app app run
```

Commandes équivalentes avec npm :

```powershell
npm run setup
npm run dev
```

Le site sera disponible sur `http://127.0.0.1:5000`.

Compte initial :

- Administrateur : `admin` / `admin123`

## Ajouter des articles

L'initialisation reste volontairement minimale. Pour remplir la base locale avec un lot d'articles éditoriaux, lancez :

```powershell
flask --app app seed-content
```

Cette commande crée des catégories et huit articles publiés. Elle est idempotente : la relancer ne duplique pas les articles déjà créés.

## Parcours attendu

1. Connectez-vous avec le compte administrateur initial.
2. Créez les éditeurs dans `Utilisateurs`.
3. Créez les catégories dans `Gestion catégories`.
4. Créez les articles dans `Articles`, avec possibilité d'ajouter, remplacer ou retirer une image.
5. Générez les jetons SOAP dans `Jetons` avant d'utiliser les opérations SOAP protégées.

## Fonctionnalités web

- Accueil avec les derniers articles et pagination `Précédent` / `Suivant`.
- Consultation du détail d'un article en cliquant sur son titre.
- Consultation des articles par catégorie.
- Gestion des articles et catégories par les éditeurs.
- Gestion des utilisateurs par les administrateurs.
- Génération et suppression des jetons SOAP par les administrateurs.
- Upload, changement et suppression d'image pour chaque article.

## Services REST

Les endpoints retournent du JSON par défaut et du XML avec `?format=xml`.

- `GET /api/articles`
- `GET /api/articles/grouped`
- `GET /api/categories/<id>/articles`

Exemple :

```powershell
curl "http://127.0.0.1:5000/api/articles?format=xml"
```

## Service SOAP

Endpoint : `POST /soap`

Opérations :

- `authenticateUser(login, password)`
- `listUsers(token)`
- `addUser(token, login, full_name, role, password)`
- `updateUser(token, id, login, full_name, role, password optionnel)`
- `deleteUser(token, id)`

Une description simplifiée est disponible sur `GET /soap?wsdl`.

Exemple de requête :

```xml
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <listUsers>
      <token>JETON_GÉNÉRÉ_DANS_L_ADMINISTRATION</token>
    </listUsers>
  </soap:Body>
</soap:Envelope>
```

## Client Python

Lancez le serveur Flask, puis :

```powershell
python client.py
```

Le client demande le login/mot de passe, vérifie que l'utilisateur est administrateur via SOAP, puis demande un jeton SOAP généré dans l'administration pour lister, ajouter, modifier ou supprimer les utilisateurs.

## Tests

```powershell
pytest
```
