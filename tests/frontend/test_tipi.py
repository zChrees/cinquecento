"""Passo 2 della migrazione (docs/MIGRAZIONE-FRONTEND.md): i tipi TypeScript del contratto.

I tipi in frontend/src/types/ copiano docs/CONTRATTO-SOCKET.md. Qui si controlla che
gli esempi del contratto (app/static/dev/*.json) li rispettino davvero: ogni esempio
diventa una costante TypeScript con il suo tipo, in una cartella temporanea fuori dal
progetto, e `tsc` la controlla. Un campo che manca, uno in più o un valore fuori
elenco (per esempio un seme 'cuori') fanno fallire il controllo: lo provano due test
che rompono apposta un esempio.

Poi: ogni chiave degli esempi ha il suo tipo (un esempio nuovo non resta senza
controllo); i nomi degli eventi sono quelli di app/static/js/core/events.js; i codici
di errore quelli del server (ERRORS di app/realtime/events.py); ogni evento della
pagina ha la sua risposta in ClientAnswers.

Serve Node con frontend/node_modules (npm ci): altrimenti i controlli con tsc si saltano.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from app.realtime.events import ERRORS

ROOT = Path(__file__).resolve().parents[2]
TYPES = ROOT / "frontend" / "src" / "types"
DEV = ROOT / "app" / "static" / "dev"
TSC = ROOT / "frontend" / "node_modules" / "typescript" / "bin" / "tsc"
EVENTS_JS = ROOT / "app" / "static" / "js" / "core" / "events.js"

# Ogni esempio (file, chiave; None = tutto il file) → il tipo TypeScript che deve rispettare
EXAMPLES = {
    ("vista_1v1.json", None): "GameView",
    ("vista_2v2.json", None): "GameView",
    ("statistiche_esempio.json", None): "Stats",
    ("home_esempio.json", "me"): "UserRef",
    ("home_esempio.json", "me_senza_login"): "UserRef | null",
    ("home_esempio.json", "home:status"): "ServerEvents['home:status']",
    ("home_esempio.json", "home:status con partita in corso"): "ServerEvents['home:status']",
    ("home_esempio.json", "queue:status"): "ServerEvents['queue:status']",
    ("home_esempio.json", "queue:status 2v2 con un amico"): "ServerEvents['queue:status']",
    ("home_esempio.json", "queue:status 2v2 con due amici"): "ServerEvents['queue:status']",
    ("home_esempio.json", "queue:left"): "ServerEvents['queue:left']",
    ("home_esempio.json", "game:start"): "ServerEvents['game:start']",
    ("amici_esempio.json", "GET /friends/"): "FriendsList",
    ("amici_esempio.json", "friends:presence"): "ServerEvents['friends:presence']",
    ("amici_esempio.json", "friends:changed"): "ServerEvents['friends:changed']",
    ("amici_esempio.json", "invite:received"): "ServerEvents['invite:received']",
    ("amici_esempio.json", "invite:update"): "ServerEvents['invite:update']",
    ("amici_esempio.json", "chat:history (risposta)"): "ChatHistory",
    ("amici_esempio.json", "chat:message"): "ServerEvents['chat:message']",
    ("amici_esempio.json", "errore (esempio)"): "ErrorResponse",
}
WHOLE_FILES = {"vista_1v1.json", "vista_2v2.json", "statistiche_esempio.json"}

HEADER = """\
import type { UserRef, ErrorResponse } from './types/common';
import type { GameView } from './types/view';
import type { Stats, FriendsList } from './types/api';
import type { ServerEvents, ClientEvents, ClientAnswers, ChatHistory } from './types/events';

