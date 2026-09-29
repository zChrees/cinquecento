"""D40: il font delle icone sta nel progetto e contiene solo le icone usate.

app/static/fonts/material-symbols-rounded.woff2 ha solo le icone elencate in
app/static/fonts/icone.txt (una per riga, in ordine alfabetico), scaricate da Google
Fonts con il comando di docs/prototipo/LEGGIMI.md ("Icone"). Controlla: ogni icona
usata nei template e nel JS è nell'elenco (un'icona nuova va aggiunta all'elenco e il
font va riscaricato); base.html precarica il font e non chiede più le icone a Google;
il font arriva dal server; nel browser le icone della home sono disegnate come icone
(larghe quanto un quadratino) e non come la parola del loro nome.
Se né Chrome né Edge sono installati il controllo nel browser si salta.
"""

import re
from pathlib import Path

import pytest

from app import create_app
from tests.browser import TEST_COOKIE, Browser, FakeUser, find_browser, running_server

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "app" / "static"
TEMPLATES = ROOT / "app" / "templates"
FONTS = STATIC / "fonts"
ICON_LIST = FONTS / "icone.txt"
FONT_URL = "/static/fonts/material-symbols-rounded.woff2"

# Chiamate con il nome calcolato: i nomi possibili stanno in queste righe di codice
# (se ne aggiungi una, aggiungi qui da dove prendere i nomi)
DYNAMIC_CALLS = {
    ("components/ModeModal.js", "look[0]"),   # stato del pulsante "Invita"
    ("components/ModeModal.js", "name"),      # righe "In breve" della Partita Veloce
    ("pages/home.js", "MESSAGE_ICONS[kind]"),  # messaggi brevi in basso
    ("components/FriendsPanel.js", "name"),   # dentro iconButton(): i nomi arrivano da iconButton('…')
}


def _listed():
    return ICON_LIST.read_text(encoding="utf-8").split()


def _used():
    """Le icone usate: {nome: [dove]}."""
    found = {}

    def add(name, where):
        found.setdefault(name, []).append(where)

    for path in TEMPLATES.rglob("*.html"):
        text = re.sub(r"\{#.*?#\}", "", path.read_text(encoding="utf-8"), flags=re.DOTALL)
        for content in re.findall(r'<span class="icon[^"]*"[^>]*>(.*?)</span>', text, flags=re.DOTALL):
            names = [content.strip()] if re.fullmatch(r"\s*[a-z_]+\s*", content) else re.findall(r':\s*"([a-z_]+)"', content)
            assert names, f"{path.name}: icona con un nome che il test non sa leggere: {content!r}"
            for name in names:
                add(name, path.name)

    for path in (STATIC / "js").rglob("*.js"):
        code = path.read_text(encoding="utf-8")
        where = path.relative_to(STATIC / "js").as_posix()
        for name in re.findall(r"\bicon(?:Button)?\(\s*'([a-z_]+)'", code):
            add(name, where)
        if where == "components/ModeModal.js":
            # righe "In breve" ([icona, testo]) e aspetto del pulsante "Invita" ([icona, testo, etichetta])
            for name in re.findall(r"\[\s*'([a-z_]+)',\s*[`']", code):
                add(name, where)
        if where == "pages/home.js":
            block = re.search(r"MESSAGE_ICONS = \{(.*?)\}", code).group(1)
            for name in re.findall(r":\s*'([a-z_]+)'", block):
                add(name, where)
    return found


def _dynamic_calls():
    calls = set()
    for path in (STATIC / "js").rglob("*.js"):
        code = path.read_text(encoding="utf-8")
        where = path.relative_to(STATIC / "js").as_posix()
        for args in re.findall(r"(?<!function )\bicon(?:Button)?\(\s*([^'\s][^,)]*)", code):
            calls.add((where, args.strip()))
    return calls


def test_elenco_in_ordine_e_senza_doppioni():
    listed = _listed()
    assert listed == sorted(set(listed))
    assert all(re.fullmatch(r"[a-z_]+", name) for name in listed)


def test_ogni_icona_usata_e_nel_font():
    used = _used()
    assert len(used) > 20, "il test non trova più le icone: controlla le espressioni regolari"
    missing = {name: where for name, where in used.items() if name not in _listed()}
    assert not missing, f"icone non nel font: aggiungile a icone.txt e riscarica il font (LEGGIMI.md): {missing}"


def test_nomi_calcolati_conosciuti():
    # Una chiamata nuova con il nome in una variabile sfuggirebbe a _used()
    assert _dynamic_calls() == DYNAMIC_CALLS


def test_nessuna_icona_in_piu():
    unused = set(_listed()) - set(_used())
    assert not unused, f"icone nel font ma non usate: toglile da icone.txt e riscarica il font: {sorted(unused)}"


def test_base_precarica_il_font_senza_google():
    app = create_app("testing")
    client = app.test_client()
    html = client.get("/").get_data(as_text=True)
    assert "Material+Symbols" not in html
    assert re.search(rf'<link rel="preload" href="{re.escape(FONT_URL)}" as="font" type="font/woff2" crossorigin>', html)
    response = client.get(FONT_URL)
    assert response.status_code == 200
    assert response.get_data()[:4] == b"wOF2"
    assert len(response.get_data()) < 50_000
    response.close()
    css = (STATIC / "css" / "base" / "typography.css").read_text(encoding="utf-8")
    assert '@font-face' in css and 'url("../../fonts/material-symbols-rounded.woff2")' in css


@pytest.fixture
def browser(tmp_path):
    app = create_app("testing")
    with running_server(app, FakeUser("Mario", 12)) as url:
        b = Browser(find_browser(), tmp_path / "chrome")
        b.send("Network.setCookie", name=TEST_COOKIE[0], value=TEST_COOKIE[1], url=url)
        yield b, url
        b.close()


def test_icone_disegnate_nel_browser(browser):
    b, url = browser
    b.open(f"{url}/", 390, 844, "document.querySelector('[data-friends-button] .icon') !== null")
    assert b.js("document.fonts.check('24px \"Material Symbols Rounded\"')") is True
    icons = b.js("""[...document.querySelectorAll('.icon')].filter((e) => e.offsetWidth > 0)
        .map((e) => ({name: e.textContent, width: e.offsetWidth,
                      size: parseFloat(getComputedStyle(e).fontSize)}))""")
    assert len(icons) >= 5
    # Con il glifo l'icona è un quadratino; senza, si vedrebbe la parola ("person", "groups"…)
    wide = [i for i in icons if i["width"] > i["size"] * 1.3]
    assert not wide, wide
