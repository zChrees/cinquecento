"""P20, P35: le carte (nomi, semi, immagini).

Controlla il "Fatto quando" di SCALETTA.md (P20): ogni carta ha data-suit e data-rank
stabili; i semi e i nomi delle carte sono quelli del motore (app/game/engine/cards.py)
e del contratto ({"suit", "rank"}, rank da 1 a 10); e (P35) le 40 immagini delle carte
vere, leggere e con la licenza.
Dal lotto 9b-2 della migrazione le carte sono quelle del tavolo React:
frontend/src/game/cards.ts (nomi, semi, indirizzi) e CardView.tsx (il disegno). Le
costanti si leggono come testo (scelta 3 del passo 9), senza Node. Fino al 9b-2 qui
c'erano anche la pagina di prova delle carte (app/static/dev/carte.html, tolta con il
JavaScript vecchio) e i controlli di checkCard di Card.js eseguito con Node (una carta
fuori elenco rifiutata, le 40 accettate): leggendo il testo non si possono fare.
"""

import re
from pathlib import Path

from app.game.engine.cards import RANK_NAMES, Suit

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "app" / "static"
GAME_SRC = ROOT / "frontend" / "src" / "game"
CARDS_TS = (GAME_SRC / "cards.ts").read_text(encoding="utf-8")


def test_ogni_carta_ha_data_suit_e_data_rank():
    code = (GAME_SRC / "CardView.tsx").read_text(encoding="utf-8")
    # carta scoperta e carta pulsante
    assert code.count("data-suit={props.card.suit}") == 2
    assert code.count("data-rank={props.card.rank}") == 2


def test_immagini_usate_dalle_carte_esistono():
    # P35: una faccia per ognuna delle 40 carte, con il nome del codice del motore
    # ("coppe-10"), e il dorso
    images = STATIC / "img" / "cards"
    expected = {f"{suit.value}-{rank}.webp" for suit in Suit for rank in range(1, 11)}  # rank del contratto
    assert {path.name for path in images.glob("*.webp")} == expected
    assert (STATIC / "img" / "cards-bg" / "dorso.webp").is_file()
    assert "const FACE_BASE = '/static/img/cards/';" in CARDS_TS
    assert "return `${FACE_BASE}${card.suit}-${card.rank}.webp`;" in CARDS_TS
    assert "export const BACK_URL = '/static/img/cards-bg/dorso.webp';" in CARDS_TS


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
    suits = re.search(r"export const SUITS: Suit\[\] = \[(.*?)\];", CARDS_TS).group(1)
    assert sorted(re.findall(r"'([a-z]+)'", suits)) == sorted(suit.value for suit in Suit)
    names = re.search(r"export const RANK_NAMES: Record<Rank, string> = \{(.*?)\};", CARDS_TS, flags=re.DOTALL).group(1)
    found = {int(rank): name for rank, name in re.findall(r"(\d+): '([^']+)'", names)}
    assert found == {rank.value: name for rank, name in RANK_NAMES.items()}
    # Il nome di una carta: "Re di coppe", "7 di denari"
    assert "return `${RANK_NAMES[card.rank]} di ${card.suit}`;" in CARDS_TS


def test_carta_non_valida_con_il_messaggio_del_motore():
    # Il messaggio è quello del motore e del contratto (P10, P20)
    assert "throw new Error('Carta non valida.');" in CARDS_TS
