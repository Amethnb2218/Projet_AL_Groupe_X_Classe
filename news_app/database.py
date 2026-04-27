from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from flask import current_app, g
from werkzeug.security import generate_password_hash


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_error: Exception | None = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def init_db() -> None:
    db = get_db()
    schema_path = Path(__file__).with_name("schema.sql")
    db.executescript(schema_path.read_text(encoding="utf-8"))
    seed_db(db)
    db.commit()


def seed_db(db: sqlite3.Connection) -> None:
    now = utc_now()
    db.execute(
        """
        INSERT OR IGNORE INTO users (login, full_name, role, password_hash, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("admin", "Administrateur initial", "admin", generate_password_hash("admin123"), now),
    )


def seed_editorial_content() -> None:
    db = get_db()
    now = utc_now()
    admin = db.execute("SELECT id FROM users WHERE login = 'admin'").fetchone()
    if admin is None:
        seed_db(db)
        admin = db.execute("SELECT id FROM users WHERE login = 'admin'").fetchone()
    admin_id = admin["id"]

    categories = [
        ("Technologie", "technologie", "Architecture, innovation et usages numeriques."),
        ("Economie", "economie", "Entreprises, investissements et transformation des marches."),
        ("Culture", "culture", "Creation, medias, livres, festivals et nouveaux publics."),
        ("International", "international", "Cooperation, politiques publiques et enjeux mondiaux."),
        ("Sciences", "sciences", "Recherche, sante, environnement et donnees."),
    ]
    for name, slug, description in categories:
        db.execute(
            """
            INSERT OR IGNORE INTO categories (name, slug, description, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (name, slug, description, now),
        )

    category_ids = {
        row["name"]: row["id"] for row in db.execute("SELECT id, name FROM categories").fetchall()
    }

    articles = [
        (
            "Education numerique : les plateformes cherchent la fiabilite",
            "education-numerique-plateformes-fiabilite",
            "Les etablissements renforcent leurs outils en ligne pour mieux suivre les parcours des apprenants.",
            "Les plateformes educatives doivent supporter les inscriptions, les contenus, les evaluations et les statistiques sans perdre en clarte. Une architecture bien separee aide les equipes a faire evoluer les modules de cours, d'administration et de reporting. Elle permet aussi de connecter les services a d'autres applications tout en gardant des droits d'acces coherents.",
            "Sciences",
        ),
        (
            "Presse locale : les donnees ouvertes changent l'enquete",
            "presse-locale-donnees-ouvertes",
            "Les redactions utilisent davantage les jeux de donnees publics pour produire des formats utiles.",
            "Les journalistes croisent des donnees ouvertes avec leurs observations de terrain pour expliquer les transports, les budgets, la sante ou l'environnement. Les sites d'actualite doivent donc publier des contenus consultables, classes par categorie et reutilisables par des services web. Cette logique donne plus de valeur au travail editorial.",
            "Economie",
        ),
        (
            "Sante numerique : proteger les parcours patients",
            "sante-numerique-proteger-parcours-patients",
            "Les applications de sante rappellent l'importance des roles, des jetons et de la tracabilite.",
            "La transformation numerique de la sante exige des interfaces simples et des controles stricts. Les administrateurs gerent les acces, les editeurs maintiennent les contenus et les visiteurs consultent les informations publiques. Cette separation des responsabilites reduit les erreurs et renforce la confiance dans les services.",
            "Sciences",
        ),
        (
            "Cooperation regionale : connecter les services publics",
            "cooperation-regionale-connecter-services-publics",
            "Les administrations misent sur des interfaces interoperables pour simplifier les demarches.",
            "Les services publics gagnent en efficacite lorsqu'ils exposent des informations fiables a travers des API. Les applications externes peuvent lire les donnees sans dupliquer la logique interne. REST facilite la consultation, tandis que SOAP reste utile pour les operations encadrees par un contrat strict et un jeton d'authentification.",
            "International",
        ),
        (
            "Culture numerique : les festivals inventent un nouveau public",
            "culture-numerique-festivals-nouveau-public",
            "Les evenements hybrides rapprochent les spectateurs en ligne et sur place.",
            "Les festivals utilisent les plateformes web pour publier des programmes, partager des critiques et conserver des archives accessibles. Un bon site editorial ne se limite pas a afficher des textes : il organise les categories, met en valeur les articles et facilite le travail des editeurs qui maintiennent les contenus au quotidien.",
            "Culture",
        ),
        (
            "Startups africaines : la qualite logicielle devient strategique",
            "startups-africaines-qualite-logicielle-strategique",
            "Les jeunes entreprises renforcent leurs bases techniques pour grandir sans fragiliser leurs produits.",
            "Lorsqu'une application attire plus d'utilisateurs, les raccourcis techniques deviennent visibles. Les equipes qui investissent dans une architecture claire, des tests et une documentation solide reduisent les couts futurs. La qualite du code devient alors un avantage concurrentiel aussi important que la rapidite de lancement.",
            "Economie",
        ),
        (
            "Gouvernance des donnees : pourquoi les API comptent",
            "gouvernance-donnees-pourquoi-api-comptent",
            "Les services web rendent les fonctionnalites metier accessibles sans dupliquer l'application.",
            "Une API bien concue permet a un site d'actualite d'ouvrir ses articles a d'autres outils, tout en gardant une seule source de verite. Le format JSON sert les usages modernes et le XML reste pertinent pour certaines integrations. L'essentiel est de separer clairement consultation publique et operations protegees.",
            "Technologie",
        ),
        (
            "Cybersouverainete : les equipes techniques reprennent la main",
            "cybersouverainete-equipes-techniques-reprennent-main",
            "Les organisations structurent leurs applications autour de composants auditables et maintenables.",
            "Face aux risques de dependance, les equipes techniques privilegient les architectures explicites, documentees et testees. Les couches de presentation, de services et de donnees sont separees pour faciliter les audits et les evolutions. Cette demarche donne plus d'autonomie aux organisations et protege mieux leurs actifs numeriques.",
            "Technologie",
        ),
    ]

    for title, slug, summary, content, category_name in articles:
        db.execute(
            """
            INSERT OR IGNORE INTO articles
                (title, slug, summary, content, category_id, author_id, published, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (title, slug, summary, content, category_ids[category_name], admin_id, now, now),
        )

    db.commit()


def init_app(app) -> None:
    app.teardown_appcontext(close_db)

    @app.cli.command("init-db")
    def init_db_command() -> None:
        init_db()
        print("Base de donnees initialisee.")

    @app.cli.command("seed-content")
    def seed_content_command() -> None:
        seed_editorial_content()
        print("Articles editoriaux ajoutes.")
