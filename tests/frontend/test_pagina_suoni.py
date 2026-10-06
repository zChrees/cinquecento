"""P115: pagina per ascoltare e confrontare i suoni del menu (solo sviluppo; è quella di
P113 per i suoni del tavolo, con un altro elenco).

Controlla che l'elenco (app/static/dev/suoni.json) e i file corrispondano: ogni
avviso (richiesta di amicizia, messaggio, invito) ha il suono di oggi (provvisorio) e
almeno tre alternative, ogni file esiste, i suoni di oggi sono quelli dei tre avvisi
in js/core/sounds.js, ogni candidato è usato e ha la sua riga in suoni/LICENZA.md. Nel browser: la pagina disegna i momenti, "Ascolta"
suona una scelta alla volta, "Mi piace" finisce nel riepilogo, e tutti i file si
decodificano davvero.
"""

import json
import re
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from app import create_app
from tests.browser import Browser, find_browser, running_server

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "app" / "static"
DEV = STATIC / "dev"
CANDIDATES = DEV / "suoni"
SOUNDS = STATIC / "sounds"
ALLOWED_ORIGINS = {"https://fonts.googleapis.com", "https://fonts.gstatic.com"}


def _moments():
    return json.loads((DEV / "suoni.json").read_text(encoding="utf-8"))["moments"]


def _files():
    return [file for moment in _moments() for option in moment["options"] for file in option["files"]]


# --- Elenco e file -----------------------------------------------------------


def test_ogni_momento_ha_oggi_e_almeno_tre_alternative():
    moments = _moments()
    ids = [moment["id"] for moment in moments]
    assert len(ids) == len(set(ids))
    for moment in moments:
        options = moment["options"]
        assert options[0]["id"] == "oggi", moment["id"]
        assert len(options) >= 4, moment["id"]
        option_ids = [option["id"] for option in options]
        assert len(option_ids) == len(set(option_ids)), moment["id"]
        for option in options:
            assert option["source"].strip(), (moment["id"], option["id"])
            if len(option["files"]) > 1:
                assert option["gap_ms"] > 0, (moment["id"], option["id"])
        assert moment["title"].strip() and moment["when"].strip()


def test_i_file_esistono_e_stanno_solo_nelle_due_cartelle():
    for file in _files():
        assert file.startswith(("../sounds/", "suoni/")) and file.endswith(".mp3"), file
        assert (DEV / file).resolve().is_file(), file


def test_oggi_sono_proprio_i_suoni_del_menu():
    sounds_js = (STATIC / "js" / "core" / "sounds.js").read_text(encoding="utf-8")
    for moment in _moments():
        today = [Path(file).stem for file in moment["options"][0]["files"]]
        files = re.search(rf"^\s+{moment['id']}: \[([^\]]*)\]", sounds_js, re.MULTILINE).group(1)
        assert today == re.findall(r"'([\w-]+)'", files), moment["id"]
        assert all((SOUNDS / f"{name}.mp3").is_file() for name in today)


def test_ogni_candidato_e_usato_e_ha_la_licenza():
    used = {Path(file).name for file in _files() if file.startswith("suoni/")}
    present = {path.name for path in CANDIDATES.glob("*.mp3")}
    assert used == present
    licence = (CANDIDATES / "LICENZA.md").read_text(encoding="utf-8")
    assert "CC0" in licence
    listed = set(re.findall(r"`([\w-]+\.mp3)`", licence))
    # Le righe con "…" valgono per una serie (card-slide-5 … card-slide-8)
    for prefix, first, last in re.findall(r"`([\w-]+?)(\d+)\.mp3` … `[\w-]+?(\d+)\.mp3`", licence):
        listed |= {f"{prefix}{n}.mp3" for n in range(int(first), int(last) + 1)}
    assert present <= listed, sorted(present - listed)


def test_pagina_servita_e_risorse_esterne_solo_da_google_fonts():
    client = create_app("testing").test_client()
    for name in ("suoni.html", "suoni.js", "suoni.css", "suoni.json"):
        response = client.get(f"/static/dev/{name}")
        assert response.status_code == 200, name
        response.close()
    html = (DEV / "suoni.html").read_text(encoding="utf-8")
    assert '<script type="module" src="suoni.js"></script>' in html
    for url in re.findall(r'(?:href|src)="(https?://[^"]+)"', html):
        parts = urlsplit(url)
        assert f"{parts.scheme}://{parts.netloc}" in ALLOWED_ORIGINS, url


# --- Nel browser ---------------------------------------------------------------


@pytest.fixture(scope="module")
def server():
    with running_server(create_app("testing")) as url:
        yield url


@pytest.fixture
def browser(server, tmp_path):
    b = Browser(find_browser(), tmp_path / "chrome")
    yield b
    b.close()


def test_pagina_ascolto_scelta_e_riepilogo(browser, server):
    browser.open(f"{server}/static/dev/suoni.html", 390, 844, ready="'ready' in document.body.dataset")
    moments = _moments()
    assert browser.js("document.querySelectorAll('[data-moment]').length") == len(moments)
    # Un pulsante "Ascolta" con un nome per ogni scelta; "Silenzio" spento dove oggi non c'è suono
    labels = browser.js("[...document.querySelectorAll('[data-play]')].map((b) => b.getAttribute('aria-label'))")
    assert len(labels) == sum(len(m["options"]) for m in moments) and all(labels)

    # Un suono alla volta: "Ascolta" su un'altra scelta ferma quella di prima
    browser.click('[data-moment="message"] [data-option="A"] [data-play]')
    browser.wait_js("!!document.querySelector('[data-moment=\"message\"] [data-option=\"A\"][data-playing]')", "A suona")
    browser.click('[data-moment="invite"] [data-option="B"] [data-play]')
    browser.wait_js("!!document.querySelector('[data-moment=\"invite\"] [data-option=\"B\"][data-playing]')", "B suona")
    assert browser.js("document.querySelectorAll('[data-playing]').length") == 1

    # "Mi piace" segna la scelta e finisce nel riepilogo
    browser.click('[data-moment="invite"] [data-option="C"] [data-choose]')
    assert browser.js("!!document.querySelector('[data-moment=\"invite\"] [data-option=\"C\"][data-chosen]')")
    text = browser.js("document.querySelector('[data-summary]').textContent")
    assert text.startswith("Suoni del menu scelti (P115):")
    assert "Invito a una partita [invite]: Alternativa C (Casino Audio: chips-stack-1)" in text
    assert "Messaggio in chat [message]: non ancora scelto" in text


def test_tutti_i_file_si_decodificano(browser, server):
    browser.open(f"{server}/static/dev/suoni.html", 390, 844, ready="'ready' in document.body.dataset")
    files = sorted(set(_files()))
    failed = browser.js(f"""(async () => {{
      const ctx = new OfflineAudioContext(1, 44100, 44100);
      const failed = [];
      for (const file of {json.dumps(files)}) {{
        try {{
          const data = await (await fetch(file)).arrayBuffer();
          const buffer = await ctx.decodeAudioData(data);
          if (!(buffer.duration > 0)) failed.push(file);
        }} catch (error) {{
          failed.push(file);
        }}
      }}
      return failed;
    }})()""")
    assert failed == []
