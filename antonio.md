# Riepiloghi di Antonio

> **Questo file lo scrive solo Antonio** (Studente 2: account, dati, amici). Christian lo legge dopo il `git pull` di `dev` e da qui aggiorna i documenti condivisi (`SCALETTA.md`, `CLAUDE.md`, `DECISIONI.md`, `DA-DECIDERE.md`); Giuseppe lo legge per sapere cosa è cambiato. Nessun altro lo modifica, nemmeno per correggere un errore: si segnala ad Antonio.
>
> **Come si aggiorna** (regola in `CLAUDE.md`, "Consegna"): a fine punto, nel branch del punto (`feature/…`, `fix/…`), Antonio aggiunge il riepilogo **in cima** alla sezione "Riepiloghi", nello stesso commit del punto; così arriva in `dev` con il merge. Il numero del commit non si scrive: lo si trova con `git log -- antonio.md`.
>
> **Cosa legge Antonio**: dopo il `git pull` di `dev`, `christian.md` e `giuseppe.md`, per le modifiche al progetto e le informazioni utili al suo lavoro (per esempio le funzioni da usare senza modificarle, come `create_room(...)` di P24).

## Schema

```markdown
### P<numero> — <titolo> (<data>)

- **Branch**: feature/…
- **File**: creati …; modificati … (se fuori elenco: perché e con l'ok di chi)
- **Controlli**: <N> PASS in tutto (<M> nuovi), `ruff check .` pulito
- **Decisioni prese**: … oppure "nessuna"
- **Domande nuove**: … oppure "nessuna"
- **Punti delicati**: …
- **Note per il contratto o per gli altri**: … oppure "nessuna"
```

## Riepiloghi

<!-- Il più recente in cima. File creato da Christian il 28/09/2026 con lo schema; da qui in poi lo scrive solo Antonio. Il riepilogo di P16 (punto di Antonio fatto da Giuseppe) è in giuseppe.md, quello di P5 (fatto da Christian) in christian.md. -->

### P17 — Impostazioni: avatar e cancellazione dell'account (28/09/2026)

- **Branch**: feature/p17-impostazioni
- **File**: modificati `app/blueprints/profile/routes.py` (segnaposto di P4), `app/services/auth_service.py`, `app/repositories/user_repo.py` (P16); creati `app/services/avatars.py`, `app/templates/profile/settings.html`, `app/static/js/pages/profile.js`, `app/static/css/pages/profile.css`, `tests/api/test_impostazioni.py`. Nessun file fuori elenco
- **Controlli**: 866 PASS in tutto (30 nuovi, nella suite `api`), `ruff check .` pulito; foto con Chrome a 360 px di larghezza e a 1440×900
- **Decisioni prese** (scelte di Antonio sulle raccomandazioni di Claude):
  - **D29, i 12 avatar** (resta aperto solo chi disegna le immagini e con che licenza, per P43): i 4 semi `coppe`, `denari`, `spade`, `bastoni`; i 4 Re `re_coppe`, `re_denari`, `re_spade`, `re_bastoni`; `cavallo_coppe`, `cavallo_bastoni`; `fante_denari`, `fante_spade`. Ogni seme ha 3 avatar e ci sono tutte e tre le figure. I nomi mostrati sono "Coppe", "Re di denari", "Fante di spade"…; l'elenco sta in `app/services/avatars.py` (`AVATARS`, codice → nome);
  - **per cancellare l'account si riscrive la password**, in una finestra nella pagina (`Modal.js`). Le password sbagliate contano come gli errori di login (stesso limite di 5 e stesso blocco di 5 minuti, che vale anche per il login).
- **Scelte tecniche**:
  - indirizzi: `GET /profile/settings` (pagina), `POST /profile/avatar` (campo `avatar`), `POST /profile/delete` (campo `password`), tutti con il login e il codice CSRF;
  - nella griglia c'è anche "Iniziale" (valore vuoto = nessun avatar, `avatar` a `NULL`); ogni codice fuori elenco si rifiuta con "Avatar non valido: scegline uno dell'elenco.";
  - dopo la cancellazione si esce dall'account e si torna alla home con "Account cancellato…". Il resto lo fa MySQL con le chiavi esterne (D6): rating, amicizie, blocchi e messaggi spariscono, nelle partite resta "utente eliminato" (c'è un test);
  - **chi ha una partita in corso non si può cancellare** ("Hai una partita in corso: finiscila prima…"), con `find_room_of_user` di P24, usata senza modificarla: a fine partita il salvataggio (P26) cercherebbe un utente che non c'è più.
