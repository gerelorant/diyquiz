from flask import Flask, request
from flask_babelex import Babel, Domain
from flask_bootstrap import Bootstrap
from flask_migrate import Migrate
from flask_security import current_user

import admin
from config import Config
from model import db
from security import security, data_store, LoginUserForm, RegisterUserForm


app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
mig = Migrate(app=app, db=db, directory=app.config.get('MIGRATE_DIRECTORY', 'data/migrations'))
Bootstrap(app)

security.init_app(app, data_store, login_form=LoginUserForm, register_form=RegisterUserForm)
admin.admin.init_app(app)

domain = Domain(app.config.get("BABEL_TRANSLATIONS")[0], "messages")
babel = Babel(app, default_domain=domain)
babel.domain = "messages"
babel.translation_directories = app.config.get("BABEL_TRANSLATIONS")


@babel.localeselector
def get_locale():
    if current_user.is_authenticated:
        return current_user.language or 'hu'
    return request.accept_languages.best_match(app.config.get('LANGUAGES'))


@babel.timezoneselector
def get_timezone():
    if current_user.is_authenticated:
        return


if __name__ == '__main__':
    app.run()
