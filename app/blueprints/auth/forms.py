"""Moduli di accesso e registrazione (P16), con le regole di ogni campo.

Regole: username da 3 a 20 caratteri, solo lettere, numeri e _ (D7); password di
almeno 8 caratteri con almeno una maiuscola, un numero e un simbolo (D8, P61): un
simbolo è un carattere che non è una lettera, un numero o uno spazio. Ogni regola
mancante ha il suo messaggio. Valgono solo per le password nuove: il login non le
controlla. I limiti di lunghezza vengono da config.py.

Un "modulo" di WTForms (FlaskForm) è una classe con un attributo per ogni campo; ogni
campo ha i suoi "validatori", le regole che controllano il valore e, se non va, danno
il messaggio. form.validate() li prova tutti e mette i messaggi in form.errors.

Cosa contiene:
    USERNAME_MIN, USERNAME_MAX, PASSWORD_MIN, EMAIL_MAX   i limiti di lunghezza
    PASSWORD_HINT          il suggerimento sotto la password, per esempio "Almeno 8 caratteri, ..."
    _is_symbol("!")        True se il carattere è un simbolo
    _needs(test, msg)      un validatore: la password deve avere almeno un carattere che passa test
    LoginForm              username (o email) e password
    RegisterForm           username, email, password e conferma

DA DOVE ARRIVANO I DATI: app/blueprints/auth/api.py crea i moduli con i campi
mandati dalla SPA (frontend/src/pages/LoginPage.tsx e RegisterPage.tsx), in una
MultiDict, e chiama form.validate().
"""

from flask_wtf import FlaskForm
from wtforms import EmailField, PasswordField, StringField
from wtforms.validators import DataRequired, EqualTo, Length, Regexp, ValidationError

from config import BaseConfig

USERNAME_MIN = BaseConfig.USERNAME_MIN
USERNAME_MAX = BaseConfig.USERNAME_MAX
PASSWORD_MIN = BaseConfig.PASSWORD_MIN
EMAIL_MAX = 254  # come la colonna utenti.email
# Due testi uno dopo l'altro tra parentesi diventano un testo solo (si scrive su due righe)
PASSWORD_HINT = (f"Almeno {PASSWORD_MIN} caratteri, con almeno una lettera maiuscola, "
                 "un numero e un simbolo (per esempio ! ? @ # - _).")


def _is_symbol(char):
    """True se il carattere è un simbolo: né lettera, né numero, né spazio.

    In parole semplici:
        _is_symbol(char)
        Per esempio _is_symbol("!") = True, _is_symbol("a") = False,
        _is_symbol(" ") = False. La usa RegisterForm, attraverso _needs, per la
        regola "almeno un simbolo".
    """
    return not char.isalnum() and not char.isspace()


def _needs(test, message):
    """Validatore: rifiuta la password se nessun carattere supera `test`.

    In parole semplici:
        _needs(test, message)
        Costruisce e restituisce una funzione nuova, check, che WTForms chiama per
        controllare il campo. test è una funzione che riceve un carattere e dice
        True o False (per esempio str.isupper, "è una maiuscola?"); in C sarebbe un
        puntatore a funzione. message è il messaggio se nessun carattere passa, per
        esempio "La password deve contenere almeno una lettera maiuscola.".
        check si "ricorda" test e message anche dopo che _needs è finita (si chiama
        "closure"): così con una funzione sola si fanno tre regole diverse.

        Restituisce: la funzione check(form, field), da mettere tra i validatori.
    """
    def check(form, field):
        # form: il modulo intero; field: il campo, con il testo scritto in field.data.
        # Con il campo vuoto non dice niente: quel messaggio lo dà DataRequired.
        if not field.data:
            return
        # Ricerca lineare: basta un carattere che passa test
        for char in field.data:
            if test(char):
                return
        raise ValidationError(message)

    return check


class LoginForm(FlaskForm):
    """Il modulo di accesso: nome utente (o email) e password.

    In parole semplici:
        LoginForm(formdata=dati, meta={"csrf": False})
        Lo crea login di api.py con i campi mandati dalla SPA. Non controlla le regole
        della password: quelle valgono solo per le password nuove.
    """

    # P96: un campo solo, nome utente o email (con una @ è un'email: gli username non ne hanno, D7)
    username = StringField("Nome utente o email", validators=[
        DataRequired("Scrivi il tuo nome utente o la tua email."),
        Length(max=EMAIL_MAX, message=f"Al massimo {EMAIL_MAX} caratteri."),
    ])
    password = PasswordField("Password", validators=[DataRequired("Scrivi la password.")])


class RegisterForm(FlaskForm):
    """Il modulo di registrazione: username, email, password e conferma.

    In parole semplici:
        RegisterForm(formdata=dati, meta={"csrf": False})
        Lo crea register di api.py. I validatori di ogni campo si provano nell'ordine
        in cui sono scritti, e il primo che non va dà il messaggio.
    """

    username = StringField("Username", validators=[
        DataRequired("Scegli uno username."),
        Length(USERNAME_MIN, USERNAME_MAX,
               f"Lo username deve avere da {USERNAME_MIN} a {USERNAME_MAX} caratteri."),
        # \Z e non $: in Python $ vale anche prima di un a-capo finale (P137)
        Regexp(r"^[A-Za-z0-9_]+\Z", message="Lo username può contenere solo lettere, numeri e _."),
    ])
    email = EmailField("Email", validators=[
        DataRequired("Scrivi la tua email."),
        Length(max=EMAIL_MAX, message=f"L'email può avere al massimo {EMAIL_MAX} caratteri."),
        Regexp(r"^[^@\s]+@[^@\s]+\.[^@\s]+\Z", message="Scrivi un'email valida, per esempio nome@esempio.it."),
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
