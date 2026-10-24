"""Registrazione e login (P16), avatar e cancellazione dell'account (P17).

- Le password si salvano solo come hash (werkzeug.security, scrypt): un "hash" è un
  codice ricavato dalla password da cui non si torna indietro; per controllare una
  password si rifà il conto e si confrontano i due hash.
- Username o email già usati: decide il vincolo unico di MySQL dentro la stessa
  transazione, così anche due registrazioni contemporanee non creano doppioni.
- Login (P96): con lo username o con l'email, in un campo solo; con una @ è un'email.
  Login sbagliato: sempre lo stesso messaggio, che non dice se l'account esiste.
- Tentativi: dopo LOGIN_MAX_ATTEMPTS errori sullo stesso account, per
  LOGIN_LOCK_SECONDS ogni login di quell'account si rifiuta, anche con la password
  giusta. P96: il conto è per **account** (scrivendo una volta lo username e una volta
  l'email il blocco non si aggira); per un account che non esiste, per il testo scritto.
  Il conteggio sta in memoria (un solo processo, DECISIONI.md): si azzera con un login
  riuscito o al riavvio del server.
- Nei log non finiscono mai password né hash.

Impostazioni (P17):
- Avatar: solo un codice di app/services/avatars.py, oppure vuoto (iniziale del nome).
- Cancellazione dell'account: serve la password; gli errori contano come quelli del
  login (stesso limite, stesso blocco). Chi ha una partita in corso non si può
  cancellare: a fine partita il salvataggio (P26) cercherebbe un utente che non c'è più.

Cosa contiene:
    AuthError                    l'errore con il messaggio per l'utente e il campo del modulo
    LoginLimiter / limiter       il conto dei tentativi sbagliati, in memoria
    register(u, e, p)            crea un account, per esempio register("Mario", "mario@x.it", "segreta1")
    authenticate(login, p)       il login: authenticate("Mario", "segreta1") -> l'utente
    set_avatar(user, code)       salva l'avatar: set_avatar(user, "re_coppe")
    delete_account(user, p)      cancella l'account dopo aver controllato la password
    load_user(user_id)           l'utente della sessione, per Flask-Login: load_user("7")

DA DOVE ARRIVANO I DATI: le pagine della SPA mandano i moduli in JSON a
/api/auth/login e /api/auth/register (app/blueprints/auth/api.py, che chiama
authenticate e register) e a /api/profile/avatar e /api/profile/delete
(app/blueprints/profile/api.py, che chiama set_avatar e delete_account); load_user lo
registra app/blueprints/auth/routes.py come user_loader di Flask-Login, che lo chiama
a ogni richiesta con il numero dell'utente salvato nel cookie di sessione.
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

# I messaggi che vede l'utente
LOGIN_FAILED = "Nome utente, email o password non corretti."
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


# class AuthError(Exception): una classe nuova che "eredita" da Exception, cioè è un
# tipo di errore come gli altri di Python: si lancia con raise e si prende con except.
# Le rotte la prendono e mandano message alla pagina, accanto al campo field.
class AuthError(Exception):
    """Richiesta rifiutata; `field` è il campo del modulo a cui si riferisce (None = tutto il modulo).

    In parole semplici:
        AuthError(message, field)
        Per esempio AuthError("Questo username è già usato: scegline un altro.", "username").
        message: il testo da mostrare all'utente, una delle costanti qui sopra.
        field:   facoltativo; il nome del campo del modulo ("username", "email",
                 "password", "avatar"); se manca vale None e l'errore riguarda tutto il modulo.
    """

    def __init__(self, message, field=None):
        # super().__init__(message): fa il lavoro del costruttore di Exception, che
        # conserva il messaggio (lo stampa per esempio un traceback)
        super().__init__(message)
        self.message = message
        self.field = field


class LoginLimiter:
    """Errori di login per account, in memoria, sotto un lock (le richieste arrivano da più thread).

    In parole semplici:
        LoginLimiter(clock)
        Tiene il conto dei login sbagliati per ogni chiave (per esempio "utente:7" o
        "testo:nina@x.it", vedi _attempts_key) e dice se una chiave è bloccata.
        clock: facoltativo; la funzione che dà l'ora in secondi, per esempio
               time.monotonic (il valore predefinito: un orologio che non torna mai
               indietro, anche se si cambia l'ora del PC). I test passano un orologio
               finto per far passare il tempo senza aspettare.
        Il lock (threading.Lock) è un "lucchetto": Flask risponde a più richieste
        insieme, in thread diversi, e con "with self._lock:" una sola alla volta legge
        o cambia il dizionario. Si apre da solo alla fine del blocco with.
    """

    SWEEP_SIZE = 1000  # oltre questo numero di voci si tolgono quelle scadute

    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self._lock = threading.Lock()
        # _entries: chiave -> [errori, bloccato_fino_a (None = non bloccato), ora dell'ultimo errore],
        # per esempio {"utente:7": [2, None, 5031.2]} (due errori, non ancora bloccato)
        self._entries = {}

    def is_locked(self, username):
        """True se la chiave è bloccata adesso.

        In parole semplici:
            is_locked(username)
            username: la chiave dei tentativi, per esempio "utente:7" (da _attempts_key).
            Restituisce True durante il blocco; a blocco finito toglie la voce e
            restituisce False, così si riparte da zero errori.
        """
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

        In parole semplici:
            record_failure(username, max_attempts, lock_seconds)
            Per esempio record_failure("utente:7", 5, 300): il quinto errore blocca
            la chiave per 300 secondi e restituisce True; prima restituisce False.
            username:     la chiave dei tentativi (da _attempts_key)
            max_attempts: quanti errori bloccano; LOGIN_MAX_ATTEMPTS di config.py
            lock_seconds: quanto dura il blocco; LOGIN_LOCK_SECONDS di config.py
        """
        with self._lock:
            now = self._clock()

            # Pulizia: con troppe voci si tengono solo quelle ancora bloccate o con un
            # errore recente (il nuovo dizionario mantiene l'ordine di prima)
            if len(self._entries) >= self.SWEEP_SIZE:
                kept = {}
                for key, value in self._entries.items():
                    still_locked = value[1] is not None and value[1] > now
                    recent_error = now - value[2] < lock_seconds
                    if still_locked or recent_error:
                        kept[key] = value
                self._entries = kept

            # Una voce nuova se non c'era, o se l'ultimo errore è troppo vecchio
            entry = self._entries.get(username)
            if entry is None or (entry[1] is None and now - entry[2] >= lock_seconds):
                entry = [0, None, now]
                self._entries[username] = entry

            # Si conta l'errore; al massimo si blocca fino a now + lock_seconds
            entry[0] += 1
            entry[2] = now
            if entry[0] >= max_attempts:
                entry[1] = now + lock_seconds
                return True
            return False

    def reset(self, username=None):
        """Dimentica gli errori di una chiave, o di tutte.

        In parole semplici:
            reset(username)
            username: facoltativo; la chiave da dimenticare (per esempio dopo un login
                      riuscito). Se manca (None) si dimenticano tutte.
        """
        with self._lock:
            if username is None:
                self._entries.clear()
            else:
                self._entries.pop(username, None)  # pop con None: niente errore se non c'è


# limiter: l'unico conto dei tentativi del server (i test lo sostituiscono con uno nuovo)
limiter = LoginLimiter()


def register(username, email, password):
    """Crea l'utente e lo restituisce; username o email già usati → AuthError sul campo.

    In parole semplici:
        register(username, email, password)
        Per esempio register("Mario", "mario@x.it", "segreta1") -> l'utente nuovo.
        I tre valori arrivano da api.py (/api/auth/register), già controllati dal
        modulo (lunghezze e caratteri). La password si salva solo come hash.
        try / except: se il commit fallisce con IntegrityError (un vincolo unico
        violato) si annulla la transazione e si dice quale campo è già usato;
        "raise ... from None" lancia l'errore nuovo senza attaccargli quello di
        MySQL, che conterrebbe lo username o l'email (non vanno nei log).
        Un'altra violazione, che non ci si aspetta, si rilancia così com'è (raise).
    """
    user = user_repo.add(username, email, generate_password_hash(password))
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        # text: il messaggio di MySQL, che contiene il nome del vincolo violato
        text = str(exc.orig)
        if "uq_utenti_nome" in text:
            raise AuthError(USERNAME_TAKEN, "username") from None
        if "uq_utenti_email" in text:
            raise AuthError(EMAIL_TAKEN, "email") from None
        raise
    log.info("Nuovo utente registrato (id %s)", user.id)
    return user


def authenticate(login, password):
    """Restituisce l'utente se nome utente (o email) e password sono giusti; altrimenti AuthError.

    In parole semplici:
        authenticate(login, password)
        Per esempio authenticate("Mario", "segreta1") oppure
        authenticate("mario@x.it", "segreta1") -> l'utente.
        login:    quello che l'utente ha scritto nel campo "Nome utente o email" (da api.py)
        password: la password scritta
        Con la chiave bloccata, o con troppi errori, AuthError(LOGIN_LOCKED); con
        dati sbagliati AuthError(LOGIN_FAILED), lo stesso messaggio se l'account
        non esiste o se la password è sbagliata.
    """
    config = current_app.config

    # Con una @ è un'email: si cerca l'account per email, altrimenti per username.
    # written: il testo con cui contare i tentativi se l'account non c'è; un'email si
    # confronta senza maiuscole (casefold, come la colonna), uno username no (D7)
    is_email = "@" in login
    if is_email:
        user = user_repo.get_by_email(login)
        written = login.casefold()
    else:
        user = user_repo.get_by_username(login)
        written = login
    key = _attempts_key(user, written)
    if limiter.is_locked(key):
        raise AuthError(LOGIN_LOCKED)

    # Il controllo della password si fa sempre, anche senza account (con _DUMMY_HASH):
    # così la risposta impiega lo stesso tempo
    if user is not None:
        stored_hash = user.password_hash
    else:
        stored_hash = _DUMMY_HASH
    ok = check_password_hash(stored_hash, password)
    if user is None or not ok:
        locked = limiter.record_failure(key, config["LOGIN_MAX_ATTEMPTS"], config["LOGIN_LOCK_SECONDS"])
        if locked:
            log.warning("Login bloccato per troppi tentativi sbagliati")
            raise AuthError(LOGIN_LOCKED)
        raise AuthError(LOGIN_FAILED)

    # Login riuscito: gli errori di prima si dimenticano
    limiter.reset(key)
    return user


def _attempts_key(user, written):
    """P96: il conto dei tentativi è per account; per un account che non c'è, per il testo scritto.

    Le due chiavi non si confondono: una comincia con "utente:", l'altra con "testo:".

    In parole semplici:
        _attempts_key(user, written)
        Per esempio _attempts_key(mario, "Mario") = "utente:7" (Mario ha il numero 7) e
        _attempts_key(None, "nessuno") = "testo:nessuno".
        user:    l'utente trovato, o None (da authenticate e delete_account)
        written: lo username o l'email scritti (l'email già senza maiuscole)
    """
    if user is not None:
        return f"utente:{user.id}"
    return f"testo:{written}"


def set_avatar(user, code):
    """Salva l'avatar scelto; "" = nessun avatar (iniziale). Un codice fuori elenco → AuthError.

    In parole semplici:
        set_avatar(user, code)
        Per esempio set_avatar(mario, "re_coppe"), oppure set_avatar(mario, "") per
        tornare all'iniziale del nome.
        user: l'utente collegato (da profile/api.py, current_user)
        code: il codice scelto nelle impostazioni, uno di avatars.AVATARS o ""
    """
    if code == "":
        code = None
    elif not avatars.is_valid(code):
        raise AuthError(AVATAR_INVALID, "avatar")
    user_repo.set_avatar(user, code)
    db.session.commit()


def delete_account(user, password):
    """Cancella l'account dopo aver controllato la password; altrimenti AuthError.

    In parole semplici:
        delete_account(user, password)
        Per esempio delete_account(mario, "segreta1").
        user:     l'utente collegato (da profile/api.py, current_user)
        password: la password scritta nella finestra di conferma; può non essere un
                  testo (arriva dal JSON della pagina), e allora si rifiuta
        Gli errori di password contano come quelli del login (stessa chiave).
    """
    config = current_app.config
    user_id = user.id
    key = _attempts_key(user, user.username)  # lo stesso conto del login (P17, P96)

    # Controlli, nell'ordine: password scritta, blocco, password giusta, nessuna partita
    if not isinstance(password, str) or not password:
        raise AuthError(DELETE_NO_PASSWORD, "password")
    if limiter.is_locked(key):
        raise AuthError(LOGIN_LOCKED)
    if not check_password_hash(user.password_hash, password):
        locked = limiter.record_failure(key, config["LOGIN_MAX_ATTEMPTS"], config["LOGIN_LOCK_SECONDS"])
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
    limiter.reset(key)
    log.info("Account cancellato (id %s)", user_id)


def load_user(user_id):
    """Per Flask-Login: l'utente della sessione, o None se l'id non è valido o non esiste più.

    In parole semplici:
        load_user(user_id)
        Per esempio load_user("7") -> l'utente numero 7; load_user("abc") -> None.
        user_id: il numero dell'utente salvato nel cookie di sessione, come testo;
                 lo passa Flask-Login a ogni richiesta.
        try / except: int("abc") lancia ValueError (e int(None) TypeError): in quei
        casi l'id non è valido e si restituisce None, cioè "nessuno collegato".
    """
    try:
        return user_repo.get_by_id(int(user_id))
    except (TypeError, ValueError):
        return None
