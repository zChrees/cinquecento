"""P43: immagini degli avatar.

Controlla il "Fatto quando" di SCALETTA.md (P43): ogni avatar di
app/services/avatars.py ha la sua immagine (app/static/img/avatars/<codice>.svg);
chi non ne ha scelto uno vede l'iniziale; il peso totale è sotto 300 KB.
Controlla anche che js/components/Avatar.js conosca gli stessi codici (con Node,
se c'è), che navbar, pannello statistiche e impostazioni mostrino l'immagine
(macro templates/partials/avatar.html) e che al tavolo di prova (/game/prova?demo=2v2,
in Chrome o Edge senza finestra, tests/browser.py) le immagini si carichino e un
codice fuori elenco mostri l'iniziale. Non serve MySQL.
"""

import json
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from flask import render_template

from app import create_app
from app.services.avatars import AVATARS
from tests.browser import TEST_COOKIE, Browser, find_browser, running_server
from tests.browser import FakeUser as BrowserUser

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "app" / "static"
AVATAR_DIR = STATIC / "img" / "avatars"
AVATAR_JS = STATIC / "js" / "components" / "Avatar.js"
SVG_NS = "{http://www.w3.org/2000/svg}"


class FakeUser:
    """Utente con il login per i template (come in test_navbar.py), con un avatar."""

    is_authenticated = True

    def __init__(self, username, avatar=None):
        self.username = username
        self.avatar = avatar

    def get_id(self):
        return "7"


@pytest.fixture
def app():
    return create_app("testing")


def _render(app, template, avatar, **context):
    with app.test_request_context("/"):
        return render_template(template, current_user=FakeUser("mario", avatar), **context)


# --- File delle immagini -----------------------------------------------------


def test_una_immagine_per_ogni_codice_e_nessuna_in_piu():
    files = {p.stem for p in AVATAR_DIR.glob("*.svg")}
    assert files == set(AVATARS)
    assert {p.name for p in AVATAR_DIR.iterdir()} == {f"{code}.svg" for code in AVATARS}


def test_peso_totale_sotto_300_kb():
    total = sum(p.stat().st_size for p in AVATAR_DIR.glob("*.svg"))
    assert total < 300 * 1024, total


@pytest.mark.parametrize("code", sorted(AVATARS))
def test_svg_valido_quadrato_e_senza_risorse_esterne(code):
    text = (AVATAR_DIR / f"{code}.svg").read_text(encoding="utf-8")
    root = ET.fromstring(text)   # un SVG non valido (per esempio "--" in un commento) non si legge
    assert root.tag == f"{SVG_NS}svg"
    assert root.get("viewBox") == "0 0 64 64"
    # Tutto disegnato dentro il file: niente immagini o font da fuori (CSP, P32)
    assert "href=" not in text and "http://" not in text.replace("http://www.w3.org/2000/svg", "")
    assert "<script" not in text and "<image" not in text and "<text" not in text
    for comment in re.findall(r"<!--(.*?)-->", text, flags=re.DOTALL):
        assert "--" not in comment


def test_immagini_servite(app):
    client = app.test_client()
    for code in AVATARS:
        response = client.get(f"/static/img/avatars/{code}.svg")
        assert response.status_code == 200, code
        assert response.mimetype == "image/svg+xml"
        response.close()


# --- Avatar.js ----------------------------------------------------------------