- **Domande nuove**: nessuna
- **Punti delicati**:
  - il controllo "partita in corso" non è nella stessa transazione della cancellazione: se una partita partisse proprio tra il controllo e la cancellazione, P26 troverebbe un utente cancellato. È una finestra di pochi millesimi di secondo; quando P28 (coda) e P47 (inviti) aggiungono altri stati ("in coda", "invito in sospeso"), vanno controllati anche loro prima di cancellare;
  - le schede già collegate in tempo reale di un utente cancellato non vengono chiuse subito; al prossimo evento il login non dovrebbe più valere, perché l'utente non si trova più nel database (dedotto, non provato);
  - un codice di avatar già scelto da qualcuno non si cambia più (resterebbe nel database): P43 aggiunge solo le immagini, una per codice;
  - la pagina usa la classe `page--form`: su telefono la parte "Cancella l'account" scorre dentro il riquadro, come deciso per le pagine con un modulo.
- **Note per il contratto o per gli altri**: nessun cambiamento al contratto. **Christian**: D29 si può chiudere per la parte "quali figure" (codici sopra); P43 mostra le immagini nella griglia di `settings.html` (ogni riquadro ha `data-avatar="<codice>"`). **Giuseppe**: nessuna modifica ai tuoi file; `auth_service.py` ora importa `find_room_of_user` da `app/realtime/room_manager.py`.

### P18 — Backup e ripristino (28/09/2026)

