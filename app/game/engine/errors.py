"""Errori del motore di gioco (P10).

Il messaggio è in italiano e si può mostrare così com'è al giocatore: non contiene
mai dettagli tecnici né carte che il giocatore non può vedere.

Cosa contiene (ognuno è un tipo di errore, dal più generale al più preciso):
    EngineError        qualsiasi errore del motore, per esempio EngineError("La partita è finita.")
    InvalidMoveError   una mossa non valida, per esempio InvalidMoveError("Carta non valida.")
    NotYourTurnError   la mossa di chi non è di turno: NotYourTurnError("Non è il tuo turno.")

Come si usano: il motore li "lancia" con raise e la funzione che lo ha chiamato
(la stanza, app/realtime/room.py, o un gestore di app/sockets/) li "prende" con
try/except e manda il messaggio al giocatore. In C non c'è niente di uguale: è come
uscire subito da tutte le funzioni chiamate, fino a quella che ha detto di voler
gestire quell'errore.

Ogni classe qui sotto "eredita" da quella tra parentesi: un NotYourTurnError è anche
un InvalidMoveError e un EngineError, quindi "except EngineError" li prende tutti.
"""


# Exception: la classe di base di Python per gli errori normali
class EngineError(Exception):
    """Base di tutti gli errori del motore."""


class InvalidMoveError(EngineError):
    """Mossa non valida: viene rifiutata e lo stato della partita non cambia."""


class NotYourTurnError(InvalidMoveError):
    """Mossa di chi non è di turno: il server risponde not_your_turn invece di illegal_move."""
