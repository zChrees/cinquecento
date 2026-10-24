"""Statistiche di un utente per il pannello che si apre dall'avatar (P30; contratto 2.1).

- games, wins, losses, draws: tutte le partite finite, di ogni modalità e punteggio;
  una partita abbandonata è persa (anche per il compagno, D13).
- win_rate: percentuale di vittorie sulle partite giocate (pareggi compresi), intero
  arrotondato (la metà per eccesso); None se non ha ancora giocato.
- ratings: per 1v1 e 2v2 il valore arrotondato (1500 se non c'è la riga, D9), le
  partite che contano per il rating in quella modalità e "provvisorio" per le prime
  RATING_PROVISIONAL_GAMES (10). "Provvisorio" non si salva: si conta (P27).
Un utente vede solo le proprie statistiche: la rotta passa sempre current_user.id.

Cosa contiene:
    win_rate(wins, games)   la percentuale di vittorie, per esempio win_rate(1, 3) = 33
    stats_of(user_id)       tutte le statistiche di un utente

DA DOVE ARRIVANO I DATI: la rotta GET /api/stats/me (app/blueprints/stats/routes.py)
e create_room (il rating da mostrare al tavolo, P88) chiamano stats_of; i numeri si
leggono con stats_repo.
"""

import math

from flask import current_app

from app.models.match import MODES
from app.repositories import stats_repo


def win_rate(wins, games):
    """La percentuale di vittorie, arrotondata all'intero (la metà per eccesso).

    In parole semplici:
        win_rate(wins, games)
        Per esempio win_rate(1, 8) = 13 (12,5 arrotondato per eccesso); None con 0 partite.
        Il conto è fatto solo con interi ("//" è la divisione intera): niente
        arrotondamenti dei numeri con la virgola.
    """
    if games == 0:
        return None
    return (wins * 100 * 2 + games) // (games * 2)  # arrotondata, la metà per eccesso


def stats_of(user_id):
    """Le statistiche di un utente nella forma del contratto (2.1).

    In parole semplici:
        stats_of(7)
        Restituisce per esempio {"games": 12, "wins": 7, "losses": 4, "draws": 1,
        "win_rate": 58, "ratings": {"1v1": {"value": 1534, "games": 8,
        "provisional": True}, "2v2": {...}}}.
    """
    config = current_app.config
    results = stats_repo.results(user_id)
    # get(chiave, 0): il numero di quel risultato, 0 se non ce ne sono
    wins = results.get("vittoria", 0)
    losses = results.get("sconfitta", 0)
    draws = results.get("pareggio", 0)
    games = wins + losses + draws

    rated = stats_repo.rated_games(user_id)
    values = stats_repo.rating_values(user_id)
    ratings = {}
    for mode in MODES:
        count = rated.get(mode, 0)
        ratings[mode] = {
            # floor(x + 0,5): arrotonda la metà per eccesso (round di Python la arrotonda al pari)
            "value": math.floor(values.get(mode, config["RATING_INITIAL"]) + 0.5),
            "games": count,
            "provisional": count < config["RATING_PROVISIONAL_GAMES"],
        }
    return {
        "games": games,
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "win_rate": win_rate(wins, games),
        "ratings": ratings,
    }
