import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()


def _require_env(key):
    value = os.getenv(key)
    if not value:
        raise RuntimeError(
            f"La variable de entorno '{key}' no está definida. "
            f"Revisá tu archivo .env antes de iniciar la app."
        )
    return value


def create_app():
    app = Flask(__name__)

    # ── Config ──
    app.config["SECRET_KEY"] = _require_env("SECRET_KEY")
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"mysql+pymysql://{_require_env('DB_USER')}:{_require_env('DB_PASS')}"
        f"@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '3306')}"
        f"/{_require_env('DB_NAME')}"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,   # evita "MySQL has gone away" tras períodos de inactividad
        "pool_recycle": 300,
    }
    app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "uploads")
    app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8 MB

    # ── Logging ──
    _setup_logging(app)

    # ── Extensions ──
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Iniciá sesión para acceder al sistema."
    login_manager.login_message_category = "warning"
    csrf.init_app(app)

    # ── User loader ──
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # ── Blueprints ──
    from app.blueprints.auth.routes import auth_bp
    from app.blueprints.inventory.routes import inventory_bp
    from app.blueprints.search.routes import search_bp
    from app.blueprints.admin.routes import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(admin_bp)

    # ── Context processors ──
    @app.context_processor
    def inject_globals():
        from flask_login import current_user
        from flask import session
        from app.models import Barrio
        extra = {}
        if current_user.is_authenticated and current_user.is_admin:
            extra["barrios_admin"] = Barrio.query.filter_by(activo=True).order_by(Barrio.nombre).all()
            extra["admin_barrio_id"] = session.get("admin_barrio_id")
        else:
            extra["barrios_admin"] = []
            extra["admin_barrio_id"] = None
        return dict(current_user=current_user, **extra)

    # ── Create upload folder ──
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    return app


def _setup_logging(app):
    # logs/ vive un nivel arriba del paquete app/, en la raíz del deploy
    log_dir = os.path.join(os.path.dirname(app.root_path), "logs")
    os.makedirs(log_dir, exist_ok=True)

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
    )

    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "app.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(logging.INFO)

    app.logger.addHandler(file_handler)
    app.logger.addHandler(stream_handler)
    app.logger.setLevel(logging.INFO)
