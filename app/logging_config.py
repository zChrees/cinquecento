"""Configurazione dei log (P7).

- Il file logs/cinquecento.log (LOG_DIR) raccoglie i messaggi dell'applicazione (il
  logger "app" e i suoi figli, come app.services.auth_service) dal livello LOG_LEVEL
  in su, e del server web solo le anomalie (WARNING ed ERROR): le righe di ogni
  richiesta, con l'indirizzo IP di chi la fa, restano sul terminale.
- Rotazione: quando il file arriva a 1 MB diventa cinquecento.log.1 e se ne apre uno
  nuovo; si tengono 5 file vecchi, poi il più vecchio si cancella.
- Livelli: INFO per gli eventi normali, WARNING per le anomalie, ERROR per gli errori.
- Mai dati personali, password, token o testo della chat nei messaggi. In più qui si
  nascondono i valori che MySQL e SQLAlchemy mettono nei loro errori (per esempio
  email e hash della password di una INSERT), prima di scrivere la riga.
- I test non scrivono mai nella cartella logs/ vera: nei test il file si scrive solo
  se LOG_DIR punta altrove (una cartella temporanea).
"""

import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

from flask.logging import default_handler

from config import BaseConfig

LOG_FILE_NAME = "cinquecento.log"
LOG_MAX_BYTES = 1_000_000
LOG_BACKUP_COUNT = 5
LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"

# Valori dentro gli errori del database: la riga "[parameters: ...]" di SQLAlchemy e
# il valore doppio di MySQL ("Duplicate entry 'Mario' for key ...").
_HIDDEN = (
    (re.compile(r"^\[parameters: .*$", re.MULTILINE), "[parameters: nascosti nel log]"),
    (re.compile(r"Duplicate entry '.*?' for key"), "Duplicate entry '...' for key"),
)

# Segno sui gestori aggiunti qui, per toglierli quando create_app() viene richiamata
_MARK = "_cinquecento_log"


class SafeFormatter(logging.Formatter):
    """Formatta la riga e poi nasconde i valori degli errori del database."""

    def format(self, record):
        text = super().format(record)
        for pattern, replacement in _HIDDEN:
            text = pattern.sub(replacement, text)
        return text


class _Anomalies(logging.Handler):
    """Passa al file solo WARNING ed ERROR del server web.

    È un gestore a parte, con il suo livello, perché Werkzeug scrive le righe delle
    richieste sul terminale solo se nessun gestore del suo livello (INFO) le riceve già.
    """

    def __init__(self, target):
        super().__init__(logging.WARNING)
        self.target = target

    def emit(self, record):
        self.target.handle(record)

    def close(self):
        self.target.close()
        super().close()


def configure_logging(app):
    """Chiamata da create_app(): livelli, formato e file con rotazione."""
    formatter = SafeFormatter(LOG_FORMAT)
    app.logger.setLevel(app.config["LOG_LEVEL"])
    default_handler.setFormatter(formatter)
    remove_file_handlers(app)

    log_dir = Path(app.config["LOG_DIR"])
    if app.testing and log_dir.resolve() == Path(BaseConfig.LOG_DIR).resolve():
        return
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        log_dir / LOG_FILE_NAME,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
        delay=True,
    )
    handler.setFormatter(formatter)
    web = _Anomalies(handler)
    for h in (handler, web):
        setattr(h, _MARK, True)
    app.logger.addHandler(handler)
    logging.getLogger("werkzeug").addHandler(web)
    app.logger.info("Applicazione avviata (configurazione %s)", app.config["ENV_NAME"])


def remove_file_handlers(app):
    """Toglie e chiude il file di log aggiunto da una configure_logging precedente."""
    for logger in (app.logger, logging.getLogger("werkzeug")):
        for handler in [h for h in logger.handlers if getattr(h, _MARK, False)]:
            logger.removeHandler(handler)
            handler.close()
