from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from flask import current_app, g
from werkzeug.security import generate_password_hash


def ensure_schema_updates(db: sqlite3.Connection) -> None:
    table = db.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'categories'"
    ).fetchone()
    if table is None:
        return
    columns = {row["name"] for row in db.execute("PRAGMA table_info(categories)").fetchall()}
    if "image_filename" not in columns:
        db.execute("ALTER TABLE categories ADD COLUMN image_filename TEXT")
        db.commit()
    article_columns = {row["name"] for row in db.execute("PRAGMA table_info(articles)").fetchall()}
    if "image_hidden" not in article_columns:
        db.execute("ALTER TABLE articles ADD COLUMN image_hidden INTEGER NOT NULL DEFAULT 0")
        db.commit()


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
        ensure_schema_updates(g.db)
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


def deduplicate_editorial_articles(db: sqlite3.Connection, articles: list[tuple[str, str, str, str, str]]) -> None:
    for title, slug, _summary, _content, _category_name in articles:
        rows = db.execute(
            """
            SELECT id, slug
            FROM articles
            WHERE TRIM(title) = ?
            ORDER BY
                CASE WHEN slug = ? THEN 0 ELSE 1 END,
                updated_at DESC,
                created_at DESC,
                id DESC
            """,
            (title.strip(), slug),
        ).fetchall()
        if not rows:
            continue

        kept = rows[0]
        for duplicate in rows[1:]:
            db.execute("DELETE FROM articles WHERE id = ?", (duplicate["id"],))
        if kept["slug"] != slug:
            db.execute("UPDATE articles SET slug = ? WHERE id = ?", (slug, kept["id"]))


