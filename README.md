# Projet d'architecture logicielle - AL News

AL News est un site d'actualite complet realise pour le cours d'architecture logicielle. Le projet couvre les trois parties demandees dans le sujet :

- un site web d'actualite avec consultation, categories, pagination et back-office ;
- des services web REST et SOAP ;
- une application cliente Python pour gerer les utilisateurs via SOAP.

Le projet est developpe avec Flask, SQLite, des templates Jinja, du CSS responsive et une suite de tests Pytest.

## Objectif du projet

L'objectif est de montrer une architecture logicielle claire autour d'une application d'actualite :

- separation entre routes web, services metier, base de donnees, API REST et service SOAP ;
- gestion de plusieurs profils utilisateurs ;
- exposition des fonctionnalites metier a d'autres applications ;
- client externe utilisant les services web ;
- interface responsive utilisable sur ordinateur, tablette et telephone.

## Fonctionnalites realisees

### Site web d'actualite

- Page d'accueil avec les derniers articles publies.
- Description sommaire pour chaque article.
- Pagination avec boutons `Precedent` et `Suivant`.
- Clic sur le titre ou la carte d'un article pour consulter le detail.
- Consultation des articles par categorie.
- Design responsive sans defilement horizontal sur mobile.
- Images distinctes pour les articles editoriaux.
- Ajout, remplacement, suppression et previsualisation d'images pour les articles.
- Ajout, remplacement, suppression et previsualisation d'images pour les categories.

### Profils utilisateurs

- Visiteur simple :
  - consulte l'accueil ;
  - consulte les articles ;
  - filtre les articles par categorie ;
  - consulte les services REST publics.

- Editeur :
  - possede toutes les fonctionnalites du visiteur ;
  - se connecte avec login et mot de passe ;
  - liste, ajoute, modifie et supprime les articles ;
  - liste, ajoute, modifie et supprime les categories.

- Administrateur :
  - possede toutes les fonctionnalites de l'editeur ;
  - liste, ajoute, modifie et supprime les utilisateurs ;
  - genere et supprime les jetons SOAP ;
  - autorise l'acces aux operations SOAP protegees.

### Services web

- REST :
  - liste de tous les articles en JSON ou XML ;
  - liste des articles regroupes par categories en JSON ou XML ;
  - liste des articles d'une categorie donnee en JSON ou XML.

- SOAP :
  - authentification d'un utilisateur par login et mot de passe ;
  - liste des utilisateurs avec jeton ;
  - ajout d'un utilisateur avec jeton ;
  - modification d'un utilisateur avec jeton ;
  - suppression d'un utilisateur avec jeton.

### Application cliente Python

Le fichier `client.py` est une application console. Elle :

- demande l'URL du site ;
- demande le login et le mot de passe ;
- appelle le service SOAP `authenticateUser` ;
- verifie que l'utilisateur est administrateur ;
- demande un jeton SOAP ;
- permet de lister, ajouter, modifier et supprimer les utilisateurs via SOAP.

## Correspondance avec le cahier des charges

| Exigence du sujet | Realisation dans le projet |
| --- | --- |
| Page d'accueil avec derniers articles | Route `/`, template `home.html`, service `list_articles` |
| Description sommaire des articles | Champ `summary`, affiche sur accueil et categories |
| Boutons suivant et precedent | Pagination sur accueil et pages de categories |
| Clic sur le titre pour consulter le detail | Route `/articles/<slug>` |
| Consultation par categorie | Routes `/categories` et `/categories/<slug>` |
| Visiteurs simples | Acces public aux pages de consultation |
| Editeurs | Role `editor`, acces au back-office articles/categories |
| Administrateurs | Role `admin`, acces utilisateurs et jetons |
| Gestion articles | Lister, ajouter, modifier, supprimer, publier, images |
| Gestion categories | Lister, ajouter, modifier, supprimer, images |
| Gestion utilisateurs | Lister, ajouter, modifier, supprimer |
| Jetons d'authentification | Page `/admin/tokens` |
| SOAP authentification | Operation `authenticateUser` |
| SOAP utilisateurs avec jeton | Operations `listUsers`, `addUser`, `updateUser`, `deleteUser` |
| REST liste articles | `GET /api/articles` |
| REST articles par categories | `GET /api/articles/grouped` |
| REST articles d'une categorie | `GET /api/categories/<id>/articles` |
| JSON ou XML | Parametre `?format=json` ou `?format=xml` |
| Client Java ou Python | Client Python `client.py` |

