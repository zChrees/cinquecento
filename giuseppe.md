# Riepiloghi di Giuseppe

> **Questo file lo scrive solo Giuseppe** (Studente 1: motore e tempo reale). Lo leggono Christian e Antonio dopo il `git pull` di `dev`, per le novità utili al progetto e al loro lavoro; chi è di turno sui documenti condivisi (`SCALETTA.md`, `CLAUDE.md`, `DECISIONI.md`, `DA-DECIDERE.md`, scelto dal gruppo a fine giornata) li aggiorna da qui. Nessun altro lo modifica, nemmeno per correggere un errore: si segnala a Giuseppe.
>
> **Come si aggiorna** (regola in `CLAUDE.md`, "Consegna"): a fine punto, nel branch del punto (`feature/…`, `fix/…`), Giuseppe aggiunge il riepilogo **in cima** alla sezione "Riepiloghi", nello stesso commit del punto; così arriva in `dev` con il merge. Quando è di turno sui documenti, il riepilogo dell'aggiornamento va qui, nel branch `docs/…`. Il numero del commit non si scrive: lo si trova con `git log -- giuseppe.md`.

## Schema

```markdown
### P<numero> — <titolo> (<data>)

- **Branch**: feature/… (docs/… per un aggiornamento dei documenti condivisi)
- **File**: creati …; modificati … (se fuori elenco: perché e con l'ok di chi)
- **Controlli**: <N> PASS in tutto (<M> nuovi), `ruff check .` pulito
- **Decisioni prese**: … oppure "nessuna"
- **Domande nuove**: … oppure "nessuna"
- **Punti delicati**: …
- **Note per il contratto o per gli altri**: … oppure "nessuna"
```

## Riepiloghi

<!-- Il più recente in cima. I riepiloghi di P10–P13 li ha copiati Christian il 28/09/2026 dai messaggi di Giuseppe, senza cambiarli. -->

### P29 — Matchmaking 2v2 (28/09/2026)

Punto di Antonio, fatto da Giuseppe con il suo permesso, subito dopo P28.

