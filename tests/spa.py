"""Il frontend React compilato per i test (passo 4 della migrazione).

Le pagine della SPA (/auth/login, /auth/register, ...) Flask le prende da
app/static/dist/, che non è nel repository (D54) e che i test non devono toccare.
Per questo tests/conftest.py, all'avvio di ogni suite, chiama prepare_spa(): compila
il frontend in una cartella temporanea fuori dal progetto e la indica a Flask con
SPA_DIST_DIR (config.py, solo con APP_ENV=testing). La cartella si chiama con
l'impronta (hash) dei sorgenti: se i sorgenti non cambiano si riusa, e la
compilazione si fa una volta sola (circa un secondo) per tutte le suite.

Senza Node o senza frontend/node_modules (npm ci) non si compila niente: i test
che aprono una pagina della SPA chiamano needs_spa() e si saltano.
"""

import hashlib
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parents[1]
FRONTEND = BASE_DIR / "frontend"
VITE = FRONTEND / "node_modules" / "vite" / "bin" / "vite.js"
CACHE = Path(tempfile.gettempdir()) / "cinquecento-test-dist"
# I file da cui dipende il build: se cambia uno di questi, si ricompila
SOURCES = ("index.html", "vite.config.ts", "tsconfig.json", "package-lock.json")


def _fingerprint():
    digest = hashlib.sha256()
    files = [FRONTEND / name for name in SOURCES] + sorted((FRONTEND / "src").rglob("*"))
    for path in files:
        if path.is_file():
            digest.update(path.relative_to(FRONTEND).as_posix().encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


def prepare_spa():
    """Compila il frontend (se serve) e imposta SPA_DIST_DIR; restituisce la cartella o None."""
    node = shutil.which("node")
    if node is None or not VITE.is_file():
        return None
    out = CACHE / _fingerprint()
    if not (out / "index.html").is_file():
        for old in CACHE.glob("*"):
            shutil.rmtree(old, ignore_errors=True)
        result = subprocess.run(
            [node, str(VITE), "build", "--outDir", str(out), "--emptyOutDir", "--logLevel", "error"],
            cwd=FRONTEND, capture_output=True, text=True, encoding="utf-8", timeout=120, check=False,
        )
        if result.returncode != 0:
            pytest.exit(f"Compilazione del frontend non riuscita:\n{result.stdout}{result.stderr}", returncode=2)
    os.environ["SPA_DIST_DIR"] = str(out)
    return out


def needs_spa():
    """Salta il test se il frontend non è compilato (manca Node o npm ci)."""
    if not os.environ.get("SPA_DIST_DIR"):
        pytest.skip("Frontend non compilato per i test: serve Node e npm ci in frontend/")
