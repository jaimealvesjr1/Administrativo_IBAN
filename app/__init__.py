from flask import Flask, current_app
from .extensions import db, login_manager, migrate
from unidecode import unidecode

from .membresia import models as membresia_models
from .ctm import models as ctm_models
from .financeiro import models as financeiro_models
from .grupos import models as grupos_models
from .jornada import models as jornada_models
from .eventos import models as eventos_models
from .jornada.models import registrar_evento_jornada
from .auth.models import User

from .auth.routes import auth_bp
from .membresia.routes import membresia_bp
from .financeiro.routes import financeiro_bp
from .ctm.routes import ctm_bp
from .admin_users.routes import admin_users_bp
from .grupos.routes import grupos_bp
from .eventos.routes import eventos_bp
from .jornada.routes import jornada_bp

from app.filters import to_brasilia, format_datetime, format_currency
from config import Config
from .routes import main_bp
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads', 'profile_pics')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    app.jinja_env.filters['brasilia'] = to_brasilia
    app.jinja_env.filters['format_datetime'] = format_datetime
    app.jinja_env.filters['currency'] = format_currency

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    @app.cli.command("init-db")
    def init_db_command():
        with app.app_context():
            if db.engine.dialect.name == 'sqlite':
                conn = db.engine.connect().connection
                conn.create_function("unidecode", 1, unidecode)
                print("Função unidecode registrada no SQLite.")
            
    @app.before_request
    def register_unidecode_function():
        if not hasattr(current_app, 'unidecode_registered'):
            if db.engine.dialect.name == 'sqlite':
                conn = db.engine.connect().connection
                conn.create_function("unidecode", 1, unidecode)
            current_app.unidecode_registered = True
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(membresia_bp)
    app.register_blueprint(financeiro_bp)
    app.register_blueprint(ctm_bp)
    app.register_blueprint(admin_users_bp)
    app.register_blueprint(grupos_bp)
    app.register_blueprint(eventos_bp)
    app.register_blueprint(jornada_bp)

    from .cli import create_admin, optimize_images_command
    app.cli.add_command(create_admin)
    app.cli.add_command(optimize_images_command)

    @app.context_processor
    def inject_config():
        return dict(config=app.config)

    return app
