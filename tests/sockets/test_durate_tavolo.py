"""Passo 8 della migrazione: le durate del tavolo uguali tra server e pagina.

Il server aspetta le pause del tavolo (P94: presa chiusa, riepilogo, lanci, pescate,
mescolata, distribuzione, carte calate) prima di far partire il turno, e la pagina
mostra quelle stesse animazioni: se i numeri non sono uguali, il tempo del turno
parte prima o dopo la fine dell'animazione. Dal lotto 9a (tavolo Jinja tolto) la
copia lato pagina è una sola, frontend/src/game/animations.ts. Questo file controlla:
- ogni pausa di app/realtime/room.py (in secondi) è uguale, in millisecondi, a
  quella di animations.ts;
- la pausa delle frasi è uguale al limite del server (table_phrases, P55, P56);
- TRICK_AWAY_MS e AWAY_DELAY_MS (i due nomi della stessa attesa) sono uguali;
- ogni riga di animations.ts che non è un commento ha la forma
  "export const NOME_MS: number = 1500;", quella che i test leggono.
I file si leggono come testo: non serve né il server, né MySQL, né Node.
Tutti i confronti delle durate stanno qui.
"""

import re
from pathlib import Path

import pytest

from app.realtime import room as room_module
from app.realtime import table_phrases

ROOT = Path(__file__).resolve().parents[2]
ANIMATIONS_TS = ROOT / "frontend" / "src" / "game" / "animations.ts"
# LINE: la forma di ogni durata in animations.ts
LINE = re.compile(r"export const ([A-Z_]+): number = (\d+);")
# PAUSES: durata della pagina (ms) → pausa del server (secondi, in room.py)
PAUSES = [
    ("LAST_TRICK_MS", "LAST_TRICK_SECONDS"),
    ("SUMMARY_MS", "SUMMARY_SECONDS"),
    ("THROW_MS", "THROW_SECONDS"),
    ("DRAW_MS", "DRAW_SECONDS"),
    ("SHUFFLE_MS", "SHUFFLE_SECONDS"),
    ("DEAL_STEP_MS", "DEAL_STEP_SECONDS"),
    ("LAID_DOWN_MS", "LAID_DOWN_SECONDS"),
]


def _ts_constants():
    """Le durate di animations.ts, controllando la forma di ogni riga."""
    found = {}
    for number, line in enumerate(ANIMATIONS_TS.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith(("/*", "*", "//")):
            continue
        match = LINE.fullmatch(stripped)
        assert match, f"animations.ts, riga {number}: forma diversa da 'export const NOME_MS: number = 1500;'"
        assert match.group(1) not in found, f"animations.ts: {match.group(1)} scritta due volte"
        found[match.group(1)] = int(match.group(2))
    return found


@pytest.fixture(scope="module")
def page():
    return _ts_constants()


@pytest.mark.parametrize(("ms", "seconds"), PAUSES)
def test_pause_del_server_uguali_a_quelle_della_pagina(page, ms, seconds):
    assert ms in page, f"{ms} manca in animations.ts"
    assert page[ms] == round(getattr(room_module, seconds) * 1000), f"{ms} di animations.ts contro {seconds} di room.py"


def test_pausa_delle_frasi_uguale_al_limite_del_server(page):
    assert page["PHRASE_PAUSE_MS"] == round(table_phrases.MIN_INTERVAL_SECONDS * 1000)


def test_presa_che_scivola_via_uguale_nei_due_nomi(page):
    # TRICK_AWAY_MS (il suono) e AWAY_DELAY_MS (l'animazione) sono la stessa attesa
    assert page["TRICK_AWAY_MS"] == page["AWAY_DELAY_MS"]
