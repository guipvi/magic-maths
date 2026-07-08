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

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(decks_bp, url_prefix='/api/decks')
    app.register_blueprint(collection_bp, url_prefix='/api/collection')
    app.register_blueprint(analysis_bp, url_prefix='/api/analysis')
    app.register_blueprint(categories_bp, url_prefix='/api/categories')

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
        from app.services.category_service import seed_default_categories
        seed_default_categories()

    @app.route('/api/health')
    def health():
        return {'status': 'ok'}

    return app
