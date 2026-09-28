"""Moduli di accesso e registrazione (P16), con il codice CSRF di Flask-WTF.

Regole: username da 3 a 20 caratteri, solo lettere, numeri e _ (D7); password di
almeno 8 caratteri (D8, provvisorio). I limiti vengono da config.py.
"""

from flask_wtf import FlaskForm
from wtforms import EmailField, PasswordField, StringField
from wtforms.validators import DataRequired, EqualTo, Length, Regexp

from config import BaseConfig

USERNAME_MIN = BaseConfig.USERNAME_MIN
USERNAME_MAX = BaseConfig.USERNAME_MAX
PASSWORD_MIN = BaseConfig.PASSWORD_MIN
EMAIL_MAX = 254  # come la colonna utenti.email


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired("Scrivi il tuo username.")])
    password = PasswordField("Password", validators=[DataRequired("Scrivi la password.")])


class RegisterForm(FlaskForm):
    username = StringField("Username", validators=[
        DataRequired("Scegli uno username."),
        Length(USERNAME_MIN, USERNAME_MAX,
               f"Lo username deve avere da {USERNAME_MIN} a {USERNAME_MAX} caratteri."),
        Regexp(r"^[A-Za-z0-9_]+$", message="Lo username può contenere solo lettere, numeri e _."),
    ])
    email = EmailField("Email", validators=[
        DataRequired("Scrivi la tua email."),
        Length(max=EMAIL_MAX, message=f"L'email può avere al massimo {EMAIL_MAX} caratteri."),
        Regexp(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", message="Scrivi un'email valida, per esempio nome@esempio.it."),
    ])
    password = PasswordField("Password", validators=[
        DataRequired("Scegli una password."),
        Length(min=PASSWORD_MIN, message=f"La password deve avere almeno {PASSWORD_MIN} caratteri."),
    ])
    confirm = PasswordField("Ripeti la password", validators=[
        DataRequired("Ripeti la password."),
        EqualTo("password", "Le due password non coincidono."),
    ])