def _node(script):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node non installato: controllo di Avatar.js saltato")
    result = subprocess.run(
        [node, "--input-type=module", "-e", script],
        capture_output=True, text=True, timeout=30, check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_avatar_js_conosce_gli_stessi_codici_del_server():
    url = AVATAR_JS.resolve().as_uri()
    data = _node(
        f"const m = await import({json.dumps(url)});"
        "console.log(JSON.stringify({"
        "codes: m.AVATAR_CODES,"
        "known: m.avatarUrl('re_coppe'),"
        "unknown: [m.avatarUrl('cavallo_spade'), m.avatarUrl(null), m.avatarUrl(''), m.avatarUrl('../x')],"
        "}))"
    )
    assert data["codes"] == list(AVATARS)
    assert data["known"].endswith("/app/static/img/avatars/re_coppe.svg")
    assert data["unknown"] == [None, None, None, None]


def test_componenti_usano_avatar_js():
    # Un solo posto decide immagine o iniziale: nessun componente la ricalcola da sé
    for name in ("Table.js", "FriendsPanel.js", "ModeModal.js", "QueueOverlay.js"):
        code = (STATIC / "js" / "components" / name).read_text(encoding="utf-8")
        assert "import { Avatar } from './Avatar.js';" in code, name
        assert "charAt(0).toUpperCase()" not in code and "slice(0, 1).toUpperCase()" not in code, name


# --- Template: navbar, pannello statistiche, impostazioni ---------------------


def test_navbar_e_statistiche_con_l_immagine(app):
    html = _render(app, "main/index.html", "re_denari")
    img = ('<span class="avatar avatar--img" data-avatar="re_denari" aria-hidden="true">'
           '<img class="avatar__img" src="/static/img/avatars/re_denari.svg" alt="" draggable="false" decoding="sync"></span>')
    assert img in re.search(r'<header class="navbar".*?</header>', html, flags=re.DOTALL).group(0)
    stats = re.search(r'<dialog class="sheet" id="stats".*?</dialog>', html, flags=re.DOTALL).group(0)
    assert img.replace('class="avatar avatar--img"', 'class="avatar avatar--big avatar--img"') in stats


def test_senza_avatar_resta_l_iniziale(app):
    html = _render(app, "main/index.html", None)
    assert '<span class="avatar" aria-hidden="true">M</span>' in html
    assert '<span class="avatar avatar--big" aria-hidden="true">M</span>' in html
    assert "img/avatars/" not in html


def test_impostazioni_con_un_immagine_per_scelta(app):
    html = _render(app, "profile/settings.html", "coppe", avatars=AVATARS)
    for code, name in AVATARS.items():
        choice = re.search(rf'<label class="avatar-choice" data-avatar="{code}">.*?</label>', html, flags=re.DOTALL)
        assert choice, code
        assert f'src="/static/img/avatars/{code}.svg"' in choice.group(0)
        assert f'<span class="avatar-choice__name">{name}</span>' in choice.group(0)
    initial = re.search(r'<label class="avatar-choice" data-avatar="">.*?</label>', html, flags=re.DOTALL).group(0)
    assert '<span class="avatar-choice__face" aria-hidden="true">M</span>' in initial


# --- Nel browser: il tavolo di prova ------------------------------------------


@pytest.fixture(scope="module")
def server():
    with running_server(create_app("testing"), BrowserUser("Mario", 12)) as url:
        yield url


@pytest.fixture
def browser(server, tmp_path):
    b = Browser(find_browser(), tmp_path / "chrome")
    b.send("Network.setCookie", name=TEST_COOKIE[0], value=TEST_COOKIE[1], url=server)
    yield b
    b.close()


SEATS = """[...document.querySelectorAll('.seat')].map((seat) => {
  const avatar = seat.querySelector('.seat__avatar > .avatar');
  const img = avatar.querySelector('img');
  const box = avatar.getBoundingClientRect();
  const inner = img ? img.getBoundingClientRect() : null;
  return {
    name: seat.querySelector('.seat__name').textContent,
    code: avatar.dataset.avatar ?? null,
    text: img ? null : avatar.textContent,
    loaded: img ? img.complete && img.naturalWidth > 0 : null,
    fits: inner ? Math.abs(inner.width - box.width) < 1 && Math.abs(inner.height - box.height) < 1 : null,
    hidden: avatar.getAttribute('aria-hidden'),
  };
})"""


@pytest.mark.parametrize("size", [(360, 640), (1440, 900)])
def test_tavolo_con_immagini_e_iniziali(browser, server, size):
    browser.open(f"{server}/game/prova?demo=2v2", *size, "document.querySelectorAll('.seat').length === 4")
    browser.wait_js("[...document.querySelectorAll('.seat img.avatar__img')].every((i) => i.complete)",
                    "immagini degli avatar caricate")
    seats = {s["name"]: s for s in browser.js(SEATS)}
    # Rosalia ha "denari"; Giulia ha "cavallo_spade", che non è del set: iniziale
    assert seats["Rosalia"]["code"] == "denari"
    assert seats["Rosalia"]["loaded"] is True and seats["Rosalia"]["fits"] is True
    assert seats["Giulia"]["code"] is None and seats["Giulia"]["text"] == "G"
    assert seats["Mario (tu)"]["text"] == "M"
    assert all(s["hidden"] == "true" for s in seats.values())
