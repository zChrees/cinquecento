"""P20: componenti carta e mano, pagina di prova delle 40 carte.

Controlla il "Fatto quando" di SCALETTA.md (P20): la pagina di prova esiste e
carica i componenti; ogni carta ha data-suit e data-rank stabili; i semi e i
nomi delle carte sono quelli del motore (app/game/engine/cards.py) e del
contratto ({"suit", "rank"}, rank da 1 a 10); una carta fuori elenco si rifiuta.
I controlli sul comportamento di Card.js usano Node, se c'è (altrimenti si saltano).
"""

import json
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from app import create_app
from app.game.engine.cards import RANK_NAMES, Suit

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "app" / "static"
DEV = STATIC / "dev"
CARD_JS = STATIC / "js" / "components" / "Card.js"
ALLOWED_ORIGINS = {"https://fonts.googleapis.com", "https://fonts.gstatic.com"}


@pytest.fixture
def client():
    return create_app("testing").test_client()


def _node(script):
    """Esegue un modulo ES con Node e restituisce il JSON che stampa."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node non installato: controllo di Card.js saltato")
    result = subprocess.run(
        [node, "--input-type=module", "-e", script],
        capture_output=True, text=True, timeout=30, check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _card_js_url():
    return CARD_JS.resolve().as_uri()


# --- Pagina di prova ---------------------------------------------------------


def test_pagina_di_prova_servita_con_i_suoi_file(client):
    response = client.get("/static/dev/carte.html")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    response.close()
    assert '<script type="module" src="carte.js"></script>' in html
    for css in re.findall(r'href="(\.\./[^"]+\.css|carte\.css)"', html):
        path = (DEV / css).resolve()
        assert path.is_file(), css
    for name in ("card.css", "hand.css"):
        assert f'href="../css/components/{name}"' in html
    for name in ("carte.js", "carte.css"):
        response = client.get(f"/static/dev/{name}")
        assert response.status_code == 200, name
        response.close()


def test_pagina_di_prova_risorse_esterne_solo_da_google_fonts():
    html = (DEV / "carte.html").read_text(encoding="utf-8")
    for url in re.findall(r'(?:href|src)="(https?://[^"]+)"', html):
        parts = urlsplit(url)
        assert f"{parts.scheme}://{parts.netloc}" in ALLOWED_ORIGINS, url


def test_pagina_di_prova_mostra_40_carte_e_una_mano_da_5():
    code = (DEV / "carte.js").read_text(encoding="utf-8")
    assert "for (const suit of SUITS)" in code and "rank <= 10" in code
    hand = re.search(r"const hand = \[(.*?)\];", code, flags=re.DOTALL).group(1)
    assert len(re.findall(r"\{ suit: '\w+', rank: \d+ \}", hand)) == 5


# --- Componenti --------------------------------------------------------------


def test_ogni_carta_ha_data_suit_e_data_rank():
    code = CARD_JS.read_text(encoding="utf-8")
    assert "const data = { suit: card.suit, rank: card.rank };" in code
    assert code.count("data,") == 2   # carta scoperta e carta pulsante


def test_immagini_usate_dalle_carte_esistono():
    # P35: una faccia per ognuna delle 40 carte, con il nome del codice del motore
    # ("coppe-10"), e il dorso delle altre pagine
    images = STATIC / "img" / "cards"
    expected = {f"{suit.value}-{rank}.webp" for suit in Suit for rank in range(1, 11)}  # rank del contratto
    assert {path.name for path in images.glob("*.webp")} == expected
    assert (STATIC / "img" / "cards-bg" / "dorso.webp").is_file()
    code = CARD_JS.read_text(encoding="utf-8")
    assert "new URL('../../img/cards/', import.meta.url)" in code
    assert "${FACE_BASE}${card.suit}-${card.rank}.webp" in code


def test_carte_vere_leggere_e_con_licenza():
    images = STATIC / "img" / "cards"
    total = sum(path.stat().st_size for path in images.glob("*.webp"))
    assert total < 1024 * 1024, f"le 40 carte pesano {total} byte: il limite è 1 MB (P35)"
    for path in images.glob("*.webp"):
        # File WebP veri (intestazione RIFF...WEBP), non solo con l'estensione giusta
        head = path.read_bytes()[:12]
        assert head[:4] == b"RIFF" and head[8:12] == b"WEBP", path.name
    licence = (images / "LICENZA.md").read_text(encoding="utf-8")
    assert "Matsoftware" in licence and "CC BY-SA 3.0" in licence


def test_semi_e_nomi_uguali_al_motore():
    data = _node(
        f"import {{ SUITS, RANK_NAMES, cardName }} from '{_card_js_url()}';"
        "console.log(JSON.stringify({ suits: SUITS, names: RANK_NAMES,"
        " king: cardName({ suit: 'coppe', rank: 10 }), seven: cardName({ suit: 'denari', rank: 7 }) }));"
    )
    assert sorted(data["suits"]) == sorted(suit.value for suit in Suit)
    assert {int(k): v for k, v in data["names"].items()} == {rank.value: name for rank, name in RANK_NAMES.items()}
    assert data["king"] == "Re di coppe"
    assert data["seven"] == "7 di denari"


@pytest.mark.parametrize(
    "card",
    [
        {"suit": "Coppe", "rank": 10},
        {"suit": "coppe", "rank": 0},
        {"suit": "coppe", "rank": 11},
        {"suit": "coppe", "rank": "10"},
        {"suit": "coppe", "rank": 1.5},
        {"suit": "cuori", "rank": 1},
        {"suit": "coppe"},
        {},
        None,
    ],
)
def test_carta_non_valida_rifiutata(card):
    result = _node(
        f"import {{ checkCard }} from '{_card_js_url()}';"
        f"let out; try {{ checkCard({json.dumps(card)}); out = 'accettata'; }}"
        " catch (error) { out = error.message; }"
        "console.log(JSON.stringify(out));"
    )
    assert result == "Carta non valida."


def test_tutte_le_40_carte_valide():
    result = _node(
        f"import {{ checkCard, SUITS }} from '{_card_js_url()}';"
        "let n = 0; for (const suit of SUITS) for (let rank = 1; rank <= 10; rank += 1) { checkCard({ suit, rank }); n += 1; }"
        "console.log(JSON.stringify(n));"
    )
    assert result == 40