## Structure du projet

```text
architecturelogicielle/
├── app.py                         # Point d'entree Flask
├── client.py                      # Client Python SOAP
├── package.json                   # Commandes npm pratiques
├── requirements.txt               # Dependances Python
├── README.md                      # Documentation du projet
├── news_app/
│   ├── __init__.py                # Creation de l'application Flask
│   ├── api.py                     # API REST JSON/XML
│   ├── database.py                # Connexion, initialisation et seed
│   ├── routes.py                  # Routes web et back-office
│   ├── schema.sql                 # Schema SQLite
│   ├── services.py                # Logique metier
│   ├── soap.py                    # Service SOAP
│   ├── static/
│   │   ├── styles.css             # Design responsive
│   │   ├── editor-preview.js      # Previsualisation d'images
│   │   └── images/                # Images du site
│   └── templates/                 # Templates Jinja
└── tests/
    └── test_app.py                # Tests automatises
```

## Installation

### Prerequis

- Python 3.10 ou plus recent.
- pip.
- Node.js est optionnel mais pratique pour lancer les scripts `npm`.

### Installation avec Python

```powershell
python -m pip install -r requirements.txt
python -m flask --app app init-db
python -m flask --app app run --debug
```

Le site est alors disponible sur :

```text
http://127.0.0.1:5000
```

### Installation avec npm

```powershell
npm run setup
npm run dev
```

Si PowerShell bloque `npm` avec une erreur de politique d'execution, utilisez :

```powershell
npm.cmd run setup
npm.cmd run dev
```

## Compte initial

Apres `init-db`, un seul compte existe :

| Role | Login | Mot de passe |
| --- | --- | --- |
| Administrateur | `admin` | `admin123` |

Ce choix evite de precharger de faux utilisateurs. Les editeurs et autres administrateurs se creent depuis l'interface.

## Ajouter les articles editoriaux fournis

L'initialisation de base reste minimale. Pour remplir le site avec les categories et articles editoriaux prepares pour la demonstration :

```powershell
python -m flask --app app seed-content
```

Commande equivalente avec Flask direct :

```powershell
flask --app app seed-content
```

La commande est idempotente : elle peut etre relancee sans dupliquer les articles.

## Tester sur un telephone ou un autre appareil

Pour ouvrir le site depuis un telephone, une tablette ou un autre ordinateur, les appareils doivent etre connectes au meme reseau Wi-Fi que l'ordinateur qui lance Flask.

### 1. Lancer le serveur en mode reseau local

```powershell
npm run dev:lan
```

ou, si PowerShell bloque `npm` :

```powershell
npm.cmd run dev:lan
```

Commande Python equivalente :

```powershell
python -m flask --app app run --debug --host 0.0.0.0
```

### 2. Trouver l'adresse IP de l'ordinateur

Dans PowerShell :

```powershell
Get-NetIPAddress -AddressFamily IPv4
```

Cherchez l'adresse de l'interface `Wi-Fi`. Sur cette machine, l'adresse detectee est :

```text
192.168.12.155
```

### 3. Ouvrir le site depuis l'autre appareil

Dans le navigateur du telephone ou de l'autre ordinateur :

```text
http://192.168.12.155:5000
```

Si l'adresse change, remplacez `192.168.12.155` par l'adresse IPv4 actuelle de votre Wi-Fi.

### 4. Si la page ne s'ouvre pas

- Verifiez que les deux appareils sont sur le meme Wi-Fi.
- Verifiez que le serveur Flask est toujours lance.
- Autorisez Python ou Flask dans le pare-feu Windows si une fenetre de securite apparait.
- Si le port `5000` est deja utilise, lancez le mode LAN sur `5001` :

```powershell
npm.cmd run dev:lan:5001
```

Puis ouvrez :

```text
http://192.168.12.155:5001
```

- Vous pouvez aussi relancer le mode LAN standard avec :

```powershell
npm.cmd run dev:lan
```

## Parcours de demonstration recommande