- **Branch**: feature/p29-matchmaking-2v2
- **File**: creato `tests/sockets/test_matchmaking_2v2.py`; modificati `app/realtime/matchmaking.py`, `app/sockets/lobby_events.py`, `app/static/js/pages/home.js`. **Correzione del browser dei test** (commit a parte, con l'ok di Giuseppe): modificato `tests/browser.py` (di Christian, P46), creato `tests/frontend/test_avvio_browser.py`. **Fuori elenco, miei**: `tests/sockets/test_matchmaking_1v1.py` (P28: le partite trovate ora sono oggetti `Match`, tolto il controllo "2v2 non attivo") e `tests/sockets/conftest.py` (il fixture `server` restituisce anche `app`, per chiamare `matchmaker.join_pair` dai test)
- **Controlli**: **1146 PASS** in 7 suite, tutto PASS, dopo il rebase su P30 e sulla correzione di Christian del test della home di P28 (23 nuovi nella suite `sockets`, rilanciata 3 volte di fila senza errori, e 5 nella suite `frontend` per la correzione del browser dei test), `ruff check .` pulito
- **Decisioni prese**: **coda 2v2 di singoli** (chiude D17, scelta di Giuseppe sulla raccomandazione di Claude): le squadre si formano in modo che le medie delle due squadre siano il più vicine possibile.
- **Scelte tecniche**:
  - in coda ci sono **voci**: un singolo, oppure una **coppia già formata**, che gioca sempre nella stessa squadra, contro due singoli o contro un'altra coppia; il rating della coppia è la media dei due (vale per l'intervallo di `queue:status`, uguale per i due);
  - la regola "si accettano a vicenda" di P28 vale per **ogni coppia di voci** della partita: con quattro singoli servono tutti e quattro nell'intervallo di ognuno;
  - si serve prima chi aspetta da più tempo; tra le partite possibili si sceglie quella con i rating più vicini (differenza tra il più alto e il più basso), poi quella con le squadre più bilanciate, poi chi aspetta da più tempo; per ogni voce si guardano solo le 8 più vicine di rating (`CANDIDATES`), così il calcolo resta leggero (provato con 40 in coda);
  - posti: squadre e posti dentro la squadra tirati a sorte; i posti 0 e 2 sono una squadra (contratto 3.1); `rated=True` sempre (anche la coppia con l'amico, D36);
  - **`matchmaker.join_pair(app, utente, compagno, target_score, sid=None)`** fa entrare la coppia nella coda 2v2 e restituisce lo stato di `utente`; il compagno riceve `queue:status` con `partner`. Rifiuta con `busy` se uno dei due è già in coda o in partita, con `invalid_data` la coppia con sé stessi. **Non è collegata a nessun evento**: la chiamerà `invite:start` di P47;
  - se esce uno della coppia (Annulla o ultima scheda chiusa) esce tutta la coppia: lui riceve `queue:left` `"cancelled"`, il compagno `"partner_left"`;
  - pagina: "Gioca" nella Partita Veloce 2v2 usa la coda vera; con `"partner_left"` compare "Il tuo compagno è uscito dalla coda."; il 2v2 con un amico resta con i dati finti fino a P47.
- **Domande nuove**: nessuna (quella sul 2v2 con più amici invitati è nel riepilogo di P28)
- **Punti delicati**:
  - la coda tiene un indice utente → voce: i due della coppia puntano alla **stessa** voce; per toglierla si usa sempre `leave` (o `_remove`), mai il `del` di un solo utente;
  - `join_pair` va chiamata dentro Flask (serve per leggere il rating e per avviare il controllo delle code con l'app), come `create_room` (P26);
  - **errore intermittente nella suite `frontend`, corretto** (commit separato nello stesso branch, con l'ok di Giuseppe): circa un giro su cinque dava "1 errori" all'avvio del browser di un test (visto in `test_momenti_tavolo.py`). Causa: `tests/browser.py` leggeva `DevToolsActivePort` mentre Chrome lo stava ancora scrivendo, e su Windows il file bloccato dà `PermissionError`. Non dipendeva da P28 né da P29. Ora `read_devtools_port` considera il file bloccato, vuoto o incompleto come "non ancora pronto" e riprova; test nuovo `tests/frontend/test_avvio_browser.py` (5 controlli); dopo la correzione 10 giri di `frontend` su 10 senza errori.
- **Note per il contratto o per gli altri**: nessun cambiamento al contratto. **Chi fa P47** (io): `invite:start` nel 2v2 chiama `matchmaker.join_pair(current_app._get_current_object(), chi_invita, invitato, target_score, request.sid)` e risponde con lo stato che restituisce; nel 1v1 chiama `create_room(..., rated=False)`. **Christian**: oltre alla correzione del test di P28, ho toccato il tuo `tests/browser.py` (P46) per l'errore intermittente descritto sopra: solo l'attesa della porta di Chrome (`read_devtools_port`), il resto è com'era. **Antonio**: il blocco della suite `api` che avevi visto in P27 potrebbe avere la stessa origine (il browser dei test che non parte), ma non l'ho verificato [N].

### P28 — Matchmaking 1v1 (28/09/2026)

Punto di Antonio, fatto da Giuseppe con il suo permesso (anche per P29, che segue). Prima di cominciare: nessun branch di P28 su GitHub.

- **Branch**: feature/p28-matchmaking
- **File**: creati `app/realtime/matchmaking.py`, `tests/sockets/test_matchmaking_1v1.py`; modificati `app/sockets/lobby_events.py`, `app/static/js/pages/home.js`. **Non toccati**, anche se nell'elenco: `app/sockets/__init__.py` (il controllo delle code parte al primo `queue:join`, `lobby_events` era già registrato) e `ModeModal.js` ("Gioca" arrivava già a `play(...)`). **Fuori elenco, con l'ok di Giuseppe**: `app/repositories/rating_repo.py` (P27, di Antonio: una funzione di sola lettura, `get_value`), `app/sockets/connection_events.py` (P23/P25: stato della coda alla scheda nuova, uscita dalla coda con l'ultima scheda), `app/static/js/core/events.js` (P23: i nomi `QUEUE_*`), `tests/sockets/conftest.py` (il fixture `connect` accetta `before(client)`, per ascoltare gli eventi mandati appena la scheda si collega). Aggiornata anche l'intestazione di questo file con la regola dei documenti a turno, come chiesto da Christian
- **Controlli**: 1092 PASS e **1 FAIL** su 1093, in 7 suite (39 nuovi, nella suite `sockets`, rilanciati 3 volte di fila senza errori), `ruff check .` pulito. Il FAIL è `tests/api/test_pagina_home.py::test_partita_veloce_apre_e_annulla_la_coda` (P22, di Christian): vedi "Note per gli altri"
- **Decisioni prese** (scelte di Giuseppe sulle raccomandazioni di Claude):
  - **abbinamento solo se i due si accettano a vicenda**: la differenza di rating sta nell'intervallo di tutti e due, così nessuno si trova un avversario fuori da "Avversari con rating tra X e Y";
  - **chi chiude tutte le schede esce dalla coda** (`queue:left` con `"cancelled"`), così non viene abbinato a una partita a cui non arriverebbe; una scheda che si collega mentre l'utente è in coda riceve subito `queue:status`;
  - **per P29, coda 2v2 di singoli** (chiude D17): i 4 giocatori si dividono in modo che le medie delle due squadre siano il più vicine possibile.
- **Scelte tecniche**:
  - code in memoria, una per modalità e punteggio, sotto un lock unico; la logica (`MatchQueue`) non dipende da Flask e si prova con un orologio finto;
  - si serve prima chi aspetta da più tempo, con l'avversario di rating più vicino; i posti si tirano a sorte;
  - un thread prova gli abbinamenti ogni secondo e **subito dopo ogni `queue:join`**, e rimanda `queue:status` quando l'intervallo si allarga (ogni 10 secondi fino a ±400, poi `rating_range: null` dopo 2 minuti, D16); l'intervallo non scende sotto 0;
  - la partita si crea con `create_room(..., rated=True)` dentro `app.app_context()`: a fine partita si salva (P26, c'è un test);
  - `queue:join`: `request_id` da 1 a 100 caratteri, `mode` `"1v1"` o `"2v2"`, `target_score` 150, 300 o 500 (intero, non `bool`); lo stesso `request_id` riceve la stessa risposta (`RecentRequests` di P45, importato senza modificarlo); `busy` "Sei già in coda." da un'altra scheda, "Hai già una partita in corso." se è al tavolo; **`mode: "2v2"` risponde `not_allowed` "La coda 2v2 non è ancora attiva."** fino a P29;
  - `queue:status` va anche alle altre schede dello stesso utente; `queue:left` a tutte; `queue:leave` risponde `ok` anche se non era in coda;
  - rating letto a ogni `queue:join` da `rating` della modalità (1500 se manca la riga), convertendo il `Decimal`;
  - pagina: "Gioca" nella Partita Veloce 1v1 usa la coda vera **anche in sviluppo** (con i dati finti restano il 2v2 fino a P29 e gli inviti fino a P47); `game:start` porta al tavolo.
- **Domande nuove**:
  - **2v2 con più amici invitati** (per P29 e P47): Giuseppe vorrebbe "se inviti un solo amico siete in squadra insieme; se ne inviti più di uno, le squadre sono a caso". Oggi però è deciso che **si invita un amico alla volta** (D27, contratto 5.3: un secondo `invite:send` risponde `busy`). Va deciso nel gruppo se cambiarlo; se sì, cambiano il contratto e P47.
- **Punti delicati**:
  - `create_room` dalla coda gira nel thread del controllo, fuori da una richiesta: per questo il thread lavora dentro `app.app_context()`, con l'app presa al primo `queue:join`;
  - la coda non sa quali schede ha l'utente: all'uscita di una scheda `connection_events` conta quelle rimaste nel canale `user:<id>`;
  - un abbinamento la cui `create_room` fallisce (uno dei due è entrato in partita per un'altra via, P47) rimette in coda chi non è in partita, con la sua attesa;
  - i test cambiano `matchmaking.RANGE_STEP_SECONDS` con `monkeypatch` (valori letti al momento dell'uso) e a ogni prova tolgono dalla coda e dalle stanze gli utenti di prova.
- **Note per il contratto o per gli altri**: nessun cambiamento al contratto.
  - **Christian**: il test `test_partita_veloce_apre_e_annulla_la_coda` di `tests/api/test_pagina_home.py` aspetta l'intervallo dei dati finti, "tra 1340 e 1740", ma ora la home entra nella coda vera: l'utente di prova non ha rating (1500), quindi il server manda "tra 1400 e 1600". **Proposta**: nella riga 358 cambiare `"tra 1340 e 1740"` in `"tra 1400 e 1600"`; con questo cambiamento il test passa tutto, compreso Esc che annulla la coda vera (provato con una copia temporanea, poi cancellata). Non l'ho toccato perché il file è tuo: **ci dai l'ok per cambiarlo noi, o lo cambi tu?** In più la schermata di coda si ridisegna a ogni `queue:status` (ogni 10 secondi, per l'intervallo nuovo), quindi le carte che si mescolano ripartono: se vuoi evitarlo, un `setQueueRange(overlay, range)` in `QueueOverlay.js` basterebbe;
  - **Antonio**: `rating_repo.get_value(user_id, mode)` (float o `None`) è di sola lettura, senza blocchi; P29 lo faccio io, sugli stessi file;
  - **tutti**: il `request_id` della home è un codice casuale di 32 cifre esadecimali (`getRandomValues`), uno per clic su "Gioca".

### P55 — Frasi del tavolo in tempo reale (28/09/2026)

- **Branch**: feature/p55-frasi
- **File**: creati `app/realtime/table_phrases.py`, `tests/sockets/test_frasi_tavolo.py`; modificati `app/sockets/game_events.py`, `config.py` (una chiave, `TABLE_PHRASE_MIN_INTERVAL_SECONDS = 3`). **Fuori elenco, con l'ok di Giuseppe**: `app/realtime/room.py` (un solo campo, `phrase_times`, e una riga nella descrizione) e `tests/sockets/test_partita.py` (P24: il fixture `users` registra "Quarto" solo se non c'è, come quello di P25; senza, con il file nuovo che gira prima, 28 test davano errore)
- **Controlli**: 1054 PASS in tutto, in 7 suite (23 nuovi, nella suite `sockets`), `ruff check .` pulito
- **Decisioni prese**: nessuna sul gioco. Scelte tecniche:
  - elenco delle 19 frasi di D24 in `table_phrases.PHRASES` (codice → testo, nell'ordine di D24), unico: la pagina lo riceve con `game:phrases`;
  - `game:join` manda `game:phrases` a chi entra **prima** di `game:state` (contratto 3.2), a ogni ingresso;
  - `game:send_phrase` `{game_id, code}`: sotto il lock della stanza; solo dalla scheda al tavolo (D14), altrimenti `not_allowed`; codice fuori elenco `invalid_data` "Frase non valida."; poi `game:phrase` `{seat, code}` a tutti al tavolo, anche a chi l'ha mandata e agli avversari nel 2v2;
  - limite per giocatore: `too_fast` con `retry_after` in **secondi interi arrotondati per eccesso** (3 subito dopo una frase); un rifiuto non conta per il limite;
  - **le frasi si possono mandare anche a partita finita** ("Bella partita!"), finché la stanza esiste;
  - l'ora dell'ultima frase sta nella stanza (`room.phrase_times`, `time.monotonic`), mai il testo; codice e testo non vanno nel log né nel database (c'è un test).
- **Domande nuove**: nessuna
- **Punti delicati**:
  - il limite si legge da `table_phrases.MIN_INTERVAL_SECONDS` al momento della frase: i test lo riducono con `monkeypatch`, senza cambiare `config.py`;
  - più file della suite `sockets` registrano l'utente "Quarto": ogni fixture deve registrarlo **solo se non c'è**.
- **Note per il contratto o per gli altri**: nessun cambiamento al contratto. **Christian** (P56): l'elenco arriva con `game:phrases` a ogni `game:join` (anche al rientro); `game:phrase` porta `seat` e `code`, il testo si prende dall'elenco; `retry_after` è in secondi interi. Il pulsante resta disattivato 3 secondi dopo l'invio; se arriva comunque `too_fast`, `retry_after` dice quanto aspettare

### Correzione — Test instabile di P25 ed eventi di gioco senza dati (28/09/2026)

- **Branch**: fix/p25-timer-e-dati
- **File**: modificati `app/sockets/game_events.py` (P24), `tests/sockets/test_timer_riconnessione.py` (P25), `tests/sockets/test_partita.py` (P24). Nessun file fuori elenco; `room.py` non toccato
- **Controlli**: 1031 PASS in tutto, in 7 suite (3 nuovi, nella suite `sockets`), `ruff check .` pulito. Il test instabile: prima 1 fallimento su 15 giri, dopo la correzione 0 su 20
- **Decisioni prese**: nessuna
- **Domande nuove**: nessuna
- **Cosa è cambiato**:
  - **test instabile** `test_turno_scaduto_il_server_gioca_la_mossa_automatica`: l'errore era nel test, non nel server. Con il turno da 0,3 s già alla creazione della stanza, le mosse automatiche partivano mentre i client si collegavano (è giusto così: chi non è seduto riceve la mossa automatica, scelta di P25). Se alla prima vista il turno era di chi risponde, la sua carta chiudeva la presa e finiva in `last_trick`, senza comparire mai in `trick`: il test aspettava 5 secondi e falliva (l'ipotesi di Christian era giusta). Ora i giocatori si siedono con un turno di 30 s, poi il test porta il turno a 0,3 s e fa ripartire il timer sotto il lock della stanza (`shorten_turn`);
  - **`on_join`, `on_play_card`, `on_sing`** hanno `data=None`, come `on_leave`: un evento senza dati risponde `invalid_data` invece di `server_error` (correzione proposta da Antonio in P25; test nuovo `test_evento_senza_dati_rifiutato`).
- **Punti delicati**: nei test con il turno corto, le viste arrivate **prima** del timer possono contenere già mosse automatiche; la carta che chiude una presa si vede solo in `last_trick`. Gli altri due test di P25 con il turno corto lo tengono già in conto
- **Note per il contratto o per gli altri**: nessun cambiamento al contratto. **Christian**: il test di P25 che falliva sul tuo PC è corretto; il numero dei controlli è 1031

### P24 — Stanze e partita completa (28/09/2026)

- **Branch**: feature/p24-partita (la parte server è partita prima che P21 fosse in `dev`; `game.js` l'ho toccato solo dopo, con P21 in `dev`)
- **File**: modificati app/realtime/room.py, room_manager.py (P23), app/sockets/game_events.py (P4), app/static/js/pages/game.js (P21); creato tests/sockets/test_partita.py
- **Controlli**: 790 PASS in tutto (29 nuovi, nella suite `sockets`), `ruff check .` pulito. Provato anche una volta in Chrome senza finestra (script fuori dal progetto): il tavolo si disegna dalla partita vera, un clic su una carta arriva al server e l'avversario riceve la vista nuova, D14 mostra "partita aperta in un'altra scheda"
- **Decisioni prese** (tecniche, nessuna sul gioco):
  - `create_room(giocatori, modalità, punteggio, rated=True)` in `room_manager.py`: i giocatori si passano **nell'ordine dei posti** (nel 2v2 i posti 0 e 2 sono una squadra, contratto 3.1), come `User` o `Player`; rifiuta con `RoomError` modalità, numero di giocatori, punteggio non validi, lo stesso utente due volte e chi è già in una partita in corso. Manda `game:start` a ogni giocatore (`url` = `/game/<game_id>`);
  - `find_room_of_user(user_id)`: la stanza della partita **in corso** di quell'utente, o `None`;
  - `version` parte da 1 e sale a ogni mossa e a ogni cambio della scheda al tavolo; `turn.seconds_left` si calcola da quando è cominciato il turno (il timer che gioca da solo è di P25); `connected` = il posto ha una scheda al tavolo; `reconnect_seconds_left` sempre `null` fino a P25;
  - D14: ogni posto ha una sola scheda al tavolo, l'ultima che ha fatto `game:join`; la precedente riceve `game:replaced` e le sue mosse ricevono `not_allowed`, come quelle di chi non ha fatto `game:join`;
  - `game:sang` porta Re (rank 10) e Cavallo (rank 9) del seme, `show_seconds` 3 (D15).
- **Domande nuove**: nessuna
- **Punti delicati**:
  - **mai due `create_app()` nello stesso processo con il tempo reale acceso**: `socketio` è un oggetto unico e si ricollega all'ultima app, così il server già avviato non riceve più gli eventi giusti (successo nei test: ogni evento rispondeva `('', 400)`);
  - ordine dei controlli di una mossa: dati → partita e posto → scheda al tavolo → `version` → motore (`not_your_turn`, `illegal_move`); con `stale_state` la pagina riceve anche la vista attuale;
  - la vista si confronta nei test con le chiavi di `app/static/dev/vista_1v1.json`: se il contratto cambia, quel test lo segnala;
  - le viste di `game:state` partono dentro il gestore, prima della risposta: la pagina può ricevere `game:state` prima dell'`ok` di `game:join` (per l'ordine vale `version`).
- **Note per gli altri**:
  - **Antonio** (P28, P29) e **Giuseppe** (P47): per creare una partita `create_room(...)`; **P44**: `find_room_of_user(...)`. Tutte e due in `app/realtime/room_manager.py`, senza modificarlo;
  - **`game.js`** (P24): in prova (`?demo=`) non si collega al server; in partita fa `game:join` a ogni collegamento (anche dopo una riconnessione), chiama `render(vista)` a ogni `game:state` (ignorando le viste con `version` più vecchia), manda le mosse con la `version` della vista e, finché non arriva la risposta, disegna la vista con `legal` vuoto (carte e "Canta" disattivati); un errore va nella riga di stato (`setStatus`); `game:sang` scrive "X ha cantato 40 a coppe" per 3 secondi; con `game:replaced` il tavolo si ferma con un messaggio;
  - **Christian**: restano da disegnare (P25 o un punto dell'interfaccia) l'ultima presa per un momento, il riepilogo di fine mano e le due carte del canto per 3 secondi: per ora il canto è solo una scritta. "Esci" torna alla home senza `game:leave`: l'abbandono è di P25.

### P23 — Collegamento in tempo reale (28/09/2026)

- **Branch**: feature/p23-realtime
- **File**: creati app/realtime/events.py, room.py, room_manager.py, app/static/js/core/socket.js, events.js, app/static/js/vendor/socket.io.min.js, tests/sockets/conftest.py, test_connessione.py, test_lock_stanza.py; modificato app/sockets/connection_events.py. `app/sockets/__init__.py` era nell'elenco ma non è servito toccarlo.
- **Controlli**: 748 PASS in tutto (12 nuovi, nella suite nuova `sockets`; conteggio dopo P20 di Christian), `ruff check .` pulito
- **Decisioni prese** (tecniche, nessuna sul gioco):
  - client Socket.IO **4.8.1**, versione "ES module" (`socket.io.esm.min.js` di jsDelivr), salvata con il nome dell'elenco, `vendor/socket.io.min.js`: così `core/socket.js` la importa e la pagina resta con un solo script (regola di P19). In cima al file: versione, origine e SHA-256 dell'originale;
  - ogni scheda collegata entra nel canale `user:<id>` (tutte le schede di un utente) e le stanze di gioco usano il canale `room:<game_id>`; `game_id` è un codice casuale di 12 caratteri (`secrets.token_urlsafe`);
  - D14 ("l'ultima scheda prende il posto", `game:replaced`) scatta con `game:join`, quindi la fa P24;
  - `events.py` ha la forma unica delle risposte (`ok`, `error`, il decoratore `handler` e `EventError` con i soli codici del contratto): un errore imprevisto diventa `server_error` e il dettaglio va solo nel log;
  - `socket.js`: `send()` non manda niente senza connessione e risponde subito con `{ok: false, error: {code: "no_connection", ...}}`; è un codice **solo della pagina**, non del server, quindi non è nella tabella del contratto.
- **Domande nuove**: nessuna
- **Punti delicati**:
  - ogni evento di una stanza passa da `room.run(...)` (lock della stanza, rientrante): il test manda 50 azioni insieme da 5 client e controlla che nel lock ne entri una alla volta; togliendo il lock il contatore arriva a 5 invece di 50 (provato);
  - la suite `sockets` avvia un server vero sulla porta 5099 in un thread e fa il login via HTTP con il codice CSRF; vuole MySQL;
  - il server di sviluppo (Werkzeug) non risponde alla chiusura ordinata del websocket: il client Python la aspetta 3 secondi per connessione (la suite ci metteva 42 s). Nei test l'attesa è accorciata a 0,1 s; il browser non aspetta quella risposta [D].
- **Note per gli altri**: le pagine che usano il tempo reale importano `core/socket.js` (`connect`, `send`, `on`, `onStatus`) e i nomi da `core/events.js`. P24 (Giuseppe) attende P21 di Christian.

### Correzione di migrate.py quando MySQL rifiuta la connessione (28/09/2026)

- **Branch**: fix/migrate-connessione (era "Da assegnare" in `SCALETTA.md`)
- **File**: modificato scripts/migrate.py (`main`); creato tests/db/test_migrate_connessione.py, file nuovo per non toccare `test_migrate.py` di P5
- **Controlli**: 719 PASS in tutto (2 nuovi, in `db`), `ruff check .` pulito
- **Decisioni prese**: nessuna. `engine.raw_connection()` lancia l'errore di PyMySQL così com'è, mentre `main` aspettava solo quello di SQLAlchemy: ora li prende tutti e due e stampa il suo messaggio con il codice di MySQL.
- **Domande nuove**: nessuna
- **Punti delicati**: il test prova password sbagliata (errore 1045, vuole MySQL acceso) e porta senza MySQL (2003), con la configurazione dei test; controlla che non ci sia traceback e che la password non compaia nel messaggio.
- **Note per gli altri**: nessuna

### P16 — Registrazione, login, logout: la logica (28/09/2026)

Punto di Antonio, fatto da Giuseppe con il suo permesso. È la parte di logica; la grafica di `login.html` e `register.html` si rifinisce dopo, sempre da Giuseppe.

- **Branch**: feature/p16-auth (partito prima che P7 fosse in `dev`, con l'ok di Giuseppe: P16 non tocca i file di P7)
- **File**: creati app/blueprints/auth/forms.py, app/services/auth_service.py, app/repositories/user_repo.py, app/templates/auth/login.html, app/templates/auth/register.html (versione di base, con le classi di P19), tests/api/test_auth.py; modificato app/blueprints/auth/routes.py. Nessun file fuori elenco.
- **Controlli**: 717 PASS in tutto (30 nuovi, in `api`), `ruff check .` pulito
- **Decisioni prese** (raccomandazioni di Claude, accettate da Giuseppe):
  - login **solo con lo username** (non con l'email); dopo la registrazione si entra subito e si torna alla home con "Benvenuto, *username*!";
  - **troppi tentativi**: contati **per username, in memoria**; dopo `LOGIN_MAX_ATTEMPTS` (5) errori, per `LOGIN_LOCK_SECONDS` (300) quello username non entra nemmeno con la password giusta ("Troppi tentativi sbagliati: riprova tra qualche minuto."); il conteggio si azzera con un login riuscito, dopo 5 minuti senza errori o al riavvio del server. Nessuna colonna nuova;
  - password e username sbagliati danno lo **stesso messaggio** ("Username o password non corretti."), e con uno username inesistente si calcola comunque un hash, così nemmeno il tempo di risposta dice se l'account esiste;
  - D8 usata com'è in `config.py` (almeno 8 caratteri): resta provvisoria in `DA-DECIDERE.md`.
- **Domande nuove**: nessuna
- **Punti delicati**:
  - username o email già usati li rifiuta il vincolo unico di MySQL al commit (`uq_utenti_nome`, `uq_utenti_email`), non un controllo fatto prima: così due registrazioni contemporanee non creano doppioni. L'email è unica senza distinguere le maiuscole (collation della colonna), lo username le distingue (D7);
  - il vero `user_loader` di Flask-Login si registra in `auth/routes.py` e sostituisce il segnaposto di `extensions.py`;
  - dopo il login si torna alla pagina chiesta (`?next=`) solo se è un indirizzo di questo sito (niente `//altro-sito`);
  - `/auth/logout` accetta solo POST con il codice CSRF, come il modulo "Esci" di P40; i moduli senza codice CSRF sono rifiutati (400);
  - le password sono hash `scrypt` di werkzeug; nei log non finiscono mai password né username (c'è un test).
- **Note per gli altri**:
  - **Christian**: le pagine di accesso e registrazione non hanno ancora uno script di pagina, quindi la navbar lì non si apre (serve `core/layout.js` con `initLayout()`, come dice il riepilogo di P40). Lo aggiungiamo con la grafica delle due pagine; il file (`js/pages/auth.js` o simile) non è nell'elenco di P16, va concordato;
  - **Antonio**: P16 è fatto (resta la grafica); P17 ha `auth_service` e `user_repo` da estendere. La suite `api` ora richiede MySQL (`test_auth.py`);
  - P23 (Giuseppe) può partire: attendeva P16.

### Correzione del controllo di MySQL all'avvio (28/09/2026)

- **Branch**: fix/checks-database
- **File**: modificati app/checks.py (riga 39), tests/api/test_avvio.py (1 test nuovo)
- **Controlli**: 672 PASS in tutto (1 nuovo), `ruff check .` pulito
- **Decisioni prese**: nessuna. È il bug segnalato da Christian nel riepilogo di P5: `url.set(database=None)` non toglie il database, perché `set()` ignora i valori `None`, quindi il controllo di `run.py` si collegava già a `DB_NAME` e, se il database non esisteva, dava il messaggio sbagliato. Ora è `url._replace(database=None)`.
- **Domande nuove**: nessuna
- **Punti delicati**: il test sostituisce `create_engine` con una funzione finta e controlla che riceva l'indirizzo senza database, con utente, password, host, porta e charset invariati; non serve MySQL. Provato anche a mano sul MySQL vero: con un `DB_NAME` inesistente il controllo di versione ora passa, e l'errore sul database arriverà dopo, con il suo messaggio.
- **Note per il contratto o per gli altri**: nessuna

### P6 — Runner dei test (28/09/2026)

- **Branch**: feature/p6-runner
- **File**: creati tests/esegui_tutti.py, tests/conftest.py, tests/runner/test_esegui_tutti.py
- **Controlli**: 671 PASS in tutto (13 nuovi), `ruff check .` pulito; giro completo con `python tests/esegui_tutti.py` in 24 s
- **Decisioni prese**: nessuna sul gioco. Scelte tecniche: tempo massimo 120 s per suite (oggi la più lenta, engine, ci mette 6 s); le suite sono le cartelle di tests/ con almeno un test_*.py, nell'ordine runner, engine, db, api, services, sockets, frontend, e2e, poi le altre in ordine alfabetico; `python tests/esegui_tutti.py engine db` lancia solo quelle. Codici d'uscita: 0 tutto PASS, 1 almeno un FAIL, 2 rifiuto prima di partire. Un file **nuovo** tra quelli protetti (per esempio una `migrations/002_….sql` comparsa durante i test) si segnala ma non si cancella, perché potrebbe essere lavoro vero; quelli modificati o cancellati si ripristinano dopo ogni suite, con controllo dell'hash.
- **Domande nuove**: nessuna
- **Punti delicati**: `tests/conftest.py` ripete i rifiuti (PRODUZIONE, database che non finisce con _test) anche per chi lancia `pytest` a mano, e imposta `APP_ENV=testing` per tutti i test. Una suite che supera il tempo si ferma con tutti i processi che ha avviato (`taskkill /T`), così un server di test rimasto appeso non occupa la porta 5099. Se MySQL non risponde, la pulizia finale del database lo scrive nel riepilogo ma non cambia l'esito.
- **Note per il contratto o per gli altri**: P7 e P18 (Antonio) possono partire. Da ora il comando dei test è `python tests/esegui_tutti.py` (il "Finché P6 non c'è" di CLAUDE.md si può togliere; il numero di controlli diventa 671). Trovato fuori dal punto: `scripts/migrate.py` (P5), se MySQL rifiuta utente o password, esce con un traceback invece del suo messaggio in italiano, perché `engine.raw_connection()` lancia l'errore di PyMySQL e non quello di SQLAlchemy che il `main` aspetta; da correggere su un branch `fix/…` di chi decide Christian.

### P15 — Vista per giocatore, mosse legali, mossa automatica (28/09/2026)

- **Branch**: feature/p15-viste
- **File**: creati app/game/engine/views.py, auto_move.py, tests/engine/test_viste.py, tests/engine/test_mossa_automatica.py
- **Controlli**: 603 PASS in tutto (70 nuovi), `ruff check .` pulito
- **Decisioni prese**: nessuna sul gioco (applicata D12). Scelta tecnica: il motore non conosce la stanza, quindi `player_view(partita, posto)` produce tutti i campi di gioco del contratto (3.3) con i nomi e la forma di `vista_*.json`, e la stanza (P24/P25) aggiunge i suoi: `game_id`, `version`, `rated`; per ogni giocatore `user_id`, `username`, `avatar`, `connected`, `reconnect_seconds_left`; nel turno `seconds_total`, `seconds_left`. Sono elencati in `ROOM_FIELDS`, `ROOM_PLAYER_FIELDS` e `ROOM_TURN_FIELDS` di views.py. Il `result` del motore ha sempre `reason: "score"` e `abandoned_seats: []`: l'abbandono lo scrive la stanza. La mossa automatica è `auto_move(partita, rng)` e restituisce la carta per chi è di turno.
- **Domande nuove**: nessuna
- **Punti delicati**: un test prova tutte le posizioni di 10 partite intere, per ogni posto, e controlla che nella vista ci siano solo le carte in mano a quel posto, la presa in corso e l'ultima presa chiusa. `legal` si confronta con le mosse che `apply_game` accetta davvero (40 carte e 4 semi per ogni posto e posizione). Nella mossa automatica i punti contano prima della briscola: il 2 di briscola si gioca prima dell'Asso di un altro seme.
- **Note per il contratto o per gli altri**: la carta nella vista è `{"suit", "rank"}` (`card_to_dict`). Per le azioni che arrivano dalla pagina (`game:play_card`), la conversione inversa da `{"suit", "rank"}` a carta, con il rifiuto dei valori non validi, la farà P24. `last_hand.hand_number` si ricava da `hand_number` (a partita finita è la mano in corso, altrimenti quella prima).

### P14 — Partita fino al punteggio scelto (28/09/2026)

- **Branch**: feature/p14-partita
- **File**: creati tests/engine/test_partita.py; modificati app/game/engine/state.py (GameState, GameResult), app/game/engine/game.py (new_game, apply_game, game_legal_actions)
- **Controlli**: 533 PASS in tutto (108 nuovi), `ruff check .` pulito
- **Decisioni prese**: nessuna sul gioco (applicata D11). Scelte tecniche: le funzioni della mano (apply, legal_actions) restano com'erano e la partita le usa; a fine mano, se nessuno ha vinto, la mano dopo comincia subito con il mazzo mescolato di nuovo (la pausa per mostrare il riepilogo spetta alla stanza, P24); il mazziere non si salva, si ricava: `dealer_seat = (first_seat - 1) % n`. L'abbandono (`reason: "abandon"` del contratto) resta a P24/P25: P14 fa solo la fine per punteggio.
- **Domande nuove**: nessuna
- **Punti delicati**: il punteggio si controlla solo a fine mano; un canto che porta a N durante la mano non la chiude (c'è un test). A partita finita `hand` resta l'ultima mano, finita, e ogni mossa viene rifiutata con "La partita è finita.". Un punteggio diverso da 150, 300 o 500 (anche `True` o `"300"`) viene rifiutato con "Punteggio non valido: si gioca a 150, 300 o 500.".
- **Note per il contratto o per gli altri**: i campi di GameState corrispondono a quelli della vista (`hand_number`, `dealer_seat`, `scores`, `last_hand`, `result.winner_team` con None per il pareggio): P15 li userà direttamente.

### P13 — Svolgimento di una mano (28/09/2026)

- **Commit**: 448da13, in dev e su GitHub (fast-forward, niente rebase)
- **File**: creati app/game/engine/actions.py, state.py, game.py, tests/engine/test_mano.py
- **Controlli**: 412 PASS (129 + 283 nuovi: le mani intere si provano con 100 semi fissi per modalità), ruff check . pulito
- **Decisioni prese**: nessuna sul gioco. Correzione a quanto ti avevo scritto sul contratto: il contatore version non sta nello stato del motore ma nella stanza (P24/P25), perché secondo il contratto deve salire anche per scollegamenti e rientri, che il motore non conosce. Il contratto non cambia.
- **Note tecniche**: legal_actions(stato, posto) sta in game.py, come chiede CLAUDE.md, e P15 la userà per legal. La squadra di un posto è posto % 2. new_hand riceve un mazzo già mescolato e chi comincia: mescolare e applicare D11 spetta a P14.
- **Domande nuove**: nessuna
- **Punti delicati**: dopo un canto il turno resta a chi ha cantato, che deve ancora giocare la carta. Un test prova tutte le 40 carte e i 4 semi su ogni posizione di 20 mani e controlla che le mosse legali siano esattamente quelle accettate da apply.

### P12 — Cantare 40 e 20 (28/09/2026)

- **Commit**: b5d7123, in dev e su GitHub (fast-forward, niente rebase)
- **File**: creati app/game/engine/singing.py, tests/engine/test_canti.py. Modificato fuori elenco, con il mio ok: app/game/engine/errors.py. Ho aggiunto NotYourTurnError, un caso particolare di InvalidMoveError, così il server (P24) può rispondere not_your_turn invece di illegal_move, come chiede il contratto (1.2). È un file mio (P10) e nessun altro lo tocca.
- **Controlli**: 129 PASS (106 + 23 nuovi), ruff check . pulito
- **Decisioni prese**: nessuna nuova ("un seme alla volta" è già in DECISIONI.md). Nota tecnica: i canti della mano sono un elenco Sing(seat, suit, points), nella stessa forma di sings nella vista. La briscola è il seme del primo canto e si ricava dall'elenco, senza salvarla a parte.
- **Domande nuove**: nessuna
- **Punti delicati**: il 40 è il primo canto della mano di chiunque, non di ciascun giocatore. Il controllo "Re o Cavallo già giocato" non cambia mai l'esito da solo, perché senza quella carta la coppia manca comunque, ma dà il messaggio giusto. Una prova su 3.000 situazioni controlla che singable_suits (per legal.sing) e sing diano sempre la stessa risposta.

### P11 — Chi vince la presa (28/09/2026)

- **Commit**: 121aea7 sul branch feature/p11-presa
- **File**: creati app/game/engine/trick.py, tests/engine/test_presa.py
- **Controlli**: 106 PASS (76 + 30 nuovi), ruff check . pulito
- **Decisioni prese**: nessuna. Nota tecnica: trick_winner(carte, briscola) restituisce la posizione della carta vincente nell'ordine di gioco (0 = chi ha aperto); sarà P13 a trasformarla nel giocatore.
- **Domande nuove**: nessuna
- **Punti delicati**: le carte di un seme diverso da quello di uscita e dalla briscola non prendono mai, nemmeno l'Asso. I test controllano tutte le coppie di carte e 2.000 prese da 4 carte.

### P10 — Carte, mazzo, parametri delle regole (28/09/2026)

- **Commit**: 3052632, in dev e su GitHub (rebase su b8db176, poi fast-forward)
- **File**: creati app/game/engine/cards.py, deck.py, rules.py, errors.py, tests/engine/test_carte_mazzo.py
- **Controlli**: 76 PASS (31 + 45 nuovi), ruff check . pulito
- **Decisioni prese**: nessuna nuova. Nota tecnica: i punteggi 150/300/500 sono sia in config.py sia in RuleSet, perché il motore non può importare config.py; un test controlla che restino uguali.
- **Domande nuove**: nessuna
- **Punti delicati**: i codici delle carte ("denari-1") si confrontano in modo esatto, e ogni codice diverso viene rifiutato con "Carta non valida." (serve per le azioni che arrivano dal client). C'è un test che impedisce al motore di importare Flask, il database o config.py.
