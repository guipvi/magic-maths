from flask import Flask
from flask_cors import CORS
from app.extensions import db, migrate, jwt
from app.config import Config


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    CORS(app)
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    from app.routes.auth import auth_bp
    from app.routes.decks import decks_bp
    from app.routes.collection import collection_bp
    from app.routes.analysis import analysis_bp
    from app.routes.categories import categories_bp
    from app.routes.commander import commander_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(decks_bp, url_prefix='/api/decks')
    app.register_blueprint(collection_bp, url_prefix='/api/collection')
    app.register_blueprint(analysis_bp, url_prefix='/api/analysis')
    app.register_blueprint(categories_bp, url_prefix='/api/categories')
    app.register_blueprint(commander_bp, url_prefix='/api/decks')

    # ensure tables exist and seed default categories
    with app.app_context():
        from sqlalchemy import event

        if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']:
            @event.listens_for(db.engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA busy_timeout=5000")
                cursor.close()

        db.create_all()

        from sqlalchemy import inspect
        insp = inspect(db.engine)

        cat_cols = [c['name'] for c in insp.get_columns('categories')]
        if 'parent_id' not in cat_cols:
            db.session.execute(db.text(
                "ALTER TABLE categories ADD COLUMN parent_id INTEGER REFERENCES categories(id)"
            ))
            db.session.commit()

        # Drop old UNIQUE on name for SQLite (table recreation)
        if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']:
            create_sql = db.session.execute(
                db.text("SELECT sql FROM sqlite_master WHERE type='table' AND name='categories'")
            ).scalar()
            if create_sql and 'UNIQUE' in create_sql.upper():
                old_parent_ids = dict(db.session.execute(
                    db.text("SELECT id, parent_id FROM categories")
                ).fetchall())
                db.session.execute(db.text("UPDATE categories SET parent_id=NULL"))
                db.session.execute(db.text("PRAGMA foreign_keys=OFF"))
                db.session.execute(db.text("""
                    CREATE TABLE categories_v2 (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name VARCHAR(64) NOT NULL,
                        color VARCHAR(7) DEFAULT '#6366f1',
                        config JSON DEFAULT '{}',
                        is_default BOOLEAN DEFAULT 0,
                        parent_id INTEGER REFERENCES categories(id),
                        created_at DATETIME
                    )
                """))
                db.session.execute(db.text("INSERT INTO categories_v2 SELECT * FROM categories"))
                db.session.execute(db.text("DROP TABLE categories"))
                db.session.execute(db.text("ALTER TABLE categories_v2 RENAME TO categories"))
                db.session.execute(db.text("PRAGMA foreign_keys=ON"))
                for cid, pid in old_parent_ids.items():
                    if pid:
                        db.session.execute(
                            db.text("UPDATE categories SET parent_id=:pid WHERE id=:cid"),
                            {'pid': pid, 'cid': cid}
                        )
                db.session.commit()

        cols = [c['name'] for c in insp.get_columns('deck_card_categories')]
        if 'tutored_card_id' not in cols:
            db.session.execute(db.text(
                "ALTER TABLE deck_card_categories ADD COLUMN tutored_card_id INTEGER REFERENCES cards(id)"
            ))
            db.session.commit()

        cols = [c['name'] for c in insp.get_columns('deck_commander_config')]
        if 'condition_groups' not in cols:
            db.session.execute(db.text(
                "ALTER TABLE deck_commander_config ADD COLUMN condition_groups JSON DEFAULT '[]'"
            ))
            db.session.commit()

        cat_contain_cols = [c['name'] for c in insp.get_columns('category_containments')]
        if 'mode' not in cat_contain_cols:
            db.session.execute(db.text(
                "ALTER TABLE category_containments ADD COLUMN mode VARCHAR(20) DEFAULT 'subcategoria'"
            ))
            db.session.commit()

        from app.services.category_service import seed_default_categories
        seed_default_categories()

    @app.route('/api/health')
    def health():
        return {'status': 'ok'}

    return app
