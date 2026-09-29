"""P33: niente alert, confirm e prompt del browser nelle pagine.

Le finestre del browser bloccano la pagina e non seguono lo stile del sito: si
usano le finestre nella pagina (components/Modal.js, InviteDialog.js). Controlla
tutto il JS dell'applicazione (non le librerie in js/vendor/) e i template, senza
i commenti; confirmModal() e simili non contano, perché il nome è diverso.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
JS = ROOT / "app" / "static" / "js"
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


def test_niente_finestre_del_browser_nel_js():
    files = [p for p in JS.rglob("*.js") if "vendor" not in p.relative_to(JS).parts]
    assert len(files) > 20
    found = {p.relative_to(JS).as_posix(): _found(_strip_js_comments(p.read_text(encoding="utf-8"))) for p in files}
    assert not {name: calls for name, calls in found.items() if calls}


def test_niente_finestre_del_browser_nei_template():
    found = {}
    for path in TEMPLATES.rglob("*.html"):
        text = re.sub(r"\{#.*?#\}", "", path.read_text(encoding="utf-8"), flags=re.DOTALL)
        if _found(text):
            found[path.name] = _found(text)
    assert not found
