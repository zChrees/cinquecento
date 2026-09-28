# Riepiloghi di Christian

> **Questo file lo scrive solo Christian** (Studente 3: interfaccia e documenti). Giuseppe e Antonio lo leggono dopo il `git pull` di `dev`, per sapere cosa è cambiato: punti fatti, decisioni nuove e cosa devono fare loro. Nessun altro lo modifica, nemmeno per correggere un errore: si segnala a Christian.
>
> **Come si aggiorna** (regola in `CLAUDE.md`, "Consegna"): a fine punto, e dopo ogni aggiornamento dei documenti condivisi, Christian aggiunge il riepilogo **in cima** alla sezione "Riepiloghi", nello stesso branch e commit; così arriva in `dev` con il merge. È il gemello di `giuseppe.md`.

## Schema

```markdown
### P<numero> — <titolo> (<data>)

- **Branch**: feature/… oppure docs/…
- **File**: creati …; modificati …; cancellati …
- **Controlli**: <N> PASS in tutto (<M> nuovi), `ruff check .` pulito
- **Decisioni prese**: … oppure "nessuna"
- **Domande nuove**: … oppure "nessuna"
- **Punti delicati**: …
- **Cosa devono fare gli altri**: … oppure "niente"
```

## Riepiloghi

<!-- Il più recente in cima. I riepiloghi di P3, P52, P8 e P19 li ha ricostruiti Christian il 28/09/2026 dalle note di SCALETTA.md. -->

### Documenti: P5, P14, P15 e nascita di questo file (28/09/2026)

- **Branch**: docs/p5-p14-p15
- **File**: creato `christian.md`; modificati `SCALETTA.md` (P5, P14 e P15 spuntati, "Da dove si parte"), `DECISIONI.md`, `CLAUDE.md` (riga "Stato", comando del database, numero di test, punti delicati, regola di `christian.md`), `README.md` (installazione del database)
- **Controlli**: nessun codice cambiato; 658 PASS restano quelli di P5
- **Decisioni prese**: `christian.md` come `giuseppe.md`, scritto solo da Christian (`DECISIONI.md`, Processo)
- **Domande nuove**: nessuna
- **Punti delicati**: nessuno
- **Cosa devono fare gli altri**: leggere questo file dopo ogni pull di `dev`

### P5 — Database e prima migrazione (28/09/2026)

Punto di Antonio, fatto da Christian con Claude Code perché Antonio oggi non c'era.

- **Branch**: feature/p5-database (commit `976dec5`, in `dev` e su GitHub dopo un rebase su P14 e P15, senza conflitti)
- **File**: creati `scripts/setup_db.sql`, `scripts/migrate.py`, `migrations/001_init.sql`, `app/models/user.py`, `rating.py`, `match.py`, `friendship.py` (amicizie e blocchi), `chat_message.py`, `tests/db/test_migrate.py`; modificato `app/models/__init__.py`; cancellato `docs/proposta-tabelle.sql` (le tabelle ora stanno in `migrations/001_init.sql`)
- **Controlli**: 658 PASS in tutto (55 nuovi, nella suite `db`), `ruff check .` pulito
- **Cosa fa**:
  - `setup_db.sql` crea `cinquecento_dev`, `cinquecento_test` e l'utente MySQL `cinquecento`, che può usare solo quei due database; la password la genera MySQL e la mostra una volta sola;
  - `migrate.py` applica i file di `migrations/` non ancora registrati in `versione_schema`; rilanciato non fa niente; si ferma con un messaggio chiaro se un file ha un nome sbagliato, se due file hanno lo stesso numero o se il database ha tabelle ma non `versione_schema`;
  - i modelli hanno classi e attributi in inglese e colonne in italiano (`User.username` → `nome_utente`, come vuole `base.html`); `User` ha già `UserMixin` per Flask-Login (P16); nessun modello crea tabelle;
  - i test provano tutte le regole del "Fatto quando" su `cinquecento_test`, dentro transazioni annullate alla fine, e confrontano ogni modello con le colonne vere delle tabelle.
