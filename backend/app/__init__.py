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

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(decks_bp, url_prefix='/api/decks')
    app.register_blueprint(collection_bp, url_prefix='/api/collection')
    app.register_blueprint(analysis_bp, url_prefix='/api/analysis')

    @app.route('/api/health')
    def health():
        return {'status': 'ok'}

    return app
