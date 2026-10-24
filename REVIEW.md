# Code review indipendente (P36)

> **Tracker attivo** dal 11/10/2026 (P37): la scaletta è archiviata in `docs/archivio/SCALETTA-2026-09.md`. Lo stato di ogni finding e i punti ancora aperti della scaletta (P38) sono in fondo, in "Stato e punti aperti". Lo aggiorna chi è di turno sui documenti, come prima la scaletta.

> 11/10/2026. I finding sono stati scritti **prima** di leggere `DECISIONI.md`; poi sono stati confrontati con le decisioni (sezione "Confronto con DECISIONI.md"): quelli che ne contraddicono una sono segnati "rischio residuo", senza riproporre le soluzioni scartate. La review non ha modificato il codice.

Legenda dell'evidenza: **[T]** verificato con una prova · **[L]** letto nel codice · **[D]** dedotto · **[N]** non verificabile.
Gravità: critico, alto, medio, basso.

## Riepilogo

- **Critici e alti**: nessuno.
- **Medi**: R1 (username con a-capo), R2 (rischio residuo), R3 (in parte rischio residuo).
- **Bassi**: R4–R16 (R5, R10 e R12 rischi residui).
- Ambito: motore e regole, viste, tempo reale, socket e rotte, servizi e repository, migrazione, script di backup, sicurezza delle pagine (ricerca dei punti in cui il testo potrebbe diventare HTML), protezioni dei test. Non riletti riga per riga: la strategia della CPU (`cpu.py`, salvo cosa legge), i CSS e il disegno del tavolo in `game.js`.

## Finding

### R1 — medio — Username ed email accettano un a-capo finale [T] · fatto (P137)

- **Dove**: `app/blueprints/auth/forms.py:326` (`Regexp(r"^[A-Za-z0-9_]+$")`), `:331` (email); `migrations/001_init.sql:63` (`ck_utenti_nome`).
- **Cosa**: in Python `$` vale anche prima di un a-capo finale, e `Regexp` di WTForms usa `re.match`. Il `CHECK` di MySQL (`REGEXP_LIKE`, ICU) fa lo stesso. Il campo non toglie gli spazi.
- **Prova**: `re.match(r"^[A-Za-z0-9_]+$", "Mario\n")` → trovato; su MySQL 8.0 `REGEXP_LIKE('Mario\n', '^[A-Za-z0-9_]{3,20}$', 'c')` = 1, e anche con `"Mario\r\n"`. Un `POST /auth/register` con `username="Revis\n"` (client di prova di Flask) ha passato il modulo ed è arrivato all'`INSERT`.
- **Scenario**: con una richiesta scritta a mano (non dal modulo della pagina) qualcuno registra `Mario\n`. La collation `utf8mb4_0900_as_cs` è NO PAD, quindi è diverso da `Mario`, ma nelle pagine si vede come "Mario": in chat, al tavolo, nelle richieste di amicizia. È un modo per farsi passare per un altro.
- **Correzione**: `\Z` al posto di `$` (o `fullmatch`) nelle due regole del modulo; un test con `"Mario\n"` e `"a@b.it\n"`. Il `CHECK` del database non si può cambiare in `001_init.sql` (migrazione già applicata): servirebbe una `002_…sql` con `'^[A-Za-z0-9_]{3,20}\\z'`, da concordare (DECISIONI, 28/09: "nella prima versione non sono previste altre migrazioni"). La correzione del modulo da sola basta, perché tutte le registrazioni passano da lì.
- **Decisioni**: nessuna in contrasto; è un difetto dell'attuazione di D7 (solo lettere, numeri e `_`).
- **File**: `app/blueprints/auth/forms.py`, `tests/api/test_auth.py`; facoltativo `migrations/002_….sql`.

### R2 — medio — Chi non arriva mai al tavolo non ha limite di tempo [L] · rischio residuo, poi fatto (P138)