1. Lancer le site avec `npm.cmd run dev`.
2. Ouvrir `http://127.0.0.1:5000`.
3. Verifier l'accueil, les articles, les categories et la pagination.
4. Se connecter avec `admin` / `admin123`.
5. Aller dans `Articles` :
   - ajouter un article ;
   - modifier un article ;
   - ajouter, remplacer et retirer une image ;
   - verifier la previsualisation de l'image.
6. Aller dans `Gestion categories` :
   - ajouter une categorie ;
   - modifier une categorie ;
   - ajouter, remplacer et retirer une image.
7. Aller dans `Utilisateurs` :
   - ajouter un editeur ;
   - modifier son role ;
   - supprimer un utilisateur.
8. Aller dans `Jetons` :
   - generer un jeton SOAP ;
   - l'utiliser dans le client Python.
9. Tester les endpoints REST en JSON et XML.
10. Lancer `python client.py` pour verifier le client SOAP.

## Services REST

Les routes REST retournent du JSON par defaut. Le format XML est disponible avec `?format=xml`.

### Liste de tous les articles

```powershell
curl "http://127.0.0.1:5000/api/articles"
curl "http://127.0.0.1:5000/api/articles?format=xml"
```

### Articles groupes par categories

```powershell
curl "http://127.0.0.1:5000/api/articles/grouped"
curl "http://127.0.0.1:5000/api/articles/grouped?format=xml"
```

### Articles d'une categorie

```powershell
curl "http://127.0.0.1:5000/api/categories/1/articles"
curl "http://127.0.0.1:5000/api/categories/1/articles?format=xml"
```

## Service SOAP

Endpoint :

```text
POST /soap
```

Aide :

```text
GET /soap
```

Description simplifiee :

```text
GET /soap?wsdl
```

### Operations SOAP

| Operation | Protection | Description |
| --- | --- | --- |
| `authenticateUser(login, password)` | Publique | Authentifie un utilisateur |
| `listUsers(token)` | Jeton requis | Liste les utilisateurs |
| `addUser(token, login, full_name, role, password)` | Jeton requis | Ajoute un utilisateur |
| `updateUser(token, id, login, full_name, role, password)` | Jeton requis | Modifie un utilisateur |
| `deleteUser(token, id)` | Jeton requis | Supprime un utilisateur |

Les jetons se generent dans l'interface administrateur : `Jetons`.

Exemple de requete SOAP :

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

Lancer le serveur Flask, puis :

```powershell
python client.py
```

Le client demande :

1. l'URL du site ;
2. le login ;
3. le mot de passe ;
4. le jeton SOAP administrateur.

Ensuite il propose :

- lister les utilisateurs ;
- ajouter un utilisateur ;
- modifier un utilisateur ;
- supprimer un utilisateur.

## Tests

Lancer toute la suite de tests :

```powershell
pytest -q
```

ou avec npm :

```powershell
npm.cmd run test
```

Les tests couvrent notamment :

- l'initialisation minimale de la base ;
- l'accueil, les articles, les categories et la pagination ;
- les roles editeur et administrateur ;
- l'upload, le remplacement, la suppression et la previsualisation des images ;
- les routes REST en JSON et XML ;
- le service SOAP avec authentification, liste, ajout, modification et suppression ;
- la persistance de la suppression d'une image ;
- le responsive des tableaux d'administration.

## Commandes utiles

| Commande | Utilite |
| --- | --- |
| `npm.cmd run setup` | Installer les dependances et initialiser la base |
| `npm.cmd run dev` | Lancer le site en local |
| `npm.cmd run dev:lan` | Lancer le site pour tester depuis un autre appareil |
| `npm.cmd run dev:lan:5001` | Lancer le site sur le reseau local si le port 5000 est occupe |
| `npm.cmd run test` | Lancer les tests |
| `npm.cmd run client` | Lancer le client Python |
| `python -m flask --app app seed-content` | Ajouter les articles editoriaux |

## Notes importantes

- Le dossier `instance/` contient la base SQLite locale et les images uploadees. Il n'est pas versionne dans Git.
- Les images editoriales statiques sont versionnees dans `news_app/static/images/articles/`.
- Les donnees initiales restent volontairement minimales : seul l'administrateur initial est cree par `init-db`.
- Les articles de demonstration sont ajoutes uniquement avec `seed-content`.
- Le design est responsive : les tableaux deviennent des cartes sur mobile pour eviter le defilement horizontal.
