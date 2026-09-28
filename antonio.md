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

### P26 — Salvataggio delle partite (28/09/2026)

- **Branch**: feature/p26-salvataggio
- **File**: creati `app/services/match_service.py`, `app/repositories/match_repo.py`, `tests/services/test_match_service.py` (suite nuova `services`); modificato `app/realtime/room.py`, **un po' più di "solo la chiamata"** (scelta 1a di Antonio, vedi sotto). Nessun altro file
- **Controlli**: 995 PASS in tutto, in 7 suite (15 nuovi, nella suite `services`), `ruff check .` pulito
- **Decisioni prese** (scelte di Antonio sulle raccomandazioni di Claude):
  - **1a, `room.py` tiene l'elenco delle mosse**: il motore conserva solo lo stato attuale, non lo storico, quindi senza questo `mosse_partita` resterebbe vuota. La scaletta diceva di toccare `room.py` "solo per la chiamata al salvataggio": in più ci sono l'elenco delle mosse in memoria (`_moves`) e la loro registrazione in `play`, `sing`, nella mossa automatica e in `abandon`;
  - **2a, mosse salvate** (`mosse_partita.tipo` e `dettagli`, nomi in italiano come le colonne, D38): `gioca_carta` `{"seme", "valore"}`; `canta` `{"seme", "punti"}` (40 o 20, letti dal motore); `mossa_automatica` `{"seme", "valore"}` (tempo scaduto, D12); `abbandono` `{"motivo": "esci" | "tempo_scaduto"}`. Ogni mossa ha numero progressivo da 1, mano, posto e ora (UTC, con i millesimi).
- **Scelte tecniche**:
  - la stanza, a fine partita, prepara un `MatchRecord` (modalità, punteggio, rating sì/no, inizio e fine, motivo, squadra vincente, punti finali, giocatori e mosse) e chiama `match_service.save_match`, che controlla i dati e scrive `partite`, `giocatori_partita` e `mosse_partita` in **una sola transazione**; un errore a metà fa rollback e non resta niente (provato con un errore finto dopo partita e giocatori, e con un utente inesistente);
  - risultato per giocatore da `winner_team`: `vittoria`, `sconfitta` o `pareggio`; `ha_abbandonato` per chi è uscito; nell'abbandono vince l'altra squadra (nel 2v2 perde tutta la squadra, D13);
  - si salva **una volta sola**, nei due punti in cui la partita finisce: `Room._apply` (per punteggio) e `Room.abandon` (per abbandono);
  - la partita può finire per un timer, fuori da una richiesta: la stanza si ricorda l'applicazione Flask quando la partita parte (`has_app_context`) e salva dentro `app.app_context()`. Una stanza creata fuori da Flask (per esempio dai test di P24 e P25, che chiamano `create_room` direttamente) non salva e lo scrive nel log (WARNING);
  - se il salvataggio fallisce, i giocatori vedono comunque il risultato; l'errore va nel log (ERROR).
- **Domande nuove**: nessuna
- **Punti delicati**:
  - **`create_room` va chiamata dentro Flask** (un gestore di un evento o di una richiesta), altrimenti la partita non si salva: vale per P28, P29 (coda) e P47 (inviti), che la chiamano dai loro gestori;
  - il salvataggio avviene sotto il lock della stanza: l'ultima mossa aspetta la scrittura nel database (pochi millesimi);
  - `utente_id` deve esistere al momento del salvataggio: P17 già impedisce di cancellare l'account durante una partita.
- **Note per il contratto o per gli altri**: nessun cambiamento al contratto. **Antonio** (P27, rating): l'aggiornamento del rating va in `match_service.save_match`, prima del `commit`, così sta nella stessa transazione. **Giuseppe**: `room.py` ha l'elenco delle mosse e il salvataggio; `Room._apply` ora vuole anche il tipo e i dettagli della mossa. **Christian** (P30, statistiche): le partite finite sono in `giocatori_partita` (risultato per utente) e `partite`.

### P25 — Timer, riconnessione, abbandono (28/09/2026)

Punto di Giuseppe, fatto da Antonio con il suo permesso. Prima di cominciare: nessun branch di P25 su GitHub né sul PC.