def seed_editorial_content() -> None:
    db = get_db()
    now = utc_now()
    admin = db.execute("SELECT id FROM users WHERE login = 'admin'").fetchone()
    if admin is None:
        seed_db(db)
        admin = db.execute("SELECT id FROM users WHERE login = 'admin'").fetchone()
    admin_id = admin["id"]

    categories = [
        ("Technologie", "technologie", "Architecture, innovation et usages numériques."),
        ("Économie", "economie", "Entreprises, investissements et transformation des marchés."),
        ("Culture", "culture", "Création, médias, livres, festivals et nouveaux publics."),
        ("International", "international", "Cooperation, politiques publiques et enjeux mondiaux."),
        ("Sciences", "sciences", "Recherche, santé, environnement et données."),
    ]
    for name, slug, description in categories:
        db.execute(
            """
            INSERT INTO categories (name, slug, description, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(slug) DO UPDATE SET
                name = excluded.name,
                description = excluded.description
            """,
            (name, slug, description, now),
        )

    category_ids = {
        row["name"]: row["id"] for row in db.execute("SELECT id, name FROM categories").fetchall()
    }

    articles = [
        (
            "Éducation numérique : les plateformes cherchent la fiabilité",
            "education-numerique-plateformes-fiabilite",
            "Les établissements renforcent leurs outils en ligne pour mieux suivre les parcours des apprenants.",
            "Les plateformes éducatives doivent supporter les inscriptions, les contenus, les évaluations et les statistiques sans perdre en clarté. Une architecture bien séparée aide les équipes à faire évoluer les modules de cours, d'administration et de reporting. Elle permet aussi de connecter les services à d'autres applications tout en gardant des droits d'accès cohérents.",
            "Sciences",
        ),
        (
            "Presse locale : les données ouvertes changent l'enquête",
            "presse-locale-donnees-ouvertes",
            "Les rédactions utilisent davantage les jeux de données publics pour produire des formats utiles.",
            "Les journalistes croisent des données ouvertes avec leurs observations de terrain pour expliquer les transports, les budgets, la santé ou l'environnement. Les sites d'actualité doivent donc publier des contenus consultables, classés par catégorie et réutilisables par des services web. Cette logique donne plus de valeur au travail éditorial.",
            "Économie",
        ),
        (
            "Santé numérique : protéger les parcours patients",
            "sante-numerique-proteger-parcours-patients",
            "Les applications de santé rappellent l'importance des rôles, des jetons et de la traçabilité.",
            "La transformation numérique de la santé exige des interfaces simples et des contrôles stricts. Les administrateurs gèrent les accès, les éditeurs maintiennent les contenus et les visiteurs consultent les informations publiques. Cette séparation des responsabilités réduit les erreurs et renforce la confiance dans les services.",
            "Sciences",
        ),
        (
            "Coopération régionale : connecter les services publics",
            "cooperation-regionale-connecter-services-publics",
            "Les administrations misent sur des interfaces interopérables pour simplifier les démarches.",
            "Les services publics gagnent en efficacité lorsqu'ils exposent des informations fiables à travers des API. Les applications externes peuvent lire les données sans dupliquer la logique interne. REST facilite la consultation, tandis que SOAP reste utile pour les opérations encadrées par un contrat strict et un jeton d'authentification.",
            "International",
        ),
        (
            "Culture numérique : les festivals inventent un nouveau public",
            "culture-numerique-festivals-nouveau-public",
            "Les événements hybrides rapprochent les spectateurs en ligne et sur place.",
            "Les festivals utilisent les plateformes web pour publier des programmes, partager des critiques et conserver des archives accessibles. Un bon site éditorial ne se limite pas à afficher des textes : il organise les catégories, met en valeur les articles et facilite le travail des éditeurs qui maintiennent les contenus au quotidien.",
            "Culture",
        ),
        (
            "Startups africaines : la qualité logicielle devient stratégique",
            "startups-africaines-qualite-logicielle-strategique",
            "Les jeunes entreprises renforcent leurs bases techniques pour grandir sans fragiliser leurs produits.",
            "Lorsqu'une application attire plus d'utilisateurs, les raccourcis techniques deviennent visibles. Les équipes qui investissent dans une architecture claire, des tests et une documentation solide réduisent les coûts futurs. La qualité du code devient alors un avantage concurrentiel aussi important que la rapidité de lancement.",
            "Économie",
        ),
        (
            "Gouvernance des données : pourquoi les API comptent",
            "gouvernance-donnees-pourquoi-api-comptent",
            "Les services web rendent les fonctionnalités métier accessibles sans dupliquer l'application.",
            "Une API bien conçue permet à un site d'actualité d'ouvrir ses articles à d'autres outils, tout en gardant une seule source de vérité. Le format JSON sert les usages modernes et le XML reste pertinent pour certaines intégrations. L'essentiel est de séparer clairement consultation publique et opérations protégées.",
            "Technologie",
        ),
        (
            "Cybersouveraineté : les équipes techniques reprennent la main",
            "cybersouverainete-equipes-techniques-reprennent-main",
            "Les organisations structurent leurs applications autour de composants auditables et maintenables.",
            "Face aux risques de dépendance, les équipes techniques privilégient les architectures explicites, documentées et testées. Les couches de présentation, de services et de données sont séparées pour faciliter les audits et les évolutions. Cette démarche donne plus d'autonomie aux organisations et protège mieux leurs actifs numériques.",
            "Technologie",
        ),
    ]

    deduplicate_editorial_articles(db, articles)

    for title, slug, summary, content, category_name in articles:
        db.execute(
            """
            INSERT INTO articles
                (title, slug, summary, content, category_id, author_id, published, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
            ON CONFLICT(slug) DO UPDATE SET
                title = excluded.title,
                summary = excluded.summary,
                content = excluded.content,
                category_id = excluded.category_id,
                published = excluded.published,
                updated_at = excluded.updated_at
            """,
            (title, slug, summary, content, category_ids[category_name], admin_id, now, now),
        )

    db.commit()


def init_app(app) -> None:
    app.teardown_appcontext(close_db)

    @app.cli.command("init-db")
    def init_db_command() -> None:
        init_db()
        print("Base de données initialisée.")

    @app.cli.command("seed-content")
    def seed_content_command() -> None:
        seed_editorial_content()
        print("Articles éditoriaux ajoutés.")
