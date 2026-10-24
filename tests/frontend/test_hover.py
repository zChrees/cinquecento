"""P129: sul telefono niente ":hover".

Il browser del telefono lascia ":hover" sull'elemento appena toccato, finché non
si tocca un altro punto dello schermo: le X restavano con il cerchio grigio e gli
altri pulsanti con il loro colore. Ogni regola con ":hover" deve stare dentro
@media (hover: hover), che vale solo dove c'è un puntatore vero (come le carte,
P97); con la tastiera resta ":focus-visible", scritto fuori.
Legge i CSS e basta: non serve né MySQL né il browser.
"""

import re
from pathlib import Path

CSS = Path(__file__).resolve().parents[2] / "app" / "static" / "css"

COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)


def rules(text):
    """Coppie (selettore, @media che lo contengono), leggendo le graffe del file."""
    text = COMMENT.sub("", text)
    found, stack, start = [], [], 0
    for mark in re.finditer(r"[{};]", text):
        if mark.group() == "{":
            selector = text[start:mark.start()].strip()
            found.append((selector, tuple(stack)))
            stack.append(selector)
        elif mark.group() == "}":
            stack.pop()
        start = mark.end()
    return found


def hover_rules():
    for path in sorted(CSS.rglob("*.css")):
        for selector, parents in rules(path.read_text(encoding="utf-8")):
            if ":hover" in selector:
                yield path.relative_to(CSS).as_posix(), selector, parents


def test_ogni_hover_solo_con_il_mouse():
    fuori = [
        f"{path}: {' '.join(selector.split())}"
        for path, selector, parents in hover_rules()
        if not any(re.fullmatch(r"@media\s*\(\s*hover\s*:\s*hover\s*\)", p) for p in parents)
    ]
    assert not fuori, "regole :hover fuori da @media (hover: hover):\n" + "\n".join(fuori)


def test_il_controllo_trova_le_regole():
    """Il controllo di sopra vale qualcosa solo se trova davvero le regole :hover."""
    found = {(path, " ".join(selector.split())) for path, selector, _ in hover_rules()}
    assert ("components/button.css", ".icon-btn:hover") in found
    assert ("components/card.css", "button.card:not(:disabled):hover") in found
    assert len(found) >= 20


def test_con_la_tastiera_resta_il_fuoco():
    """Le regole che valevano per :hover e :focus-visible insieme tengono il fuoco fuori da @media."""
    outside = {
        " ".join(selector.split())
        for path in CSS.rglob("*.css")
        for selector, parents in rules(path.read_text(encoding="utf-8"))
        if not parents
    }
    for selector in (
        ".navbar__friends:focus-visible, .navbar__account:focus-visible",
        ".navbar__account:focus-visible .avatar",
        ".mode-tile:focus-visible",
        ".resume__link:focus-visible .resume__btn",
    ):
        assert selector in outside