- **Dove**: `app/realtime/room.py:17-19`, `:506-522` (il conto alla rovescia parte solo da `disconnect`, cioè per chi era seduto).
- **Scenario**: la coda abbina due giocatori; uno chiude la scheda proprio in quel momento e non fa mai `game:join`. L'altro gioca tutta la partita (fino a 500 punti) contro le mosse automatiche, 15 s a turno, oppure preme "Esci" e **perde per abbandono**, con il rating che scende a lui e non a chi è sparito.
- **Decisione**: è la scelta di Antonio del 28/09/2026 (P25, opzione b; scartati i 60 secondi dall'inizio). Resta da sapere, per la demo, che chi preme "Esci" in quel caso perde rating.
- **Correzione**: nessuna proposta nuova; se il gruppo vuole riaprirla, si riparte dalla decisione del 28/09.
- **File**: —

### R3 — medio — Suite dei test vicine al limite di 240 s [L] · in parte rischio residuo, poi fatto (P139)

- **Dove**: `tests/esegui_tutti.py` (`SUITE_TIMEOUT`); misure nei riepiloghi del 10/10: `table3` 226 s, `frontend` 206 s.
- **Scenario**: con il PC un po' carico una suite supera il limite e il giro risulta FAIL senza un difetto vero; con il tempo si smette di fidarsi del rosso. In `frontend` c'è anche un blocco raro in `test_banner_connessione.py` (circa 1 giro su 10).
- **Decisione**: il limite di 240 s è deciso (29/09) e "non cambia" (P121, 06/10): alzarlo non si ripropone.
- **Correzione**: dividere `table3` e `frontend` come si è fatto con `table2` e `table3` (P114, P121); cercare la causa del blocco (il collegamento lasciato a metà di P58).
- **File**: file spostati in una suite nuova (`tests/table4/`, `tests/frontend2/` o simili); il runner le trova da solo.

### R4 — basso — Le stanze finite non si tolgono mai dalla memoria [L]

- **Dove**: `app/realtime/room_manager.py:108` (`remove`, chiamata solo dai test).
- **Scenario**: ogni partita, anche contro la CPU, resta nel dizionario con partita, mosse e lock. `_room_of` e `rooms_of` le scorrono tutte a ogni `create_room`, `queue:join`, `home:status` e scollegamento. Con meno di 50 persone non si nota, ma la memoria cresce finché il server non si riavvia.
- **Correzione**: togliere la stanza qualche minuto dopo la fine (il tempo di vedere il risultato), per esempio con un timer avviato in `_save`.
- **File**: `app/realtime/room.py`, `app/realtime/room_manager.py`, un test in `tests/sockets/`.

### R5 — basso — `legal.lay_down` rivela qualcosa delle carte nascoste [D] · rischio residuo

- **Dove**: `app/game/engine/lay_down.py:27-39`, `app/game/engine/views.py:237`.
- **Scenario**: il server calcola "puoi calare" conoscendo le mani di tutti. Nel 2v2 a mazzo finito, `lay_down` vero o falso dice a chi apre se gli avversari hanno o no una carta che rompe il conto, cioè qualcosa sulla loro mano che non potrebbe sapere (nel 1v1 a mazzo finito le carte dell'avversario si ricavano comunque). Anche la CPU lo legge (`cpu.py:96`).
- **Decisione**: è la regola di "Cala le carte" (01/10 e D45 del 04/10): il pulsante compare solo quando si può calare e "il controllo lo fa il server, che conosce le carte di tutti". È una conseguenza voluta della regola.
- **Correzione**: nessuna; va solo saputo (per esempio nella relazione).
- **File**: —

### R6 — basso — Il salvataggio della partita non riprova e blocca la stanza [L]

- **Dove**: `app/realtime/room.py:552-568`.
- **Scenario**: se MySQL non risponde a fine partita, partita, mosse e rating si perdono (resta solo la riga nel log). Il salvataggio gira sotto il lock della stanza: finché MySQL non risponde, i giocatori di quella stanza non ricevono risposte (né le frasi del tavolo né la vista finale).
- **Correzione**: un secondo tentativo dopo qualche secondo, fuori dal lock, con la copia del `MatchRecord`.
- **Decisioni**: non contraddice "le partite si salvano tutte insieme a fine partita" (28/09); il rischio accettato lì è il server che si spegne durante la partita, non MySQL che non risponde alla fine.
- **File**: `app/realtime/room.py`, un test in `tests/services/`.

### R7 — basso — Coda, CPU e inviti: controlli fuori dallo stesso lock [D]

- **Dove**: `app/realtime/matchmaking.py:348` (`queue:join` guarda le partite ma non gli inviti e non prende `invites.lock`); `app/sockets/lobby_events.py:96-104` e `friends_events.py:174-200` prendono `invites.lock`.
- **Scenario**: due schede dello stesso utente mandano insieme `cpu:start` e `queue:join`: l'utente può finire in coda e in partita. Quando la coda lo abbina, `create_room` rifiuta, gli altri tornano in coda, ma la sua voce sparisce senza `queue:left` (`matchmaking.py:410-412`). Allo stesso modo `queue:join` riesce con un invito aperto.
- **Correzione**: `queue:join` sotto `invites.lock`, con il controllo degli inviti aperti; nel ramo `RoomError` mandare `queue:left` a chi non torna in coda.
- **File**: `app/realtime/matchmaking.py`, `app/sockets/lobby_events.py`, test in `tests/sockets/`.

### R8 — basso — Il cookie di sessione non è `Secure` con ngrok [L]

- **Dove**: `config.py:43-45`.
- **Scenario**: con ngrok la pagina è in https, ma il cookie può partire anche in http (per esempio aprendo l'indirizzo con `http://`). Con la Wi-Fi (passo 11b) si è comunque in http.
- **Correzione**: `SESSION_COOKIE_SECURE = True` nella configurazione della demo quando si usa ngrok (con una variabile del `.env`, perché con la Wi-Fi non funzionerebbe).
- **File**: `config.py`, `.env.example`, `docs/DEMO.md`.

### R9 — basso — La sessione non si può revocare [D]

- **Dove**: Flask-Login con la sessione nel cookie firmato (`app/blueprints/auth/routes.py:264-269`).
- **Scenario**: "Esci" cancella il cookie nel browser, ma una copia del cookie presa prima (per esempio da un PC condiviso) resta valida finché non cambia la `SECRET_KEY`. Non c'è un cambio password che la invalidi.
- **Correzione**: un numero di sessione nell'utente, salvato nel cookie e confrontato in `load_user` (serve una colonna, e quindi una migrazione nuova: da discutere, vedi R1); oppure accettare il rischio per la demo.
- **File**: `app/services/auth_service.py`, `app/models/user.py`, migrazione nuova.

### R10 — basso — Chiunque può bloccare il login di un altro [L] · rischio residuo

- **Dove**: `app/services/auth_service.py:136-162`.
- **Scenario**: 5 password sbagliate scritte apposta con lo username di un altro bloccano il suo account per 5 minuti, anche se poi lui scrive la password giusta.
- **Decisione**: è il comportamento deciso per P16 (28/09: "anche con la password giusta") e confermato per account da P96 (04/10), perché il blocco non si aggiri.
- **Correzione**: nessuna per la consegna.
- **File**: —

### R11 — basso — Nessun limite sulle richieste HTTP degli amici [L]

- **Dove**: `app/blueprints/friends/routes.py`; `friend_service._check_limits` conta solo gli amici accettati.
- **Scenario**: uno script manda richieste di amicizia a tutti gli username che conosce, senza limite di numero né di frequenza (il limite di P32 vale solo per gli eventi socket).
- **Correzione**: un limite di frequenza per utente sulle `POST`/`DELETE` di `/friends/`, e un massimo di richieste in attesa.
- **File**: `app/blueprints/friends/routes.py`, `app/services/friend_service.py`, `tests/api/test_amicizie.py`.

### R12 — basso — Nella demo gira il server di sviluppo di Werkzeug [L] · rischio residuo

- **Dove**: `config.py:38-41` (`ALLOW_UNSAFE_WERKZEUG = True`), `run.py:20-28`.
- **Scenario**: Werkzeug non è pensato per stare esposto in rete (lo dice il suo stesso avviso); con ngrok la pagina è raggiungibile da Internet.
- **Decisione**: Werkzeug in tutte le configurazioni (27/09), un solo processo in modalità `threading` (26/09), per meno di 50 persone.
- **Correzione**: nessuna per la consegna; da riprendere con D21 (uso pubblico).
- **File**: —

### R13 — basso — In sviluppo il debugger di Werkzeug è acceso [L] · fatto (P140)

- **Dove**: `config.py:99-101` (`DEBUG = True`), `run.py:24`.
- **Scenario**: chi avvia in sviluppo con `HOST=0.0.0.0` (per provare dal telefono) espone il debugger interattivo alla rete locale (protetto da un PIN).
- **Correzione**: una riga in `.env.example`/`README.md`: in rete usare `APP_ENV=demo`; oppure `use_debugger=False` quando `HOST` non è locale.
- **File**: `.env.example`, `README.md` (o `run.py`).

### R14 — basso — Backup sullo stesso PC e non cifrati [L] · fatto (P140)

- **Dove**: `scripts/backup.py`, `docs/DEMO.md` passo 8.
- **Scenario**: se il disco del PC della demo si rompe, si perdono database e backup insieme. I file contengono email e hash delle password in chiaro (compressi).
- **Correzione**: copiare ogni tanto l'ultimo backup su un altro supporto; nella guida, dire dove tenerli e che contengono dati personali.
- **File**: `docs/DEMO.md`.
- **Precisazione (P140)**: il passo 8 di `DEMO.md` diceva già di copiare i backup fuori dal PC (nella review non era stato visto); mancava solo l'avviso sui dati personali, aggiunto in P140.

### R15 — basso — Mancano due test [L]

- **Cosa**: (a) nessun test prova uno username o un'email con a-capo finale (`tests/api/test_auth.py:158-163` prova spazi e lettere accentate); (b) nessun test controlla che le stanze finite si tolgano (vedi R4).
- **File**: `tests/api/test_auth.py`, `tests/sockets/`.

### R16 — basso — Piccole copie e dipendenze incrociate [L]

- **Cosa**: `_is_int` in `game_events.py` e `friends_events.py`; `_user(player)` in `invites.py`, `matchmaking.py` e `friend_service.py`; il controllo di `request_id` in `lobby_events.py` e `friend_service.py`; `MODES` in `room.py`, `lobby_events.py` e `views.py`. I servizi importano il tempo reale (`auth_service`, `friend_service`) e il tempo reale importa i servizi (`room.py` → `match_service`, `room_manager.py` → `stats_service`). `pages/game.js` ha 1087 righe.
- **Rischio**: una modifica fatta in una copia e non nelle altre.
- **Correzione**: dopo la consegna, un modulo comune per i controlli dei dati in ingresso; niente da fare adesso.
- **File**: `app/realtime/events.py` (o un modulo nuovo) e i file sopra.

## Controllato e senza finding

- **Regole del motore** rispetto a `docs/REGOLE-GIOCO.md` [L]: valori e forza delle carte, presa (`winning_position`), pesca, chi comincia e mazziere, canti (prima presa, turno, Re o Cavallo giocati, 3 carte a mazzo finito, 40 poi 20), calata (condizioni, canti del compagno), carte del compagno, mossa automatica, punteggio e pareggio.
- **Viste** [L]: mai le carte degli altri, tranne quelle del compagno quando lo dice `partner_cards_visible`; carte prese visibili solo come punti.
- **Concorrenza** [L]: ogni evento della stanza sotto il suo lock; timer e CPU con il numero di turno; `version` per le mosse vecchie; ultima scheda al tavolo (D14); amicizie e chat con le righe degli utenti bloccate in ordine e in READ COMMITTED.
- **Sicurezza** [L]: CSP rigorosa, CSRF su moduli e JSON, `next` controllato, password con scrypt e risposta uguale per account inesistenti, eventi con login e limite di frequenza, testo degli utenti sempre come testo (niente `innerHTML` né `|safe`).
- **Dati** [L]: partita, mosse e rating in una transazione; cancellazione dell'account con chiavi esterne coerenti (partite con "utente eliminato"); log senza dati personali né valori del database.
- **Test e dati reali** [L]: rifiuto con il file `PRODUZIONE` e con un database che non finisce con `_test`, anche con pytest lanciato a mano.

## Confronto con DECISIONI.md

Letto dopo la bozza. Cosa è cambiato:

- **Rischi residui** (il finding contraddice una decisione: resta segnalato, ma la correzione non si ripropone):
  - **R2**, chi non arriva al tavolo: scelta di Antonio del 28/09 (P25), scartati i 60 secondi dall'inizio;
  - **R5**, `legal.lay_down`: è la regola di "Cala le carte" (01/10, D45);
  - **R10**, blocco del login di un altro: P16 (28/09) e P96 (04/10);
  - **R12**, Werkzeug nella demo: decisioni del 26/09 e 27/09;
  - **R3**, solo per la parte "alzare il limite": 240 s decisi il 29/09 e confermati con P121 (06/10). Resta la proposta di dividere le suite.
- **Nessuna decisione in contrasto**: R1, R4, R6, R7, R8, R9, R11, R13, R14, R15, R16. Per R1 e R9 una correzione nel database vorrebbe una migrazione nuova, che le decisioni del 28/09 lasciano "da concordare".
- **Controllato e conforme alle decisioni**: punti della mano di tutte e due le squadre nella vista (D44), carte del compagno (D46), consiglio non salvato, CPU senza salvataggio né rating (D43), partita persa al riavvio del server (P95), chat che resta dopo un blocco (D24, P48).

## Ordine consigliato (prima della consegna)

1. **R1**: piccola correzione (due regole e un test), riguarda la sicurezza.
2. **R7** e **R4**: solo se c'è tempo; con meno di 50 persone non si vedono.
3. Il resto dopo la consegna, o da citare nella relazione come limiti noti (R2, R5, R10, R12 in particolare).

Scelta di Christian (11/10): corretti R1, R2, R3, R13 e R14; gli altri restano limiti noti (`DECISIONI.md`, Processo, 11/10).

## Stato e punti aperti

Si spunta solo dopo l'ok dell'utente, il commit e il merge in `dev`, come nella scaletta.

### Finding

- [x] R1 — username ed email senza a-capo finale — *P137, 11/10 (commit `fefbab7`)*
- [x] R2 — chi non arriva al tavolo ha 60 secondi — *P138, 11/10 (commit `e626987`; riaperta la scelta del 28/09)*
- [x] R3 — suite dei test più corte (16 suite) — *P139, 11/10 (commit `704713d`)*
- [ ] R4 — stanze finite tolte dalla memoria — dopo la consegna (limite noto)
- [ ] R5 — `legal.lay_down` — rischio residuo (regola di D45): da citare nella relazione
- [ ] R6 — secondo tentativo del salvataggio — dopo la consegna (limite noto)
- [ ] R7 — coda, CPU e inviti sotto lo stesso lock — dopo la consegna (limite noto)
- [ ] R8 — cookie `Secure` con ngrok — dopo la consegna (va legato a una variabile del `.env`, altrimenti con la Wi-Fi il login non funziona)
- [ ] R9 — sessione revocabile — dopo la consegna (serve una colonna nuova)
- [ ] R10 — blocco del login di un altro — rischio residuo (P16, P96): da citare nella relazione
- [ ] R11 — limite sulle richieste HTTP degli amici — dopo la consegna
- [ ] R12 — server di sviluppo nella demo — rischio residuo: da riprendere con D21
- [x] R13 — avviso sul debugger in rete — *P140, 11/10 (commit `7bf7863`)*
- [x] R14 — avviso sui dati personali nei backup — *P140, 11/10 (commit `7bf7863`)*
- [ ] R15 — test mancanti: (a) fatto con P137; (b) resta con R4
- [ ] R16 — piccole copie nel codice — dopo la consegna

### Punti della scaletta non chiusi (copiati da `docs/archivio/SCALETTA-2026-09.md`, P37)

- [x] **P38** (Fase 5): installazione demo separata e backup pianificato — Giuseppe (punto di Antonio, passato a lui il 28/09) — *11/10 (commit `dece7b8`)*
  - *File*: `docs/DEMO.md` e `scripts/pianifica_backup.ps1` (con `tests/db/test_demo.py`), già in `dev` e in `main`; il resto (cartella della demo, `.env`, `PRODUZIONE`, firewall, ngrok) è fuori dal repository.
  - *Da quale branch*: **`main`** (D20), installata da "Cinquecento v1.0.3" (`fd0f10f`).
  - *Fatto*: sul PC di Giuseppe i passi 1–9 di `docs/DEMO.md`, con i tre "Fatto quando" provati [T]. La prova generale (passi 11 e 12) **non si fa più**: dal 19/10 non c'è più la demo, il PC di Giuseppe serve per lo sviluppo (`DECISIONI.md`, Progetto e tempi).
  - *Fatto quando*: nella cartella della demo c'è il file `PRODUZIONE` (`Test-Path PRODUZIONE` → `True`: da P136 in `main` non ci sono i test, quindi il rifiuto del runner non si prova lì); il backup pianificato produce un file; un ripristino di prova su `cinquecento_test` funziona.

### Migrazione del frontend (`docs/MIGRAZIONE-FRONTEND.md`, dal 19/10/2026)

Un passo per branch, nell'ordine del piano (sezione 4). **Christian** fa il frontend (`frontend/`) e la rotta di ogni pagina nuova in `app/blueprints/spa/routes.py`; **Giuseppe** fa le parti del backend scritte sotto ogni passo. Un passo con pezzi di tutti e due si chiude quando ci sono entrambi. **Dal 20/10 Giuseppe può fare anche i pezzi di Christian** (scelta di Christian), prima dei suoi punti.

- [x] **Passo 0** — piano, decisioni, regole del codice (sezione 6 di `regole-codice.md`) — Christian — *19/10 (commit `e5e50ce`, SPA e proxy in `2e772a2`)*
- [x] **Passo 1** — `frontend/` con Vite, React, TypeScript e React Router; proxy verso Flask; build in `app/static/dist/`; blueprint `spa` con la pagina di prova `/prova-react` — Christian (backend con l'ok di Christian, che vale anche per Giuseppe) — *19/10 (commit `18dc627`)*
  - **Giuseppe, subito**: installare Node 24.19.0, poi in `frontend/` `npm ci` e `npm run build` (README, passo 5); per lavorare al frontend `npm run dev` e `http://localhost:5173`.
- [x] **Passo 2** — i tipi del contratto in `frontend/src/types/`, controllati sugli esempi `app/static/dev/*.json` — Christian — *19/10 (commit `97ab28c`; `cannot_write` aggiunto all'esempio degli amici)*
- [x] **Passo 3** — `socket.js` in TypeScript (`frontend/src/socket/`, `socket.io-client` 4.8.1) e l'hook `useSocketEvent` — Christian — *19/10 (commit `7f0ac17`; l'avviso di connessione è passato al 5a)*
- [x] **Passo 4** — accesso e registrazione in React, con la navbar di chi non ha fatto il login; si toglie `/prova-react` — *19/10 (commit `24a41ec`; `/prova-react` resta fino al passo 6: è l'unica pagina della SPA con il login)*
  - **Christian**: le pagine React e la loro rotta in `spa/routes.py`.
  - **Giuseppe**: rotte JSON di accesso e registrazione, **sotto `/api/`** (`/api/auth/...`; stesse regole e stessi messaggi dei moduli di oggi: `\Z` di P137, tentativi per account di P96, CSRF), e la rotta che dà il codice CSRF alla SPA. *Fatto da Claude con l'ok di Christian, che valeva anche per Giuseppe (19/10): `app/blueprints/auth/api.py`, con `GET /api/auth/session` (codice CSRF, utente, messaggi).*
- [x] **Passo 5** — la cornice delle pagine con il login: navbar, pannello statistiche, pannello amici e chat. Diviso in tre lotti (19/10):
  - [x] **5a** — navbar con il login, pannello statistiche, avviso di connessione — Christian — *19/10 (commit `b2688b6`)*
  - [x] **5b** — pannello amici (stesso HTML di `FriendsPanel.js`; "indietro" con React Router) — Christian — *19/10 (commit `7639e8c`)*
  - [x] **5c** — chat e suoni del menu (`ChatWindow.tsx`, `utils/sounds.ts`) — Christian — *19/10 (commit `ddd6138`)*
  - **Giuseppe**: la rotta che dice chi è l'utente collegato. *Non serve una rotta a parte (5b): basta `user` di `GET /api/auth/session` (`user_id`, nome, avatar).*
- [x] **Passo 6** — impostazioni del profilo; si toglie `/prova-react` — *19/10 (commit `c3172ef`)*
  - **Christian**: la pagina React (`SettingsPage.tsx`).
  - **Giuseppe**: rotte JSON sotto `/api/`. *Fatte da Claude con l'ok di Christian, che valeva anche per Giuseppe (19/10): `app/blueprints/profile/api.py`, `GET /api/profile/avatars`, `POST /api/profile/avatar`, `POST /api/profile/delete` (contratto 2.4). Il cambio password non c'è: non esisteva, sarebbe una funzione nuova. I suoni non passano dal server.*
- [x] **Passo 7** — home (carte-pulsante, `ModeModal`, coda, inviti) — Christian — *20/10, in quattro lotti (scelte riconfermate da Christian il 20/10)*
  - [x] **7a** — base su `/prova-home` (solo sviluppo e test): carte-pulsante con l'inclinazione, sfondo, "giocatori online" (`home:status` con il login, `GET /online` senza), avviso di rientro con `?demo=rientro`; con il login le carte mostravano un avviso provvisorio — *commit `65da2b1`*
  - [x] **7b** — carta-modal della Partita Veloce, coda (`QueueOverlay.tsx`, P105), CPU 1v1 e 2v2, rating vero in "In breve"; le carte "con un amico" con un avviso provvisorio fino al 7c — *commit `d5e25df`*
  - [x] **7c** — inviti: carta-modal "Gioca con un amico", `InviteDialog.tsx`, P59, P83 — *commit `2e33eea`*
  - [x] **7d** — `/` è la home React; la home Jinja resta su **`/vecchia-home`** (solo sviluppo e test) fino al passo 9; tolta `/prova-home`; test adattati, misure della home (P22) portate sulla home React (`test_spa_home_misure.py`); corretto `test_blueprint_registrati` (rotto dal passo 6) — *commit `d0dd8fe`*
  - Dal 7c al 7d i test li hanno scritti in parallelo dei sotto-agenti (senza lanciarli); i test nel browser li ha lanciati la sessione principale, uno alla volta (porta 5099 e database condivisi).
- [x] **Passo 8** — tavolo, prima in parallelo (`/game/<id>?ui=react`), poi al posto del vecchio; da qui home e tavolo nella stessa SPA — *20–23/10, otto lotti, tutti fatti da Giuseppe (punto di Christian, permesso del 20/10), più le prove dell'8g di Christian*
  - *Piano* (20/10): in `docs/MIGRAZIONE-FRONTEND.md`, "Piano del passo 8", con "Com'è andata". Scelte di Christian (20/10): indirizzo `/game/<id>?ui=react` fino all'8h; store TypeScript con `useSyncExternalStore`; codice in `frontend/src/game/`, durate in `animations.ts`. Scelte di Giuseppe all'8a: `?ui=react` in tutti gli ambienti, terza copia di `AVATAR_CODES` (`SeatAvatar.tsx`), interruttore `TABLE_UI` (`tests/table_ui.py`), Vite serve il tavolo React, variabili CSS in `types/css.d.ts`.
  - [x] **8a** — tavolo React raggiungibile e disegnato da una vista finta; frasi anticipate dall'8f — *commit `652164a`*
  - [x] **Pezzo di Giuseppe** — `tests/sockets/test_durate_tavolo.py`: le durate uguali tra `room.py`, `game.js` e `animations.ts` — *commit `f332385`*
  - [x] **8b** — partita vera (`tableStore.ts`, `useTable.ts`), con il consiglio al compagno anticipato dall'8c — *commit `b6030e4`*
  - [x] **8c** — momenti del tavolo (presa chiusa, riepilogo, canti, calata, compagno, punti della mano); `useStartDelay` — *commit `db5915f`*
  - [x] **8d** — lanci e pescate — *commit `0a662f4`*
  - [x] **8e** — distribuzione, prima distribuzione, anello del tempo fermo nelle pause — *commit `f6adea4`*
  - [x] **8f** — frasi e suoni nella partita vera (`soundLater` al posto di `scheduleSound`) — *commit `3d54760`*
  - [x] **8g** — doppio tocco (Giuseppe, commit `889aa2b`); suite del tavolo intere con `TABLE_UI=react`, **242 PASS in 6 suite**, e prova a mano su iPhone e Android (Christian, commit `db1624a`)
  - [x] **8h** — `/game/<id>` è il tavolo React (quello Jinja su `?ui=jinja` fino al passo 9); dalla home al tavolo e ritorno senza ricaricare; evento nuovo `home:refresh` (contratto 5.1); `TABLE_UI` predefinito `react` — *commit `5a1f5c8`*
  - Correzione a parte (Giuseppe, 22/10): `test_spa_impostazioni.py::test_cancellazione_con_la_password` instabile dal 7d — *commit `1e0781c`*
- [ ] **Passo 9** — tolti i file JS vecchi e i loro test (rifatti sul codice nuovo)
  - *Piano* (23/10, preparato da Claude per Christian): cinque lotti in fila, **9a** tavolo vecchio, **9b** home e cornice vecchie, **9c** rotte JSON sotto `/api/`, **9d** regola unica della SPA, **9e** giro completo; in `docs/MIGRAZIONE-FRONTEND.md`, "Piano del passo 9".
  - *Scelte confermate da Christian* (23/10): le otto del piano come raccomandato (test vecchi portati o cancellati con una tabella; confronti del DOM tolti; `Card.js`/`Avatar.js` letti come testo; vecchi indirizzi JSON 404 e `POST /api/auth/logout`; regola unica con la pagina React "non trovata"; errori Jinja con `base.html` ridotto; rotte dove sono), **tranne la 8: tutti i lotti del passo 9 li fa Christian**, anche 9c, 9d e 9e. Nel 9a `?ui=` si ignora; il 9b diviso in 9b-1 e 9b-2; la pagina di prova delle carte cancellata.
  - [x] **9a** — via il tavolo Jinja (`game/table.html`, `pages/game.js` e sette componenti), `?ui=` ignorato, `TABLE_UI` e `tests/table_ui.py` tolti (`table_path` in `tests/spa.py`), durate solo in `animations.ts` (confronti tutti in `test_durate_tavolo.py`) — Christian — *23/10 (commit `4233f91`)*
  - [x] **9b-1** — i test che aprivano `/vecchia-home` portati sulla home React o cancellati con il loro gemello React (tabella in `christian.md`) — Christian — *23/10 (commit `d271a87`)*
  - [x] **9b-2** — via tutto `app/static/js/`, `main/index.html`, i `partials/`, `/vecchia-home` e la pagina di prova delle carte; `base.html` solo per le pagine di errore; test rifatti sul codice nuovo; corretto un import rotto dal 9b-1 in `test_spa_amici.py` — Christian — *23/10 (commit `c8a2dbf`)*
  - [x] *Test a parte*: `checkCard` e `cardName` di `cards.ts` eseguiti con Node (tornano gli 11 controlli persi nel 9b-2) — Christian — *23/10 (commit `f737d85`)*
  - [x] **9c** — rotte JSON sotto `/api/` (`/api/online`, `/api/stats/me`, `/api/friends/...`, `POST /api/auth/logout` in JSON; vecchi indirizzi 404; `JSON_PREFIXES` solo `/api/`), contratto (1.5 riscritta, 2, 2.3, 5.1, 5.2), esempi e chiamate della SPA; "Esci" ricarica la home — Christian — *24/10 (commit `d1e32bf`)*
  - [x] **9d** — regola unica della SPA nel gestore del 404 (GET e HEAD fuori da `/api/`, `/static/`, `/socket.io`), pagina React "non trovata" con la navbar, `/` in fondo rimandata (302), `caseSensitive` in React; via `SPA_PATHS` e `GAME_TABLE` (al loro posto `NOT_SPA` e `FLASK_PATHS`) — Christian — *24/10 (commit `0cce805`)*
  - [ ] **9e** — giro completo delle suite (con le sei `table*`), `ruff`, `tsc`, build, prova a mano
    - [x] giro completo: **1983 PASS in 16 suite**; corretti due test di `runner` rotti dal passo 4 (import di `tests.spa` in `conftest.py` dopo i rifiuti) — Giuseppe, con l'ok di Christian — *24/10 (commit `d1cca95`)*
    - [ ] prova a mano su telefono e computer (accesso, home, coda, CPU, inviti, tavolo, chat, impostazioni, "Esci", pagina "non trovata") — **Christian** (24/10: la fa lui, non Giuseppe)
  - [ ] *Dopo il 9e*: riscrittura dei punti delicati di `CLAUDE.md` che citano il codice vecchio; i commenti del frontend e dei CSS che citano file tolti (`FriendsPanel.js`, `js/components/…`) e `csrfToken` di `SessionContext.tsx` non usato — Christian

### Commenti e niente zucchero nel Python (`regole-codice.md`, dal 24/10/2026)

Proposto da Giuseppe il 24/10; divisione confermata da Christian il 24/10: ognuno la sua parte, così nessuno tocca i file dell'altro. Un lotto per branch; nomi, ordine e comportamento uguali; solo i test della parte toccata. Esempi di file già fatti: `app/realtime/invites.py`, `app/blueprints/auth/api.py`.

- [x] **1a** — motore, i file piccoli (`app/game/engine/` tranne `game.py`, `lay_down.py`, `views.py`, `cpu.py`) — Giuseppe — *24/10 (commit `c61725d`)*
- [x] **1b** — motore: `game.py`, `lay_down.py`, `views.py` — Giuseppe — *24/10 (commit `7d22c95`)*
- [x] **2a** — tempo reale, i file piccoli di `app/realtime/` — Giuseppe — *24/10 (commit `44f684a`)*
- [x] **2b** — `app/realtime/room.py` — Giuseppe — *24/10 (commit `400116e`)*
- [x] **2c** — `app/realtime/matchmaking.py` — Giuseppe — *24/10 (commit `088fcd9`)*
- [x] **2d** — `app/sockets/` (7 file) — Giuseppe — *24/10 (commit `620c9a7`)*
- [ ] **3** — `app/services/`, `app/repositories/`, `app/models/` — Giuseppe, in due:
  - [x] **3a** — rating e partite (`glicko2.py`, `rating_service.py`, `match_service.py`, `stats_service.py`, `rating_repo.py`, `match_repo.py`, `stats_repo.py`, `models/match.py`, `models/rating.py`, gli `__init__.py`) — *24/10 (commit `0695aab`)*
  - [ ] **3b** — account, amici e chat (`auth_service`, `friend_service`, `chat_service`, `avatars`, `user_repo`, `friend_repo`, `chat_repo`, `models/user.py`, `friendship.py`, `chat_message.py`)
- [ ] **Sito** — `app/blueprints/` che mancano (`auth/forms.py`, `friends/routes.py`, `stats/routes.py`, gli `__init__.py`); `app/__init__.py`, `app/errors.py`, `app/extensions.py`, `app/checks.py`, `app/logging_config.py` — Christian
- [ ] **4** — `config.py`, `run.py`, `scripts/` (`backup.py`, `migrate.py`, `ripristina.py`) — Christian
- [ ] **5** — `app/game/engine/cpu.py`, per ultimo — Giuseppe
