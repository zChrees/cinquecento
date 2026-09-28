"""Controlli comuni a tutte le suite (P6), validi anche lanciando pytest a mano, senza il runner.

- I test non partono in un'installazione vera (file PRODUZIONE nella cartella del progetto)
  né con un database dei test che non finisce con _test.
- I test girano sempre con la configurazione "testing" (APP_ENV).
- La cartella del progetto è nel percorso di import: `pytest tests/...` trova app e config.
"""

import os
import sys
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Prima di importare config: load_dotenv non sovrascrive le variabili già impostate.
os.environ["APP_ENV"] = "testing"

from config import ConfigError, load_config


def pytest_configure(config):
    if (BASE_DIR / "PRODUZIONE").exists():
        pytest.exit(
            "Trovato il file PRODUZIONE: questa è un'installazione vera, i test non partono.",
            returncode=2,
        )
    try:
        load_config("testing")
    except ConfigError as exc:
        pytest.exit(f"Test non avviati: {exc}", returncode=2)
