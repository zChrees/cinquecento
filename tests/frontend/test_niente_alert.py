"""P33: niente alert, confirm e prompt del browser nelle pagine.

Le finestre del browser bloccano la pagina e non seguono lo stile del sito: si
usano le finestre nella pagina (components/Modal.tsx, InviteDialog.tsx). Controlla
tutto il codice del frontend React (frontend/src/) e i template, senza i commenti;
confirmModal() e simili non contano, perché il nome è diverso.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPA_SRC = ROOT / "frontend" / "src"
TEMPLATES = ROOT / "app" / "templates"

BROWSER_DIALOG = re.compile(r"(?<![\w.$])(?:window\.|globalThis\.|self\.)?(alert|confirm|prompt)\s*\(")


def _strip_js_comments(code):
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
    return re.sub(r"^\s*//.*$", "", code, flags=re.MULTILINE)


def _found(text):
    return [m.group(0) for m in BROWSER_DIALOG.finditer(text)]


def test_l_espressione_trova_le_finestre_del_browser():
    assert _found("if (confirm('Sicuro?')) go();") == ["confirm("]
    assert _found("window.alert('x'); prompt ('nome')") == ["window.alert(", "prompt ("]
    assert _found("confirmModal({ title }); openAlert(); this.prompt(); x.confirm()") == []


def test_niente_finestre_del_browser_nel_codice():
    files = [p for p in SPA_SRC.rglob("*") if p.suffix in (".ts", ".tsx")]
    assert len(files) > 20
    found = {p.relative_to(SPA_SRC).as_posix(): _found(_strip_js_comments(p.read_text(encoding="utf-8"))) for p in files}
    assert not {name: calls for name, calls in found.items() if calls}


def test_niente_finestre_del_browser_nei_template():
    found = {}
    for path in TEMPLATES.rglob("*.html"):
        text = re.sub(r"\{#.*?#\}", "", path.read_text(encoding="utf-8"), flags=re.DOTALL)
        if _found(text):
            found[path.name] = _found(text)
    assert not found