- **Decisioni prese**:
  - password dell'utente MySQL generata da MySQL (`IDENTIFIED BY RANDOM PASSWORD`): niente segreti nel repository;
  - **modifica a D38**: `partite.modalita`, `partite.motivo_fine`, `giocatori_partita.risultato` e `rating.modalita` non sono più `ENUM` ma testo esatto con un `CHECK`, perché un `ENUM` scritto senza valore prendeva in silenzio il primo dell'elenco (un giocatore senza risultato diventava `'vittoria'`);
  - una migrazione già applicata non si modifica più: le prossime modifiche alle tabelle vanno in `002_...sql`, da concordare.
- **Domande nuove**: nessuna
- **Punti delicati**:
  - verificato che MySQL accetta le colonne `VIRTUAL` delle amicizie: "una sola riga per coppia" la garantisce il database, P45 non deve controllarla (resta al servizio solo "non chiedere l'amicizia a se stessi");
  - i test del database vogliono MySQL in modalità rigorosa (`STRICT_TRANS_TABLES`, il valore predefinito di MySQL 8.0);
  - in PowerShell `mysql ... < file` non funziona: il comando giusto è in `README.md`, Installazione, passo 6.
- **Bug trovato fuori dal punto**: in `app/checks.py` (P4, Giuseppe) `url.set(database=None)` non toglie il nome del database, perché SQLAlchemy ignora i valori `None`; così il controllo di avvio di `run.py` si collega già a `DB_NAME` e, se il database non esiste, dà un messaggio sbagliato ("controlla utente e password" invece di "database sconosciuto"). La correzione è `url._replace(database=None)` oppure `URL.create` senza database: una riga, su un branch `fix/…`.
- **Cosa devono fare gli altri**:
  - **tutti**, una volta sola dopo il pull: lanciare `setup_db.sql`, copiare la password nel `.env` e lanciare `python scripts/migrate.py` (`README.md`, Installazione, passo 6);
  - **Giuseppe**: P6 non aspetta più niente; correggere `app/checks.py` se è d'accordo;
  - **Antonio**: P5 è fatto; i prossimi sono P7 e P18, appena P6 è in `dev`, poi P16. Il modello `User` e le tabelle ci sono già.

### P19 — Base grafica mobile-first (28/09/2026)

- **Branch**: feature/p19-base-grafica (commit `03648ef`)
- **File**: `app/templates/base.html`, messaggi flash, CSS di base e dei componenti presi dal prototipo (colori solo in `variables.css`), `Modal.js`, `dom.js`
- **Controlli**: 13 test nuovi, 425 PASS in tutto dopo il rebase su P12 e P13; foto a 360×640, 360×560 e 1440×900
- **Decisioni prese**: messaggi del server in basso al centro, spariscono dopo 7 secondi; nelle pagine con un modulo scorre solo il riquadro, mai la pagina
- **Cosa devono fare gli altri**: il modello utente deve avere `username` e `avatar` (fatto in P5)

### P8 — Contratto tra server e pagine (28/09/2026)

- **Branch**: feature/p8-contratto (commit `ab876d8`)
- **File**: `docs/CONTRATTO-SOCKET.md`, 5 file di esempio in `app/static/dev/`
- **Controlli**: 106 PASS in tutto, dopo il rebase su P10 e P11
- **Decisioni prese**: approvato dai tre di persona; da ora il contratto cambia solo con l'accordo di tutti e tre
- **Cosa devono fare gli altri**: usare i nomi e le forme del contratto e dei file di esempio

### P52 — Prototipo della home (27/09/2026)

- **File**: `docs/prototipo/` (`index.html`, `prototipo.css`, `prototipo.js`, `LEGGIMI.md`, `img/`)
- **Decisioni prese**: tutte in `DECISIONI.md`, Interfaccia ("Versione finale del prototipo"); le immagini entrano nel progetto con P40
- **Cosa devono fare gli altri**: è il riferimento grafico di P19, P40 e P22

### P3 — Riga "Stato" e regola di consegna (28/09/2026)

- **File**: `CLAUDE.md`
- **Cosa devono fare gli altri**: a fine punto mandare il riepilogo (Giuseppe in `giuseppe.md`, Antonio a Christian)
