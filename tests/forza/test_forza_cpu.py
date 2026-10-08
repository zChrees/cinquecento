"""Prove di forza della CPU (D43, "Fatto quando"): la strategia "simulazione" contro il
"giocatore medio" (heuristic_move, la prima CPU del 30/09/2026), in partite intere con il
motore vero. P122: suite a parte, perché sono le prove più lente (nella suite engine
l'avrebbero portata oltre i 200 s); le altre prove della CPU sono in tests/engine/test_cpu.py.

La CPU pensa un terzo del vero, per stare nei tempi della suite: con meno ancora (600 carte,
minimo 4 mani) perdeva, perché le mani immaginate sono troppo poche. Con un rng fisso le
partite sono sempre le stesse: il numero di vittorie non cambia da un giro all'altro.
"""

import random

from app.game.engine import cpu as cpu_module
from app.game.engine.cpu import CpuMemory, cpu_move, heuristic_move
from app.game.engine.game import apply_game, new_game
from app.game.engine.views import player_view


def third_of_the_budget(monkeypatch):
    monkeypatch.setattr(cpu_module, "SIMULATED_PLAYS", 1500)
    monkeypatch.setattr(cpu_module, "MIN_WORLDS", 8)


def play_match(players, seed, mine):
    """Partita intera: la squadra `mine` gioca con la CPU, l'altra da giocatore medio.

    Ogni CPU ricorda le carte uscite (CpuMemory), che vede da ogni vista nuova del suo posto,
    come fa la stanza. Restituisce True se vince la squadra della CPU.
    """
    rng = random.Random(seed)
    game = new_game(players, 150, rng=rng)
    memories = {seat: CpuMemory() for seat in range(players)}
    while not game.finished:
        for seat, memory in memories.items():
            memory.see(player_view(game, seat))
        seat = game.hand.turn_seat
        view = player_view(game, seat)
        if seat % 2 == mine:
            action = cpu_move(view, rng, memories[seat])
        else:
            action = heuristic_move(view, rng)
        game = apply_game(game, action, rng=rng)
    return game.result.winner_team == mine


def test_la_cpu_batte_il_giocatore_medio(monkeypatch):
    """1v1 (P68): il 04/10/2026 con un terzo ha vinto 28 partite su 40, con il budget vero
    81 su 100. Qui 12 partite (ne vince 9), metà da un posto e metà dall'altro."""
    third_of_the_budget(monkeypatch)
    wins = sum(play_match(2, seed, mine=seed % 2) for seed in range(12))
    assert wins >= 8, wins


def test_nel_2v2_la_coppia_di_cpu_batte_la_coppia_media(monkeypatch):
    """2v2 (P122): due CPU in coppia contro due giocatori medi; la CPU vede le carte scoperte
    del compagno a mazzo finito (D46). Misure del 08/10/2026: con un terzo ha vinto 30 partite
    su 40, con il budget vero 27 su 40; una mossa dura come nel 1v1. Qui 24 partite (ne vince
    17, circa 80 s), metà con le CPU nella squadra 0 e metà nella squadra 1."""
    third_of_the_budget(monkeypatch)
    wins = sum(play_match(4, seed, mine=seed % 2) for seed in range(24))
    assert wins >= 15, wins