- **Branch**: feature/p18-backup
- **File**: creati `scripts/backup.py`, `scripts/ripristina.py`, `tests/db/test_backup.py`. Nessun file fuori elenco
- **Controlli**: 836 PASS in tutto (27 nuovi, nella suite `db`), `ruff check .` pulito
- **Decisioni prese**: nessuna sul progetto; D10 resta aperta (`BACKUP_RETENTION_DAYS = 14`, provvisorio in `config.py`). Scelte tecniche:
  - `python scripts/backup.py` salva il database del `.env` in `backups/<database>_AAAA-MM-GG_HHMMSS.sql.gz` (ora locale), compresso; poi cancella i backup più vecchi di `BACKUP_RETENTION_DAYS` giorni. Cancella **solo** i file con quella forma del nome, e l'età la legge dal nome, non dalla data del file;
  - `python scripts/ripristina.py <file> <database>` ricarica un backup nel database indicato. Se il nome non finisce con `_test`, chiede di **scrivere il nome del database** per confermare (un "sì" non basta); prima di toccare il database controlla che il file sia intero e sia un backup di MySQL;
  - `mysqldump` e `mysql` si cercano nel PATH e poi in `C:\Program Files\MySQL\MySQL Server 8.0\bin` (da me non sono nel PATH);
  - la password non passa mai sulla riga di comando e non si stampa: sta in un file di opzioni temporaneo, cancellato alla fine;
  - opzioni di `mysqldump`: `--single-transaction` (copia coerente senza bloccare le tabelle), `--no-tablespaces` (senza, serve il permesso PROCESS, che l'utente `cinquecento` non ha), `--set-gtid-purged=OFF`, `--skip-dump-date`. Il backup non contiene `CREATE DATABASE` né `USE`, quindi si può ricaricare in un database diverso da quello di partenza.
- **Domande nuove**: nessuna
- **Punti delicati**:
  - un backup non riuscito non lascia file: si scrive come `.parziale` e prende il nome vero solo alla fine;
  - il ripristino sostituisce le tabelle presenti nel backup; le tabelle che nel backup non ci sono restano come sono;
  - l'utente MySQL del `.env` può scrivere solo in `cinquecento_dev` e `cinquecento_test` (`setup_db.sql`): per il database della demo (P38) servirà un `GRANT` anche su quello;
  - il backup **giornaliero** (decisione "Backup giornaliero con `mysqldump`") va programmato sul PC della demo, per esempio con l'Utilità di pianificazione di Windows: non è in P18, va in P38;
  - la suite `db` ora vuole anche i programmi `mysqldump` e `mysql`: se mancano, i test si fermano con un messaggio chiaro.
- **Note per il contratto o per gli altri**: nessun cambiamento al contratto. **Christian**: in "Comandi utili" di `CLAUDE.md` i comandi di P18 sono già giusti (`python scripts/backup.py`, `python scripts/ripristina.py <file> <database>`); vanno aggiunte le note sulla conferma e sui programmi di MySQL, se le vuoi nel README.

### P7 — Log ed errori di base (28/09/2026)

- **Branch**: feature/p7-log-errori
- **File**: modificati `app/logging_config.py`, `app/errors.py` (segnaposto di P4); creati `app/templates/errors/404.html`, `app/templates/errors/500.html`, `tests/api/test_errori.py`. Nessun file fuori elenco
- **Controlli**: 809 PASS in tutto (19 nuovi, nella suite `api`), `ruff check .` pulito
- **Decisioni prese** (scelte di Antonio sulle raccomandazioni di Claude):
  - **pagine di errore senza navbar**: solo il messaggio e "Torna alla home". Non hanno uno script di pagina, e senza quello la navbar non si apre; in più la pagina 500 così dipende il meno possibile dal database. Se anche la pagina 500 non si può mostrare (per esempio il database non risponde e `base.html` cerca l'utente), si risponde con una pagina minima scritta in `errors.py`;
  - **nel file di log niente righe delle singole richieste** del server web, che contengono l'indirizzo IP (un dato personale): restano sul terminale; nel file vanno i messaggi dell'applicazione e solo WARNING ed ERROR del server web;
  - **errori delle richieste JSON** (`/stats/…`, `/friends/…`) nella forma del contratto (1.2): `{"ok": false, "error": {"code": "not_found" | "server_error", "message"}}`; le altre richieste ricevono la pagina HTML.
- **Scelte tecniche**: file `logs/cinquecento.log`, con rotazione a 1 MB e 5 file vecchi; formato `data ora LIVELLO [parte del programma] messaggio`; il livello viene da `LOG_LEVEL` del `.env`. Gli errori imprevisti degli eventi socket, nei gestori che non usano `handler` di `events.py`, vanno nel log con il solo nome dell'evento (mai i dati, che possono contenere testo degli utenti) e rispondono `server_error` solo a chi ha mandato l'evento; se si rompe il controllo di `connect`, la connessione si rifiuta.
- **Domande nuove**: nessuna
- **Punti delicati**:
  - negli errori del database SQLAlchemy scrive i valori della query (email, hash della password) e MySQL il valore doppio (`Duplicate entry 'Mario'`): `SafeFormatter` in `logging_config.py` li nasconde prima di scrivere la riga (c'è un test). Resta valida la regola: **mai** dati personali, password, token o testo della chat nei messaggi di log;
  - i test non scrivono mai in `logs/`: con la configurazione `testing` il file si apre solo se `LOG_DIR` punta altrove (i test usano una cartella temporanea);
  - `create_app()` chiamata più volte (succede nei test) non raddoppia il file di log: il gestore vecchio si toglie e si chiude;
  - la pagina 500 in un test si vede solo con `PROPAGATE_EXCEPTIONS = False`: con `TESTING` Flask rilancia l'errore invece di mostrare la pagina;
  - le pagine di errore usano le classi di `css/pages/auth.css` (riquadro, titolo e sottotitolo centrati), senza modificarlo.
- **Note per il contratto o per gli altri**: nessun cambiamento al contratto. **Christian**: le pagine 404 e 500 sono senza navbar, come deciso; se si vuole la navbar anche lì, serve uno script di pagina (come per `js/pages/auth.js`). **Giuseppe**: i gestori degli eventi che usano già `handler` non cambiano; il gestore generale di `errors.py` vale solo per quelli che non lo usano.
