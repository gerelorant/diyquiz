import os
from local_config import LocalConfig

DIR = os.path.abspath(os.path.dirname(__file__))


class Config(LocalConfig):
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    BABEL_TRANSLATIONS = [os.path.join(DIR, "data/translations")]
    BABEL_DEFAULT_LOCALE = "hu"
    BABEL_DEFAULT_TIMEZONE = "Europe/Budapest"
    LANGUAGES = ["hu"]

    SECURITY_PASSWORD_HASH = "sha512_crypt"
    SECURITY_PASSWORD_SALT = "fhasdgihwntlgy8f"
    SECURITY_USER_IDENTITY_ATTRIBUTES = ["username", "email"]
    SECURITY_REGISTERABLE = True
    SECURITY_SEND_REGISTER_EMAIL = False
