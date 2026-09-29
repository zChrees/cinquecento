"""Moduli di accesso e registrazione (P16), con il codice CSRF di Flask-WTF.

Regole: username da 3 a 20 caratteri, solo lettere, numeri e _ (D7); password di
almeno 8 caratteri con almeno una maiuscola, un numero e un simbolo (D8, P61): un
simbolo è un carattere che non è una lettera, un numero o uno spazio. Ogni regola
mancante ha il suo messaggio. Valgono solo per le password nuove: il login non le
controlla. I limiti di lunghezza vengono da config.py.
"""

from flask_wtf import FlaskForm
from wtforms import EmailField, PasswordField, StringField
from wtforms.validators import DataRequired, EqualTo, Length, Regexp, ValidationError

from config import BaseConfig

USERNAME_MIN = BaseConfig.USERNAME_MIN
USERNAME_MAX = BaseConfig.USERNAME_MAX
PASSWORD_MIN = BaseConfig.PASSWORD_MIN
EMAIL_MAX = 254  # come la colonna utenti.email
PASSWORD_HINT = (f"Almeno {PASSWORD_MIN} caratteri, con almeno una lettera maiuscola, "
                 "un numero e un simbolo (per esempio ! ? @ # - _).")


def _is_symbol(char):
    return not char.isalnum() and not char.isspace()


def _needs(test, message):
    """Validatore: rifiuta la password se nessun carattere supera `test`."""
    def check(form, field):
        if field.data and not any(test(c) for c in field.data):
            raise ValidationError(message)
    return check


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
    password = PasswordField("Password", description=PASSWORD_HINT, validators=[
        DataRequired("Scegli una password."),
        Length(min=PASSWORD_MIN, message=f"La password deve avere almeno {PASSWORD_MIN} caratteri."),
        _needs(str.isupper, "La password deve contenere almeno una lettera maiuscola."),
        _needs(str.isdecimal, "La password deve contenere almeno un numero."),
        _needs(_is_symbol, "La password deve contenere almeno un simbolo (per esempio ! ? @ # - _)."),
    ])
    confirm = PasswordField("Ripeti la password", validators=[
        DataRequired("Ripeti la password."),
        EqualTo("password", "Le due password non coincidono."),
    ])
