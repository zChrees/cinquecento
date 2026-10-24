"""Calcolo del rating Glicko-2 (P27), in Python puro: niente Flask né database.

Segue il documento di Mark Glickman, "Example of the Glicko-2 system" (2013),
passi 1–8; il test lo confronta con l'esempio numerico del documento.
Parole usate:
- rating (r): il valore mostrato, parte da 1500;
- deviazione (RD): quanto il sistema è incerto sul rating, parte da 350 e scende giocando;
- volatilità (σ): quanto il rating oscilla, parte da 0,06;
- tau (τ): quanto può cambiare la volatilità (GLICKO_TAU in config.py).
Ogni partita è un "periodo" a sé: update() riceve i risultati di quella partita.

Cosa contiene:
    Rating(value, deviation, volatility)   un rating, per esempio Rating(1500, 350, 0.06)
    Result(opponent, score)                un avversario e il risultato, per esempio Result(avversario, 1.0)
    update(player, results, tau)           il rating nuovo dopo una partita
    team_opponent(ratings)                 la squadra avversaria vista come un solo avversario

I nomi brevi (mu, phi, sigma, g, e, v, delta) sono quelli delle formule del documento
di Glickman, così il codice si confronta riga per riga con il documento.

DA DOVE ARRIVANO I DATI: rating_service.py chiama update e team_opponent con i rating
letti dal database, a fine partita.
"""

import math
from dataclasses import dataclass

SCALE = 173.7178  # conversione tra la scala di Glicko e quella interna di Glicko-2
CENTER = 1500
EPSILON = 0.000001  # precisione del calcolo della volatilità (passo 5)


# @dataclass(frozen=True): costruttore automatico e campi che non si cambiano più
# (vedi il commento in app/game/engine/cards.py)
@dataclass(frozen=True)
class Rating:
    """Un rating Glicko-2.

    In parole semplici:
        Rating(1500.0, 350.0, 0.06)
        value:      il valore mostrato, per esempio 1523.4
        deviation:  la deviazione (RD), per esempio 290.3
        volatility: la volatilità (σ), per esempio 0.0599
    """

    value: float
    deviation: float
    volatility: float


@dataclass(frozen=True)
class Result:
    """Un avversario e il risultato: 1 vittoria, 0.5 pareggio, 0 sconfitta."""

    opponent: Rating
    score: float


def _g(phi):
    """La funzione g(φ) del documento: pesa meno un avversario con un rating incerto.

    In parole semplici:
        _g(phi)
        phi: la deviazione dell'avversario sulla scala interna. Restituisce un numero
        tra 0 e 1 (1 se l'avversario ha deviazione 0).
    """
    return 1 / math.sqrt(1 + 3 * phi * phi / math.pi ** 2)


def _expected(mu, mu_j, phi_j):
    """La funzione E del documento: la probabilità di vincere contro quell'avversario.

    In parole semplici:
        _expected(mu, mu_j, phi_j)
        mu: il rating del giocatore; mu_j e phi_j: rating e deviazione
        dell'avversario, tutti sulla scala interna. Per esempio 0.5 tra due giocatori
        con lo stesso rating.
    """
    return 1 / (1 + math.exp(-_g(phi_j) * (mu - mu_j)))


def update(player, results, tau):
    """Il nuovo Rating di `player` dopo i `results` del periodo.

    In parole semplici:
        update(player, results, tau)
        player:  il Rating del giocatore prima della partita.
        results: la lista dei Result della partita (qui sempre uno: l'avversario, o
                 la squadra avversaria vista come un solo avversario).
        tau:     GLICKO_TAU di config.py.
        Arrivano da rating_service.apply_match. Restituisce il Rating nuovo.
    """
    # Passo 2: dalla scala di Glicko a quella interna
    mu = (player.value - CENTER) / SCALE
    phi = player.deviation / SCALE
    sigma = player.volatility

    if len(results) == 0:
        # Passo 6 senza partite: cresce solo la deviazione
        return Rating(player.value, math.sqrt(phi * phi + sigma * sigma) * SCALE, sigma)

    # Passi 3 e 4: varianza stimata e miglioramento stimato.
    # games: per ogni avversario la terna (g, E, risultato)
    games = []
    for result in results:
        mu_j = (result.opponent.value - CENTER) / SCALE
        phi_j = result.opponent.deviation / SCALE
        games.append((_g(phi_j), _expected(mu, mu_j, phi_j), result.score))

    # v: la varianza stimata (1 diviso la somma di g² · E · (1 - E))
    variance_sum = 0
    for game in games:
        g = game[0]
        e = game[1]
        variance_sum = variance_sum + g * g * e * (1 - e)
    v = 1 / variance_sum

    # improvement: la somma di g · (risultato - E), che serve due volte (delta e new_mu)
    improvement = 0
    for game in games:
        g = game[0]
        e = game[1]
        s = game[2]
        improvement = improvement + g * (s - e)
    delta = v * improvement

    # Passo 5: nuova volatilità (metodo di Illinois)
    a = math.log(sigma * sigma)

    def f(x):
        """La funzione f(x) del passo 5, di cui si cerca lo zero (legge delta, phi, v, a e tau)."""
        ex = math.exp(x)
        return ex * (delta * delta - phi * phi - v - ex) / (2 * (phi * phi + v + ex) ** 2) - (x - a) / (tau * tau)

    # Il metodo di Illinois cerca lo zero di f tra due punti A e B, che si avvicinano
    # a ogni giro finché distano meno di EPSILON
    big_a = a
    if delta * delta > phi * phi + v:
        big_b = math.log(delta * delta - phi * phi - v)
    else:
        k = 1
        while f(a - k * tau) < 0:
            k += 1
        big_b = a - k * tau
    f_a = f(big_a)
    f_b = f(big_b)
    while abs(big_b - big_a) > EPSILON:
        big_c = big_a + (big_a - big_b) * f_a / (f_b - f_a)
        f_c = f(big_c)
        if f_c * f_b <= 0:
            big_a = big_b
            f_a = f_b
        else:
            f_a /= 2
        big_b = big_c
        f_b = f_c
    new_sigma = math.exp(big_a / 2)

    # Passi 6–8: nuova deviazione e nuovo rating, riportati sulla scala di Glicko
    phi_star = math.sqrt(phi * phi + new_sigma * new_sigma)
    new_phi = 1 / math.sqrt(1 / (phi_star * phi_star) + 1 / v)
    new_mu = mu + new_phi * new_phi * improvement
    return Rating(CENTER + SCALE * new_mu, SCALE * new_phi, new_sigma)


def team_opponent(ratings):
    """La squadra avversaria vista come un solo avversario (2v2, scelta (a) di P27):
    rating medio e deviazione media (radice della media dei quadrati).

    In parole semplici:
        team_opponent([rating_a, rating_b])
        ratings: i Rating dei due avversari. Arriva da rating_service.apply_match.
        Restituisce un Rating con la media dei valori, la radice della media dei
        quadrati delle deviazioni e la media delle volatilità.
    """
    count = len(ratings)
    value_sum = 0
    square_sum = 0
    volatility_sum = 0
    for rating in ratings:
        value_sum = value_sum + rating.value
        square_sum = square_sum + rating.deviation ** 2
        volatility_sum = volatility_sum + rating.volatility
    value = value_sum / count
    deviation = math.sqrt(square_sum / count)
    volatility = volatility_sum / count
    return Rating(value, deviation, volatility)
