from flask_babelex import lazy_gettext as _l
from flask_security import Security, SQLAlchemyUserDatastore, LoginForm, RegisterForm
import wtforms as wtf

import model


class RegisterUserForm(RegisterForm):
    username = wtf.StringField(
        _l('Username'),
        validators=[wtf.validators.DataRequired(), wtf.validators.Length(min=5, max=16)]
    )
    email = None
    password = wtf.PasswordField(
        _l('Password'),
        validators=[wtf.validators.DataRequired()]
    )
    password_confirm = wtf.PasswordField(
        _l('Confirm Password'),
        validators=[wtf.validators.DataRequired(), wtf.validators.EqualTo('password')]
    )
    submit = wtf.SubmitField(
        _l('Register')
    )


class LoginUserForm(LoginForm):
    email = wtf.StringField(
        _l('Username'),
        validators=[wtf.validators.DataRequired(), wtf.validators.Length(min=5, max=16)]
    )
    password = wtf.PasswordField(
        _l('Password'),
        validators=[wtf.validators.DataRequired()]
    )
    remember = wtf.BooleanField(
        _l('Remember Me'),
        default=True
    )
    submit = wtf.SubmitField(
        _l('Sign in')
    )


data_store = SQLAlchemyUserDatastore(model.db, model.User, model.Role)
security = Security()
