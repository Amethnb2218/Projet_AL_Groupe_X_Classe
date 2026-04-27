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
    users = [
        ("admin", "Administrateur", "admin", "admin123"),
        ("editor", "Editeur", "editor", "editor123"),
    ]
    for login, full_name, role, password in users:
        db.execute(
            """
            INSERT OR IGNORE INTO users (login, full_name, role, password_hash, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (login, full_name, role, generate_password_hash(password), now),
        )

    admin_id = db.execute("SELECT id FROM users WHERE login = 'admin'").fetchone()["id"]
    editor_id = db.execute("SELECT id FROM users WHERE login = 'editor'").fetchone()["id"]

    categories = [
        ("Technologie", "technologie", "Innovations, logiciels et usages numeriques."),
        ("Economie", "economie", "Marches, entreprises et politiques publiques."),
        ("Culture", "culture", "Livres, cinema, arts et tendances."),
        ("International", "international", "Regards sur les grands enjeux mondiaux."),
        ("Sciences", "sciences", "Recherche, sante, environnement et decouvertes."),
    ]
    for name, slug, description in categories:
        db.execute(
            """
            INSERT OR IGNORE INTO categories (name, slug, description, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (name, slug, description, now),
        )

    sample_articles = [
        (
            "L'architecture logicielle au service des medias",
            "architecture-logicielle-medias",
            "Comment une architecture claire rend un site d'actualite plus evolutif et plus fiable.",
            "Un site d'actualite doit publier vite, rester lisible et exposer ses donnees a d'autres applications. Une separation nette entre les pages, les services web, les roles et la persistence rend ces evolutions plus simples. Cette approche facilite aussi les tests, la maintenance et l'ajout de nouveaux canaux de diffusion.",
            "Technologie",
            admin_id,
        ),
        (
            "Les API ouvrent les redactions",
            "api-redactions",
            "Les services REST et SOAP facilitent l'integration avec les outils externes.",
            "Les applications clientes peuvent consommer les articles, automatiser des actions d'administration et connecter le site a des outils externes sans dupliquer la logique metier. REST convient aux consultations publiques, tandis que SOAP structure les operations sensibles autour d'un contrat explicite et d'un jeton d'acces.",
            "Technologie",
            editor_id,
        ),
        (
            "Budget numerique : priorite a la maintenance",
            "budget-numerique-maintenance",
            "Les investissements se concentrent sur la robustesse des plateformes existantes.",
            "Pour les organisations, la qualite de code et la testabilite comptent autant que la livraison rapide. Les projets perennes reduisent les couts futurs, car chaque module reste comprehensible, testable et remplacable sans immobiliser toute la plateforme.",
            "Economie",
            editor_id,
        ),
        (
            "Une semaine culturelle sous le signe du numerique",
            "semaine-culturelle-numerique",
            "Les festivals hybrides rapprochent les publics en ligne et sur place.",
            "Les evenements culturels utilisent davantage de plateformes web pour publier les programmes, partager les critiques et conserver des archives accessibles. Les sites d'actualite deviennent alors des lieux de mediation, capables de relier calendrier, analyse et participation du public.",
            "Culture",
            admin_id,
        ),
        (
            "La presse locale adopte les donnees ouvertes",
            "presse-locale-donnees-ouvertes",
            "Les jeux de donnees publics alimentent de nouveaux formats d'enquete.",
            "Les journalistes croisent des sources ouvertes avec leurs observations de terrain. Les sites modernes doivent donc publier des contenus consultables et reutilisables, tout en gardant une interface claire pour le lecteur et une administration efficace pour la redaction.",
            "Economie",
            admin_id,
        ),
        (
            "Cooperation regionale : les plateformes publiques se connectent",
            "cooperation-regionale-plateformes-publiques",
            "Les administrations multiplient les services interoperables pour simplifier les demarches.",
            "La modernisation des services publics repose de plus en plus sur des interfaces partagees. Les API permettent aux institutions de publier des informations fiables, de reduire les ressaisies et de mieux tracer les operations sensibles.",
            "International",
            admin_id,
        ),
        (
            "Sante numerique : la donnee exige une gouvernance precise",
            "sante-numerique-gouvernance-donnee",
            "Les acteurs de la sante renforcent la securite et la lisibilite des parcours patients.",
            "La transformation numerique de la sante montre l'importance des droits d'acces, de la journalisation et des contrats de services. Une architecture bien pensee protege les donnees tout en gardant les applications utilisables.",
            "Sciences",
            editor_id,
        ),
        (
            "Edition en ligne : les lecteurs veulent aller a l'essentiel",
            "edition-en-ligne-lecteurs-essentiel",
            "Les interfaces editoriales gagnent en impact quand elles hierarchisent clairement l'information.",
            "La qualite d'un site d'actualite ne depend pas seulement de ses contenus. La mise en page, les contrastes, la typographie et la hierarchie visuelle guident le lecteur et donnent de la credibilite a la plateforme.",
            "Culture",
            editor_id,
        ),
        (
            "Cybersouverainete : les equipes techniques reprennent la main",
            "cybersouverainete-equipes-techniques",
            "Les organisations structurent leurs applications autour de composants auditables.",
            "Face aux risques de dependance, les equipes techniques privilegient les architectures explicites, documentees et testees. Les couches de services, de donnees et d'interface sont separees pour faciliter les audits et les evolutions.",
            "Technologie",
            admin_id,
        ),
    ]
    for title, slug, summary, content, category_name, author_id in sample_articles:
        category_id = db.execute(
            "SELECT id FROM categories WHERE name = ?", (category_name,)
        ).fetchone()["id"]
        db.execute(
            """
            INSERT OR IGNORE INTO articles
                (title, slug, summary, content, category_id, author_id, published, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (title, slug, summary, content, category_id, author_id, now, now),
        )

    db.execute(
        """
        INSERT OR IGNORE INTO api_tokens (label, token, created_by, created_at)
        VALUES (?, ?, ?, ?)
        """,
        ("Jeton de demonstration", "DEMO-ADMIN-TOKEN", admin_id, now),
    )


def init_app(app) -> None:
    app.teardown_appcontext(close_db)

    @app.cli.command("init-db")
    def init_db_command() -> None:
        init_db()
        print("Base de donnees initialisee.")
