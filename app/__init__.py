from flask import Flask

from config import Config
from .auth import auth_bp
from .extensions import csrf, db, login_manager, migrate
from .game import game_bp
from .models import User
from .routes import main_bp


def create_app(config_class=Config):
    app = Flask(__name__, static_folder="../assets", static_url_path="/assets")
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    login_manager.login_view = "main.login"

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(game_bp)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.cli.command("init-db")
    def init_db():
        db.create_all()
        print("Database tables created.")

    return app