// Ogni evento della pagina ha la sua risposta, e nessuna risposta è in più
type MissingAnswers = Exclude<keyof ClientEvents, keyof ClientAnswers>;
type ExtraAnswers = Exclude<keyof ClientAnswers, keyof ClientEvents>;
export const noMissingAnswers: [MissingAnswers] extends [never] ? true : false = true;
export const noExtraAnswers: [ExtraAnswers] extends [never] ? true : false = true;
"""


def _without_notes(value):
    """Toglie le chiavi `_nota` (commenti degli esempi, il server non le manda)."""
    if isinstance(value, dict):
        return {key: _without_notes(item) for key, item in value.items() if key != "_nota"}
    if isinstance(value, list):
        return [_without_notes(item) for item in value]
    return value


def _example(file, key):
    data = _without_notes(json.loads((DEV / file).read_text(encoding="utf-8")))
    return data if key is None else data[key]


def _source(examples):
    lines = [HEADER]
    for number, ((file, key), (type_name, value)) in enumerate(examples.items()):
        lines.append(f"// {file} {key or ''}")
        lines.append(f"export const example{number}: {type_name} = {json.dumps(value, ensure_ascii=False)};")
    return "\n".join(lines) + "\n"


def _tsc(tmp_path, examples):
    """Controlla gli esempi con tsc; restituisce (codice di uscita, messaggi)."""
    if shutil.which("node") is None:
        pytest.skip("Node non installato: controllo dei tipi saltato")
    if not TSC.is_file():
        pytest.skip("frontend/node_modules manca (npm ci in frontend/): controllo dei tipi saltato")
    shutil.copytree(TYPES, tmp_path / "types")
    (tmp_path / "check.ts").write_text(_source(examples), encoding="utf-8")
    result = subprocess.run(
        [shutil.which("node"), str(TSC), "--noEmit", "--strict", "--target", "ES2022", "--module", "ESNext",
         "--moduleResolution", "bundler", "--isolatedModules", "--skipLibCheck", "check.ts"],
        cwd=tmp_path, capture_output=True, text=True, encoding="utf-8", timeout=120, check=False,
    )
    return result.returncode, result.stdout + result.stderr


def _all_examples():
    return {where: (type_name, _example(*where)) for where, type_name in EXAMPLES.items()}


# --- Gli esempi rispettano i tipi ---------------------------------------------


def test_gli_esempi_del_contratto_rispettano_i_tipi(tmp_path):
    code, output = _tsc(tmp_path, _all_examples())
    assert code == 0, output


def test_un_seme_sbagliato_si_vede(tmp_path):
    view = _example("vista_1v1.json", None)
    view["hand"][0]["suit"] = "cuori"
    code, output = _tsc(tmp_path, {("vista_1v1.json", "rotta"): ("GameView", view)})
    assert code != 0 and "cuori" in output, output


def test_un_campo_mancante_o_in_piu_si_vede(tmp_path):
    view = _example("vista_2v2.json", None)
    del view["version"]
    stats = _example("statistiche_esempio.json", None)
    stats["streak"] = 3
    code, output = _tsc(tmp_path, {
        ("vista_2v2.json", "senza version"): ("GameView", view),
        ("statistiche_esempio.json", "con un campo in più"): ("Stats", stats),
    })
    assert code != 0, output
    assert "version" in output and "streak" in output, output


# --- Elenchi allineati ----------------------------------------------------------


def test_ogni_chiave_degli_esempi_ha_il_suo_tipo():
    for path in DEV.glob("*.json"):
        if path.name in WHOLE_FILES:
            assert (path.name, None) in EXAMPLES, path.name
            continue
        keys = set(json.loads(path.read_text(encoding="utf-8"))) - {"_nota"}
        assert keys == {key for file, key in EXAMPLES if file == path.name}, path.name


def _keys_of(interface):
    code = (TYPES / "events.ts").read_text(encoding="utf-8")
    body = re.search(rf"export interface {interface} \{{(.*?)\n\}}", code, flags=re.DOTALL)
    assert body, interface
    return set(re.findall(r"^\s*'([a-z_]+:[a-z_]+)':", body.group(1), flags=re.MULTILINE))


def test_nomi_degli_eventi_come_quelli_di_oggi():
    names = set(re.findall(r":\s*'([a-z_]+:[a-z_]+)'", EVENTS_JS.read_text(encoding="utf-8")))
    assert _keys_of("ServerEvents") | _keys_of("ClientEvents") == names
    assert _keys_of("ClientEvents") == _keys_of("ClientAnswers")


def test_codici_di_errore_come_quelli_del_server():
    code = (TYPES / "common.ts").read_text(encoding="utf-8")
    body = re.search(r"export type ErrorCode =(.*?);", code, flags=re.DOTALL).group(1)
    assert set(re.findall(r"'([a-z_]+)'", body)) == set(ERRORS)
