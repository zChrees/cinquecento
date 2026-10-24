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

Un "logger" è l'oggetto a cui un file manda i suoi messaggi (log.info(...)); un
"gestore" (handler) decide dove finiscono (il terminale, un file); un "formatter"
decide com'è scritta la riga.

Cosa contiene:
    LOG_FILE_NAME, LOG_MAX_BYTES, LOG_BACKUP_COUNT, LOG_FORMAT   nome, misure e forma
    SafeFormatter               scrive la riga e nasconde i valori del database
    _Anomalies(handler)         passa a handler solo WARNING ed ERROR del server web
    configure_logging(app)      livelli, formato e file con rotazione
    remove_file_handlers(app)   toglie il file di log aggiunto prima

DA DOVE ARRIVANO I DATI: configure_logging la chiama create_app() (app/__init__.py)
con LOG_LEVEL e LOG_DIR della configurazione (config.py e .env); le righe arrivano
da tutti i file che usano logging.getLogger(__name__) sotto app/.
"""

import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

from flask.logging import default_handler

from config import BaseConfig

LOG_FILE_NAME = "cinquecento.log"
LOG_MAX_BYTES = 1_000_000  # 1 MB; in Python i trattini bassi separano le cifre, come gli spazi in 1 000 000
LOG_BACKUP_COUNT = 5
# Per esempio "2026-10-24 18:03:11,402 INFO [app] Applicazione avviata (configurazione development)"
LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"

# Valori dentro gli errori del database: la riga "[parameters: ...]" di SQLAlchemy e
# il valore doppio di MySQL ("Duplicate entry 'Mario' for key ..."). Ogni coppia è
# (espressione regolare, testo che la sostituisce).
_HIDDEN = (
    (re.compile(r"^\[parameters: .*$", re.MULTILINE), "[parameters: nascosti nel log]"),
    (re.compile(r"Duplicate entry '.*?' for key"), "Duplicate entry '...' for key"),
)

# Segno sui gestori aggiunti qui, per toglierli quando create_app() viene richiamata
_MARK = "_cinquecento_log"


# "class SafeFormatter(logging.Formatter)": un Formatter con un comportamento in più.
# La classe "eredita" tutto da logging.Formatter e cambia solo format.
class SafeFormatter(logging.Formatter):
    """Formatta la riga e poi nasconde i valori degli errori del database.

    In parole semplici:
        SafeFormatter(LOG_FORMAT)
        Si usa come un Formatter qualunque; in una riga di errore
        "Duplicate entry 'Mario' for key ..." diventa "Duplicate entry '...' for key ...".
    """

    def format(self, record):
        """La riga del messaggio `record`, con i valori del database nascosti.

        In parole semplici:
            format(record)
            La chiama il sistema dei log per ogni messaggio. super().format(record)
            è il format di logging.Formatter, la classe "madre": scrive la riga
            normale; poi ogni coppia di _HIDDEN sostituisce i valori da nascondere.
        """
        text = super().format(record)
        for pair in _HIDDEN:
            pattern = pair[0]
            replacement = pair[1]
            text = pattern.sub(replacement, text)
        return text


class _Anomalies(logging.Handler):
    """Passa al file solo WARNING ed ERROR del server web.

    È un gestore a parte, con il suo livello, perché Werkzeug scrive le righe delle
    richieste sul terminale solo se nessun gestore del suo livello (INFO) le riceve già.

    In parole semplici:
        _Anomalies(handler)
        handler è il gestore del file (il RotatingFileHandler di configure_logging).
        _Anomalies riceve i messaggi del server web e passa a handler solo quelli
        dal livello WARNING in su.
    """

    def __init__(self, target):
        """Prepara il gestore.

        In parole semplici:
            _Anomalies(target)
            super().__init__(logging.WARNING) è il costruttore di logging.Handler,
            la classe "madre", con il livello minimo; target è il gestore del file.
        """
        super().__init__(logging.WARNING)
        self.target = target

    def emit(self, record):
        """Passa il messaggio al gestore del file.

        In parole semplici:
            emit(record)
            La chiama il sistema dei log solo per i messaggi dal livello WARNING in
            su (quelli sotto si fermano prima, per il livello del gestore).
        """
        self.target.handle(record)

    def close(self):
        """Chiude il gestore del file e poi sé stesso.

        In parole semplici:
            close()
            La chiama remove_file_handlers (e Python alla fine del programma).
        """
        self.target.close()
        super().close()


def configure_logging(app):
    """Chiamata da create_app(): livelli, formato e file con rotazione.

    In parole semplici:
        configure_logging(app)
        1. dà a tutti i messaggi la forma di LOG_FORMAT, con i valori del database
           nascosti (SafeFormatter), e il livello LOG_LEVEL;
        2. toglie il file di un create_app() precedente (remove_file_handlers);
        3. nei test, se LOG_DIR è la cartella logs/ vera, si ferma: niente file;
        4. altrimenti apre logs/cinquecento.log con la rotazione e ci manda i
           messaggi dell'applicazione e le anomalie del server web (_Anomalies).
    """
    formatter = SafeFormatter(LOG_FORMAT)
    app.logger.setLevel(app.config["LOG_LEVEL"])
    default_handler.setFormatter(formatter)
    remove_file_handlers(app)

    log_dir = Path(app.config["LOG_DIR"])
    if app.testing and log_dir.resolve() == Path(BaseConfig.LOG_DIR).resolve():
        return
    log_dir.mkdir(parents=True, exist_ok=True)
    # delay=True: il file si apre solo al primo messaggio
    handler = RotatingFileHandler(
        log_dir / LOG_FILE_NAME,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
        delay=True,
    )
    handler.setFormatter(formatter)
    web = _Anomalies(handler)
    # Il segno _MARK sui due gestori: così remove_file_handlers li riconosce
    setattr(handler, _MARK, True)
    setattr(web, _MARK, True)
    app.logger.addHandler(handler)
    logging.getLogger("werkzeug").addHandler(web)
    app.logger.info("Applicazione avviata (configurazione %s)", app.config["ENV_NAME"])


def remove_file_handlers(app):
    """Toglie e chiude il file di log aggiunto da una configure_logging precedente.

    In parole semplici:
        remove_file_handlers(app)
        Guarda i gestori del logger dell'applicazione e di quello del server web
        (werkzeug) e toglie quelli con il segno _MARK. Serve quando create_app()
        si chiama più volte (nei test): altrimenti ogni riga si scriverebbe più
        volte e il file resterebbe aperto.
    """
    for logger in (app.logger, logging.getLogger("werkzeug")):
        # marked: i gestori da togliere, in un elenco a parte: togliere elementi da
        # logger.handlers mentre lo si scorre ne salterebbe qualcuno
        marked = []
        for handler in logger.handlers:
            if getattr(handler, _MARK, False):
                marked.append(handler)
        for handler in marked:
            logger.removeHandler(handler)
            handler.close()
