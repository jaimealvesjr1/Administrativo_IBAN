from flask import Flask, current_app
from .extensions import db, login_manager, migrate
from .auth.routes import auth_bp
from .membresia.routes import membresia_bp
from .financeiro.routes import financeiro_bp
from .ctm.routes import ctm_bp
from app.filters import to_brasilia, format_datetime, format_currency
from config import Config
from .routes import main_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    app.jinja_env.filters['brasilia'] = to_brasilia
    app.jinja_env.filters['strftime'] = format_datetime
    app.jinja_env.filters['currency'] = format_currency

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(membresia_bp)
    app.register_blueprint(financeiro_bp)
    app.register_blueprint(ctm_bp)

    from .cli import create_admin
    app.cli.add_command(create_admin)

    @app.context_processor
    def inject_config():
        return dict(config=app.config)

    return app
