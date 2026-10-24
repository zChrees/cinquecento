"""Frasi del tavolo (P55, D24, contratto 3.2): l'elenco unico e il limite di tempo.

- Al tavolo si mandano solo frasi di questo elenco, per codice: niente testo libero.
- Il server controlla la frase, la manda a tutti i giocatori della partita e la
  dimentica: non si salva da nessuna parte e non si scrive nel log.
- Al massimo una frase ogni TABLE_PHRASE_MIN_INTERVAL_SECONDS per giocatore; l'ora
  dell'ultima frase di ogni posto sta nella stanza (room.phrase_times) e sparisce con lei.
- L'elenco arriva alla pagina con game:phrases a ogni game:join: la pagina non ne
  tiene una copia sua.

Cosa contiene:
    MIN_INTERVAL_SECONDS          i secondi minimi tra due frasi dello stesso giocatore (3)
    PHRASES                       l'elenco: codice -> testo, per esempio "ciao" -> "Ciao!"
    phrases_event()               i dati dell'evento game:phrases
    check_code(code)              controlla che il codice sia dell'elenco
    take_turn(room, seat, now)    registra la frase di un posto, o la rifiuta se è troppo presto

DA DOVE ARRIVANO I DATI: game_events.py (game:phrase e game:join) chiama queste
funzioni con il codice mandato dalla pagina e con la stanza del giocatore.
"""

import math
import time

from app.realtime.events import EventError
from config import BaseConfig

# MIN_INTERVAL_SECONDS: da config.py. take_turn lo legge al momento della frase, così
# i test possono ridurlo (monkeypatch) senza toccare config.py
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
    """Dati di game:phrases.

    In parole semplici:
        phrases_event()
        Restituisce {"phrases": [{"code": "ciao", "text": "Ciao!"}, ...]}, nell'ordine
        di PHRASES (in Python un dizionario tiene l'ordine in cui le chiavi sono state
        scritte). La manda game_events.py a ogni game:join.
    """
    phrases = []
    # items(): le coppie (codice, testo) del dizionario, una alla volta
    for code, text in PHRASES.items():
        phrases.append({"code": code, "text": text})
    return {"phrases": phrases}


def check_code(code):
    """Controlla il codice di una frase.

    In parole semplici:
        check_code("ciao")
        code: quello che ha mandato la pagina con game:phrase. Se non è un testo o non è
        nell'elenco, la richiesta si rifiuta con invalid_data; altrimenti lo restituisce.
    """
    if not isinstance(code, str) or code not in PHRASES:
        raise EventError("invalid_data", "Frase non valida.")
    return code


def take_turn(room, seat, now=None):
    """Registra la frase del posto `seat`, o rifiuta con too_fast (sotto il lock della stanza).

    In parole semplici:
        take_turn(room, seat)
        room: la stanza del giocatore (Room di room.py); in room.phrase_times c'è l'ora
              dell'ultima frase di ogni posto.
        seat: il posto di chi manda la frase.
        now:  facoltativo, l'ora in secondi (time.monotonic); se manca si legge adesso.
              I test la passano per non aspettare davvero.
        Arrivano da game_events.py, che la chiama dentro room.run (il lock della stanza).

        Se l'ultima frase di quel posto è di meno di MIN_INTERVAL_SECONDS fa, lancia
        EventError("too_fast") con retry_after (i secondi da aspettare, almeno 1);
        altrimenti segna l'ora nuova e non restituisce niente.
    """
    if now is None:
        now = time.monotonic()
    interval = MIN_INTERVAL_SECONDS  # letto qui: i test lo riducono
    last = room.phrase_times.get(seat)
    if last is not None and now - last < interval:
        # quanto manca, arrotondato in su (math.ceil), e almeno 1 secondo
        wait = max(1, math.ceil(interval - (now - last)))
        raise EventError("too_fast", "Aspetta un momento prima di mandare un'altra frase.", retry_after=wait)
    room.phrase_times[seat] = now
