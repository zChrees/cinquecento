"""Calcolo del rating Glicko-2 (P27), in Python puro: niente Flask né database.

Segue il documento di Mark Glickman, "Example of the Glicko-2 system" (2013),
passi 1–8; il test lo confronta con l'esempio numerico del documento.
Parole usate:
- rating (r): il valore mostrato, parte da 1500;
- deviazione (RD): quanto il sistema è incerto sul rating, parte da 350 e scende giocando;
- volatilità (σ): quanto il rating oscilla, parte da 0,06;
- tau (τ): quanto può cambiare la volatilità (GLICKO_TAU in config.py).
Ogni partita è un "periodo" a sé: update() riceve i risultati di quella partita.
"""

import math
from dataclasses import dataclass

SCALE = 173.7178  # conversione tra la scala di Glicko e quella interna di Glicko-2
CENTER = 1500
EPSILON = 0.000001  # precisione del calcolo della volatilità (passo 5)


@dataclass(frozen=True)
class Rating:
    value: float
    deviation: float
    volatility: float


@dataclass(frozen=True)
class Result:
    """Un avversario e il risultato: 1 vittoria, 0.5 pareggio, 0 sconfitta."""

    opponent: Rating
    score: float


def _g(phi):
    return 1 / math.sqrt(1 + 3 * phi * phi / math.pi ** 2)


def _expected(mu, mu_j, phi_j):
    return 1 / (1 + math.exp(-_g(phi_j) * (mu - mu_j)))


def update(player, results, tau):
    """Il nuovo Rating di `player` dopo i `results` del periodo."""
    mu = (player.value - CENTER) / SCALE
    phi = player.deviation / SCALE
    sigma = player.volatility

    if not results:
        # Passo 6 senza partite: cresce solo la deviazione
        return Rating(player.value, math.sqrt(phi * phi + sigma * sigma) * SCALE, sigma)

    # Passi 3 e 4: varianza stimata e miglioramento stimato
    games = []
    for result in results:
        mu_j = (result.opponent.value - CENTER) / SCALE
        phi_j = result.opponent.deviation / SCALE
        games.append((_g(phi_j), _expected(mu, mu_j, phi_j), result.score))
    v = 1 / sum(g * g * e * (1 - e) for g, e, _s in games)
    delta = v * sum(g * (s - e) for g, e, s in games)

    # Passo 5: nuova volatilità (metodo di Illinois)
    a = math.log(sigma * sigma)

    def f(x):
        ex = math.exp(x)
        return ex * (delta * delta - phi * phi - v - ex) / (2 * (phi * phi + v + ex) ** 2) - (x - a) / (tau * tau)

    big_a = a
    if delta * delta > phi * phi + v:
        big_b = math.log(delta * delta - phi * phi - v)
    else:
        k = 1
        while f(a - k * tau) < 0:
            k += 1
        big_b = a - k * tau
    f_a, f_b = f(big_a), f(big_b)
    while abs(big_b - big_a) > EPSILON:
        big_c = big_a + (big_a - big_b) * f_a / (f_b - f_a)
        f_c = f(big_c)
        if f_c * f_b <= 0:
            big_a, f_a = big_b, f_b
        else:
            f_a /= 2
        big_b, f_b = big_c, f_c
    new_sigma = math.exp(big_a / 2)

    # Passi 6–8: nuova deviazione e nuovo rating, riportati sulla scala di Glicko
    phi_star = math.sqrt(phi * phi + new_sigma * new_sigma)
    new_phi = 1 / math.sqrt(1 / (phi_star * phi_star) + 1 / v)
    new_mu = mu + new_phi * new_phi * sum(g * (s - e) for g, e, s in games)
    return Rating(CENTER + SCALE * new_mu, SCALE * new_phi, new_sigma)


def team_opponent(ratings):
    """La squadra avversaria vista come un solo avversario (2v2, scelta (a) di P27):
    rating medio e deviazione media (radice della media dei quadrati)."""
    count = len(ratings)
    value = sum(r.value for r in ratings) / count
    deviation = math.sqrt(sum(r.deviation ** 2 for r in ratings) / count)
    volatility = sum(r.volatility for r in ratings) / count
    return Rating(value, deviation, volatility)
