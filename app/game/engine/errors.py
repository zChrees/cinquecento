"""Errori del motore di gioco (P10).

Il messaggio è in italiano e si può mostrare così com'è al giocatore: non contiene
mai dettagli tecnici né carte che il giocatore non può vedere.
"""


class EngineError(Exception):
    """Base di tutti gli errori del motore."""


class InvalidMoveError(EngineError):
    """Mossa non valida: viene rifiutata e lo stato della partita non cambia."""
