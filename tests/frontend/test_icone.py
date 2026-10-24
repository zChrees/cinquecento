"""D40: il font delle icone sta nel progetto e contiene solo le icone usate.

app/static/fonts/material-symbols-rounded.woff2 ha solo le icone elencate in
app/static/fonts/icone.txt (una per riga, in ordine alfabetico), scaricate da Google
Fonts con il comando di docs/prototipo/LEGGIMI.md ("Icone"). Controlla: ogni icona
usata nel frontend React (frontend/src/ e frontend/index.html) e nei template delle
pagine di errore è nell'elenco (un'icona nuova va aggiunta all'elenco e il font va
riscaricato), e nell'elenco non ce n'è nessuna in più; la pagina della SPA e base.html
precaricano il font e non chiedono le icone a Google; il font arriva dal server; nel
browser le icone della home sono disegnate come icone (larghe quanto un quadratino) e
non come la parola del loro nome.
Se né Chrome né Edge sono installati, o manca il build della SPA, il controllo nel
browser si salta.
"""

import re
from pathlib import Path

import pytest

from app import create_app
from tests.browser import TEST_COOKIE, Browser, FakeUser, find_browser, running_server
from tests.spa import needs_spa

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "app" / "static"
TEMPLATES = ROOT / "app" / "templates"
SPA_SRC = ROOT / "frontend" / "src"
SPA_INDEX = ROOT / "frontend" / "index.html"
FONTS = STATIC / "fonts"
ICON_LIST = FONTS / "icone.txt"
FONT_URL = "/static/fonts/material-symbols-rounded.woff2"

# Icone con il nome calcolato: <span className="icon">{espressione}</span>. I nomi possibili
# li trova _used() nelle forme icon: 'nome', icon="nome" e nell'elenco ICONS di FlashList.tsx
# (se ne aggiungi una con un'altra forma, aggiungi anche da dove prendere i nomi)
DYNAMIC_CALLS = {
    ("pages/HomePage.tsx", "props.icon"),            # le quattro carte-pulsante (icon="person" / "groups")
    ("components/FlashList.tsx", "ICONS[flash.kind]"),  # messaggi brevi in basso
    ("components/ModeModal.tsx", "look.icon"),        # stato del pulsante "Invita"
    ("components/ModeModal.tsx", "facts[i].icon"),    # righe "In breve"
}
# SPAN: un'icona scritta nella pagina, con il nome per esteso (JSX o HTML)
SPAN = r'<span class(?:Name)?="icon[^"]*"[^>]*>([a-z_]+)</span>'


def _listed():
    return ICON_LIST.read_text(encoding="utf-8").split()


def _sources():
    return sorted(path for path in SPA_SRC.rglob("*") if path.suffix in (".ts", ".tsx"))


def _used():
    """Le icone usate: {nome: [dove]}."""
    found = {}

    def add(name, where):
        found.setdefault(name, []).append(where)

    for path in TEMPLATES.rglob("*.html"):
        text = re.sub(r"\{#.*?#\}", "", path.read_text(encoding="utf-8"), flags=re.DOTALL)
        for name in re.findall(SPAN, text):
            add(name, path.name)
    for name in re.findall(SPAN, SPA_INDEX.read_text(encoding="utf-8")):
        add(name, "index.html")

    for path in _sources():
        code = path.read_text(encoding="utf-8")
        where = path.relative_to(SPA_SRC).as_posix()
        for name in re.findall(SPAN, code):
            add(name, where)
        # icon: 'nome' (elenchi di ModeModal.tsx) e icon="nome" (le carte-pulsante della home)
        for name in re.findall(r"""\bicon(?::\s*'|=")([a-z_]+)['"]""", code):
            add(name, where)
        if where == "components/FlashList.tsx":
            block = re.search(r"const ICONS[^=]*= \{(.*?)\}", code, flags=re.DOTALL).group(1)
            for name in re.findall(r":\s*'([a-z_]+)'", block):
                add(name, where)
    return found


def _dynamic_calls():
    calls = set()
    for path in _sources():
        code = path.read_text(encoding="utf-8")
        where = path.relative_to(SPA_SRC).as_posix()
        for expression in re.findall(r'<span className="icon[^"]*"[^>]*>\{([^}]+)\}</span>', code):
            calls.add((where, expression.strip()))
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
    # Un'icona nuova con il nome in una variabile sfuggirebbe a _used()
    assert _dynamic_calls() == DYNAMIC_CALLS


def test_nessuna_icona_in_piu():
    unused = set(_listed()) - set(_used())
    assert not unused, f"icone nel font ma non usate: toglile da icone.txt e riscarica il font: {sorted(unused)}"


def test_le_pagine_precaricano_il_font_senza_google():
    app = create_app("testing")
    client = app.test_client()
    # base.html, pagine di errore: dal lotto 9d un indirizzo a caso dà la SPA, la 404
    # Jinja resta per i file statici che mancano
    response = client.get("/static/non-esiste.css")
    error_page = response.get_data(as_text=True)
    response.close()
    preload = rf'<link rel="preload" href="{re.escape(FONT_URL)}" as="font" type="font/woff2" crossorigin>'
    for page, html in (("frontend/index.html", SPA_INDEX.read_text(encoding="utf-8")), ("base.html", error_page)):
        assert "Material+Symbols" not in html, page
        assert re.search(preload, html), page
    response = client.get(FONT_URL)
    assert response.status_code == 200
    assert response.get_data()[:4] == b"wOF2"
    assert len(response.get_data()) < 50_000
    response.close()
    css = (STATIC / "css" / "base" / "typography.css").read_text(encoding="utf-8")
    assert '@font-face' in css and 'url("../../fonts/material-symbols-rounded.woff2")' in css


@pytest.fixture
def browser(tmp_path):
    needs_spa()
    app = create_app("testing")
    with running_server(app, FakeUser("Mario", 12)) as url:
        b = Browser(find_browser(), tmp_path / "chrome")
        b.send("Network.setCookie", name=TEST_COOKIE[0], value=TEST_COOKIE[1], url=url)
        yield b, url
        b.close()


def test_icone_disegnate_nel_browser(browser):
    b, url = browser
    # Si aspetta anche il collegamento al tempo reale: chiudere a collegamento a metà
    # blocca a volte il server del file dopo (P58, P62)
    b.open(f"{url}/", 390, 844, "document.querySelector('[data-friends-button] .icon') !== null"
           " && document.querySelector('[data-friends-panel]')?.dataset.connection === 'connected'", timeout=60)
    assert b.js("document.fonts.check('24px \"Material Symbols Rounded\"')") is True
    icons = b.js("""[...document.querySelectorAll('.icon')].filter((e) => e.offsetWidth > 0)
        .map((e) => ({name: e.textContent, width: e.offsetWidth,
                      size: parseFloat(getComputedStyle(e).fontSize)}))""")
    assert len(icons) >= 5
    # Con il glifo l'icona è un quadratino; senza, si vedrebbe la parola ("person", "groups"…)
    wide = [i for i in icons if i["width"] > i["size"] * 1.3]
    assert not wide, wide
