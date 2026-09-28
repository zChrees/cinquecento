"""Frasi del tavolo (P55, D24, contratto 3.2): l'elenco unico e il limite di tempo.

- Al tavolo si mandano solo frasi di questo elenco, per codice: niente testo libero.
- Il server controlla la frase, la manda a tutti i giocatori della partita e la
  dimentica: non si salva da nessuna parte e non si scrive nel log.
- Al massimo una frase ogni TABLE_PHRASE_MIN_INTERVAL_SECONDS per giocatore; l'ora
  dell'ultima frase di ogni posto sta nella stanza (room.phrase_times) e sparisce con lei.
- L'elenco arriva alla pagina con game:phrases a ogni game:join: la pagina non ne
  tiene una copia sua.
"""

import math
import time

from app.realtime.events import EventError
from config import BaseConfig

MIN_INTERVAL_SECONDS = BaseConfig.TABLE_PHRASE_MIN_INTERVAL_SECONDS

# Elenco approvato (D24): codice -> testo, nell'ordine in cui la pagina li mostra
PHRASES = {
    "ciao": "Ciao!",
    "baciamo_le_mani": "Baciamo le mani",
    "sugnu_cca": "Sugnu cca!",
    "a_prossima": "Salutamu, a prossima!",
    "buona_fortuna": "Buona fortuna!",
    "bella_mossa": "Bella mossa!",
    "talia": "Talìa chi carta!",
    "mizzica": "Mizzica!",
    "chi_sciorti": "Chi sciorti!",
    "chi_fai_dormi": "Chi fai, dormi?",
    "spicciati": "Spìcciati!",
    "fozza": "Fozza!",
    "calati_juncu": "Càlati juncu ca passa la china",
    "cu_nesci": "Cu nesci, arrinesci",
    "bella_partita": "Bella partita!",
    "complimenti": "Complimenti!",
    "grazie": "Grazzi!",
    "amuni": "Amunì!",
    "amuni_nautra": "Amunì, n'autra!",
}


def phrases_event():
    """Dati di game:phrases."""
    return {"phrases": [{"code": code, "text": text} for code, text in PHRASES.items()]}


def check_code(code):
    if not isinstance(code, str) or code not in PHRASES:
        raise EventError("invalid_data", "Frase non valida.")
    return code


def take_turn(room, seat, now=None):
    """Registra la frase del posto `seat`, o rifiuta con too_fast (sotto il lock della stanza)."""
    now = time.monotonic() if now is None else now
    interval = MIN_INTERVAL_SECONDS  # letto qui: i test lo riducono
    last = room.phrase_times.get(seat)
    if last is not None and now - last < interval:
        wait = max(1, math.ceil(interval - (now - last)))
        raise EventError("too_fast", "Aspetta un momento prima di mandare un'altra frase.", retry_after=wait)
    room.phrase_times[seat] = now