- **Branch**: feature/p25-timer
- **File**: modificati `app/realtime/room.py`, `app/sockets/game_events.py` (P24), `app/sockets/connection_events.py` (P23), `app/static/js/pages/game.js` (P24); creato `tests/sockets/test_timer_riconnessione.py`. Nessun file fuori elenco
- **Controlli**: 980 PASS in tutto (17 nuovi, nella suite `sockets`; i test di P25 rilanciati 3 volte di fila senza errori), `ruff check .` pulito
- **Decisioni prese**: **chi non arriva mai al tavolo non ha limite di tempo** (scelta (b) di Antonio; Claude consigliava 60 secondi dall'inizio): non parte nessun conto alla rovescia e la mossa automatica gioca per lui finché la partita non finisce. Il conto alla rovescia di 60 secondi parte solo quando si scollega la scheda che era al tavolo
- **Scelte tecniche**:
  - **timer del turno** (D12): in `room.py`, un `threading.Timer` per stanza che riparte a ogni cambio di turno e gioca `auto_move` del motore sotto il lock della stanza. Porta un numero di turno (`_turn_token`): se il giocatore ha già giocato, il timer arrivato in ritardo non fa niente. Dopo un canto il turno resta allo stesso giocatore e il suo tempo continua; il timer continua anche se il giocatore è scollegato;
  - **scollegamento**: `connection_events.on_disconnect` chiama `room.disconnect(sid)` per le stanze dell'utente. Conta solo la scheda al tavolo: una scheda della home o una già sostituita (D14) non scollega il posto. Rientro con `game:join` entro `RECONNECT_SECONDS`; oltre, abbandono;
  - **abbandono** (`game:leave` o rientro fuori tempo): `room.abandon(seat)`. La vista diventa `status: "finished"`, `turn: null`, `legal` vuoto, `result` = `{"reason": "abandon", "winner_team": <l'altra squadra>, "abandoned_seats": [seat], "scores"}`; nel 2v2 perde tutta la squadra (D13). `room.finished` vale anche per l'abbandono, quindi `find_room_of_user` non trova più la partita. `game:leave` a partita finita risponde `ok` senza cambiare niente; da una scheda non al tavolo risponde `not_allowed`;
  - a partita finita (per punteggio o per abbandono) le mosse rispondono `not_allowed` "La partita è finita." (prima, per punteggio, era `illegal_move` dal motore);
  - i tempi si leggono da `TURN_SECONDS` e `RECONNECT_SECONDS` di `room.py` quando la partita parte (`room.turn_seconds`, `room.reconnect_seconds`): i test li riducono prima di creare la stanza, senza cambiare `config.py`. `turn.seconds_total` della vista è quello della stanza;
  - **pagina**: "Esci" manda `game:leave` dopo la conferma e poi va alla home; se la risposta è un errore (per esempio senza connessione) resta al tavolo e lo dice. A partita finita "Esci" va alla home senza chiedere. I secondi del turno e quelli per rientrare scendono da soli, contati dall'arrivo della vista; nella prova (`?demo=`) restano fermi, perché la vista finta è una fotografia (lo controlla `test_pagina_tavolo.py` di Christian).
- **Domande nuove**: nessuna
- **Punti delicati**:
  - una stanza finita resta nell'elenco `rooms` (come in P24): non occupa timer, ma nessuno la toglie. Con meno di 50 utenti non pesa; se serve, toglierla dopo il salvataggio (P26) o dopo qualche minuto;
  - `on_join`, `on_play_card` e `on_sing` (P24) vogliono sempre un argomento: un evento mandato senza dati risponde `server_error` invece di `invalid_data`. `on_leave` ha `data=None`; per gli altri è una correzione di una riga, non fatta qui;
  - il conto alla rovescia nella pagina non è stato provato nel browser con una partita vera (solo la logica del server con i test).
- **Note per il contratto o per gli altri**: nessun cambiamento al contratto. **Giuseppe**: P25 è fatto; i punti in cui la partita finisce sono due, `Room._apply` (per punteggio) e `Room.abandon` (per abbandono). **Antonio** (P26): la chiamata al salvataggio va in quei due punti. **Christian** (P57): la fine partita per abbandono usa il riquadro `Result` di `Table.js` che c'era già.

### P45 — Amicizie (28/09/2026)

- **Branch**: feature/p45-amicizie
- **File**: modificato `app/blueprints/friends/routes.py` (segnaposto di P4); creati `app/services/friend_service.py`, `app/repositories/friend_repo.py`, `tests/api/test_amicizie.py`. `app/blueprints/friends/__init__.py` era nell'elenco ma non è servito toccarlo
- **Controlli**: 925 PASS in tutto (59 nuovi, nella suite `api`), `ruff check .` pulito
- **Decisioni prese**: **`presence` calcolata già in P45** (scelta di Antonio sulla raccomandazione di Claude): `"in_game"` se `find_room_of_user` (P24) trova una partita in corso, `"online"` se l'utente ha almeno una scheda nel canale `user:<id>` (P23), altrimenti `"offline"`. Nessun file né stato in più; a P47 restano gli avvisi quando cambia (`friends:presence`, `friends:changed`)
- **Scelte tecniche** (il contratto 2.2 non le fissava):
  - `blocked` nella lista: `{"user_id", "username", "avatar"}`;
  - `counters.unread_messages`: tutti i messaggi non letti ricevuti, anche da chi non è più amico (la conversazione resta visibile, D24);
  - ordine: amici online, poi in partita, poi offline, e dentro ogni gruppo per username; richieste dalla più recente;
  - `POST /friends/requests` risponde con `data` = la richiesta mandata (`user_id`, `username`, `avatar`, `sent_at`), nella forma di `requests_out`;
  - codici: richiesta a sé stessi o blocco di sé stessi `invalid_data`; già amici o richiesta già mandata `already_exists`; accettare una richiesta che non c'è `not_found`; bloccare di nuovo lo stesso utente risponde `ok`, senza doppioni;
  - senza login le richieste rispondono `not_logged_in` (401, in JSON), non con il rimando alla pagina di accesso;
  - `request_id` (contratto 1.3): la risposta si ricorda in memoria per 10 minuti, per utente e per azione (`RecentRequests` in `friend_service.py`), sia per gli `ok` sia per gli errori del contratto; le richieste di uno stesso utente con `request_id` passano una alla volta.
- **Domande nuove**: nessuna
- **Punti delicati**:
  - **lettura dei dati dentro le scritture**: con il livello predefinito di MySQL (REPEATABLE READ) una transazione continua a vedere i dati com'erano alla prima lettura, che in una richiesta con il login avviene già quando Flask-Login carica l'utente. Così, anche dopo aver bloccato i due utenti (`SELECT ... FOR UPDATE`), il servizio non vedeva la richiesta appena salvata da un'altra scheda. Provato: due richieste incrociate contemporanee davano `Duplicate entry` (errore 500), e due accettazioni contemporanee superavano il limite di amici. Correzione: ogni scrittura chiude le letture precedenti e lavora in READ COMMITTED (`_write` in `friend_service.py`). **Vale anche per P48** (limite di 1 messaggio al secondo) e per ogni controllo "prima di scrivere" fatto con MySQL;
  - le date si scrivono da Python in UTC, non con `CURRENT_TIMESTAMP` di MySQL, che userebbe il fuso orario del server;
  - un modulo senza codice CSRF riceve il 400 di Flask-WTF in HTML, non in JSON (per la pagina basta sapere che è 400);
  - `RecentRequests` è una piccola classe riutilizzabile: se serve anche a P28, P47 o P48, conviene spostarla in un file comune (proposta di punto nuovo, non fatta qui).
- **Note per il contratto o per gli altri**: nessun cambiamento ai nomi del contratto; le scelte sopra completano i dettagli che mancavano (**Christian**: se vanno bene, aggiungile al contratto 2.2 per P46). **Giuseppe** (P47): la presenza la calcola `friend_service.presence(user_id)`; gli avvisi `friends:changed` dopo richieste, accettazioni, rimozioni e blocchi li devi mandare tu, e le funzioni di `friend_service` sono i punti in cui farlo.

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
