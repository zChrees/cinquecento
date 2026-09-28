"""Registrazione e login (P16).

- Le password si salvano solo come hash (werkzeug.security, scrypt).
- Username o email già usati: decide il vincolo unico di MySQL dentro la stessa
  transazione, così anche due registrazioni contemporanee non creano doppioni.
- Login sbagliato: sempre lo stesso messaggio, che non dice se lo username esiste.
- Tentativi: dopo LOGIN_MAX_ATTEMPTS errori sullo stesso username, per
  LOGIN_LOCK_SECONDS ogni login di quello username si rifiuta, anche con la
  password giusta. Il conteggio sta in memoria (un solo processo, DECISIONI.md):
  si azzera con un login riuscito o al riavvio del server.
- Nei log non finiscono mai password né hash.

Impostazioni (P17):
- Avatar: solo un codice di app/services/avatars.py, oppure vuoto (iniziale del nome).
- Cancellazione dell'account: serve la password; gli errori contano come quelli del
  login (stesso limite, stesso blocco). Chi ha una partita in corso non si può
  cancellare: a fine partita il salvataggio (P26) cercherebbe un utente che non c'è più.
"""

import logging
import threading
import time

from flask import current_app
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.realtime.invites import invites
from app.realtime.matchmaking import matchmaker
from app.realtime.presence import disconnect_user
from app.realtime.room_manager import find_room_of_user
from app.repositories import user_repo
from app.services import avatars

log = logging.getLogger(__name__)

LOGIN_FAILED = "Username o password non corretti."
LOGIN_LOCKED = "Troppi tentativi sbagliati: riprova tra qualche minuto."
USERNAME_TAKEN = "Questo username è già usato: scegline un altro."
EMAIL_TAKEN = "Questa email è già usata da un altro account."
AVATAR_INVALID = "Avatar non valido: scegline uno dell'elenco."
DELETE_NO_PASSWORD = "Scrivi la password per cancellare l'account."
DELETE_WRONG_PASSWORD = "Password non corretta: l'account non è stato cancellato."
DELETE_IN_GAME = "Hai una partita in corso: finiscila prima di cancellare l'account."

# Hash di una password qualsiasi: con uno username inesistente si fa lo stesso
# controllo, così il tempo di risposta non rivela se l'account esiste.
_DUMMY_HASH = generate_password_hash("password-che-non-esiste")


class AuthError(Exception):
    """Richiesta rifiutata; `field` è il campo del modulo a cui si riferisce (None = tutto il modulo)."""

    def __init__(self, message, field=None):
        super().__init__(message)
        self.message = message
        self.field = field


class LoginLimiter:
    """Errori di login per username, in memoria, sotto un lock (le richieste arrivano da più thread)."""

    SWEEP_SIZE = 1000  # oltre questo numero di voci si tolgono quelle scadute

    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self._lock = threading.Lock()
        # username -> [errori, bloccato_fino_a (None = non bloccato), ora dell'ultimo errore]
        self._entries = {}

    def is_locked(self, username):
        with self._lock:
            entry = self._entries.get(username)
            if entry is None or entry[1] is None:
                return False
            if self._clock() < entry[1]:
                return True
            del self._entries[username]  # attesa finita: si riparte da zero
            return False

    def record_failure(self, username, max_attempts, lock_seconds):
        """Conta un errore; restituisce True se con questo lo username resta bloccato.

        Gli errori più vecchi di lock_seconds si dimenticano: così anche gli username
        inventati non restano in memoria per sempre.
        """
        with self._lock:
            now = self._clock()
            if len(self._entries) >= self.SWEEP_SIZE:
                self._entries = {
                    k: v for k, v in self._entries.items()
                    if (v[1] is not None and v[1] > now) or now - v[2] < lock_seconds
                }
            entry = self._entries.get(username)
            if entry is None or (entry[1] is None and now - entry[2] >= lock_seconds):
                entry = self._entries[username] = [0, None, now]
            entry[0] += 1
            entry[2] = now
            if entry[0] >= max_attempts:
                entry[1] = now + lock_seconds
                return True
            return False

    def reset(self, username=None):
        with self._lock:
            if username is None:
                self._entries.clear()
            else:
                self._entries.pop(username, None)


limiter = LoginLimiter()


def register(username, email, password):
    """Crea l'utente e lo restituisce; username o email già usati → AuthError sul campo."""
    user = user_repo.add(username, email, generate_password_hash(password))
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        text = str(exc.orig)
        if "uq_utenti_nome" in text:
            raise AuthError(USERNAME_TAKEN, "username") from None
        if "uq_utenti_email" in text:
            raise AuthError(EMAIL_TAKEN, "email") from None
        raise
    log.info("Nuovo utente registrato (id %s)", user.id)
    return user


def authenticate(username, password):
    """Restituisce l'utente se username e password sono giusti; altrimenti AuthError."""
    config = current_app.config
    if limiter.is_locked(username):
        raise AuthError(LOGIN_LOCKED)

    user = user_repo.get_by_username(username)
    ok = check_password_hash(user.password_hash if user else _DUMMY_HASH, password)
    if user is None or not ok:
        locked = limiter.record_failure(username, config["LOGIN_MAX_ATTEMPTS"], config["LOGIN_LOCK_SECONDS"])
        if locked:
            log.warning("Login bloccato per troppi tentativi sbagliati")
            raise AuthError(LOGIN_LOCKED)
        raise AuthError(LOGIN_FAILED)

    limiter.reset(username)
    return user


def set_avatar(user, code):
    """Salva l'avatar scelto; "" = nessun avatar (iniziale). Un codice fuori elenco → AuthError."""
    if code == "":
        code = None
    elif not avatars.is_valid(code):
        raise AuthError(AVATAR_INVALID, "avatar")
    user_repo.set_avatar(user, code)
    db.session.commit()


def delete_account(user, password):
    """Cancella l'account dopo aver controllato la password; altrimenti AuthError."""
    config = current_app.config
    username, user_id = user.username, user.id
    if not isinstance(password, str) or not password:
        raise AuthError(DELETE_NO_PASSWORD, "password")
    if limiter.is_locked(username):
        raise AuthError(LOGIN_LOCKED)
    if not check_password_hash(user.password_hash, password):
        locked = limiter.record_failure(username, config["LOGIN_MAX_ATTEMPTS"], config["LOGIN_LOCK_SECONDS"])
        if locked:
            log.warning("Cancellazione dell'account bloccata per troppi tentativi sbagliati")
            raise AuthError(LOGIN_LOCKED)
        raise AuthError(DELETE_WRONG_PASSWORD, "password")
    if find_room_of_user(user_id) is not None:
        raise AuthError(DELETE_IN_GAME)

    # P32: prima di cancellare, quando l'utente è ancora riconosciuto, si chiudono le sue
    # schede collegate; poi esce dalla coda e i suoi inviti si annullano (anche senza schede)
    disconnect_user(user_id)
    matchmaker.leave(user_id)
    invites.cancel_all_of(user_id)
    user_repo.delete(user)
    db.session.commit()
    limiter.reset(username)
    log.info("Account cancellato (id %s)", user_id)


def load_user(user_id):
    """Per Flask-Login: l'utente della sessione, o None se l'id non è valido o non esiste più."""
    try:
        return user_repo.get_by_id(int(user_id))
    except (TypeError, ValueError):
        return None
