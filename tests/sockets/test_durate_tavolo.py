"""Passo 8 della migrazione: le durate del tavolo uguali tra server e pagina.

Il server aspetta le pause del tavolo (P94: presa chiusa, riepilogo, lanci, pescate,
mescolata, distribuzione, carte calate) prima di far partire il turno, e la pagina
mostra quelle stesse animazioni: se i numeri non sono uguali, il tempo del turno
parte prima o dopo la fine dell'animazione. Fino al passo 9 le copie lato pagina
sono due: app/static/js/pages/game.js (tavolo Jinja) e frontend/src/game/animations.ts
(tavolo React, dal passo 8a). Questo file le controlla tutte e due:
- ogni pausa di app/realtime/room.py (in secondi) è uguale, in millisecondi, a
  quella di game.js e di animations.ts;
- la pausa delle frasi è uguale al limite del server (table_phrases, P55, P56);
- animations.ts ha le stesse durate di game.js (e AWAY_DELAY_MS di Trick.js), con gli
  stessi nomi, e nessuna in più;
- ogni riga di animations.ts che non è un commento ha la forma
  "export const NOME_MS: number = 1500;", quella che i test leggono.
I file si leggono come testo: non serve né il server, né MySQL, né Node.
Il confronto con game.js c'era già, sparso (test_turno.py, table6/test_calata.py,
table5/test_frasi_pagina.py): resta lì finché c'è game.js (passo 9).
"""

import re
from pathlib import Path

import pytest

from app.realtime import room as room_module
from app.realtime import table_phrases

ROOT = Path(__file__).resolve().parents[2]
GAME_JS = ROOT / "app" / "static" / "js" / "pages" / "game.js"
TRICK_JS = ROOT / "app" / "static" / "js" / "components" / "Trick.js"
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


def _js_constants(path):
    """Le costanti numeriche di un file JS: "const NOME = 1500;" → {"NOME": 1500}."""
    text = path.read_text(encoding="utf-8")
    return {name: int(value) for name, value in re.findall(r"^const ([A-Z_]+) = (\d+);", text, flags=re.MULTILINE)}


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
    return {"game.js": _js_constants(GAME_JS), "animations.ts": _ts_constants()}


@pytest.mark.parametrize("copy", ["game.js", "animations.ts"])
@pytest.mark.parametrize(("ms", "seconds"), PAUSES)
def test_pause_del_server_uguali_a_quelle_della_pagina(page, copy, ms, seconds):
    assert ms in page[copy], f"{ms} manca in {copy}"
    assert page[copy][ms] == round(getattr(room_module, seconds) * 1000), f"{ms} di {copy} contro {seconds} di room.py"


@pytest.mark.parametrize("copy", ["game.js", "animations.ts"])
def test_pausa_delle_frasi_uguale_al_limite_del_server(page, copy):
    assert page[copy]["PHRASE_PAUSE_MS"] == round(table_phrases.MIN_INTERVAL_SECONDS * 1000)


def test_animations_ts_ha_le_durate_di_game_js(page):
    # Le stesse durate, con gli stessi nomi; AWAY_DELAY_MS sta in Trick.js, non in game.js
    old = dict(page["game.js"])
    old["AWAY_DELAY_MS"] = _js_constants(TRICK_JS)["AWAY_DELAY_MS"]
    new = page["animations.ts"]
    # Solo le durate (_MS) e il ticchettio: game.js ha anche altre costanti (HIDDEN, ...)
    wanted = {name: value for name, value in old.items() if name.endswith("_MS") or name == "TICK_SECONDS"}
    assert new == wanted


def test_presa_che_scivola_via_uguale_nei_due_nomi(page):
    # TRICK_AWAY_MS (game.js, il suono) e AWAY_DELAY_MS (Trick.js, l'animazione) sono la stessa attesa
    assert page["animations.ts"]["TRICK_AWAY_MS"] == page["animations.ts"]["AWAY_DELAY_MS"]
