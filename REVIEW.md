# Code review indipendente (P36)

> 11/10/2026. I finding sono stati scritti **prima** di leggere `DECISIONI.md`; poi sono stati confrontati con le decisioni (sezione "Confronto con DECISIONI.md"): quelli che ne contraddicono una sono segnati "rischio residuo", senza riproporre le soluzioni scartate. La review non ha modificato il codice.

Legenda dell'evidenza: **[T]** verificato con una prova · **[L]** letto nel codice · **[D]** dedotto · **[N]** non verificabile.
Gravità: critico, alto, medio, basso.

## Riepilogo

- **Critici e alti**: nessuno.
- **Medi**: R1 (username con a-capo), R2 (rischio residuo), R3 (in parte rischio residuo).
- **Bassi**: R4–R16 (R5, R10 e R12 rischi residui).
- Ambito: motore e regole, viste, tempo reale, socket e rotte, servizi e repository, migrazione, script di backup, sicurezza delle pagine (ricerca dei punti in cui il testo potrebbe diventare HTML), protezioni dei test. Non riletti riga per riga: la strategia della CPU (`cpu.py`, salvo cosa legge), i CSS e il disegno del tavolo in `game.js`.

## Finding

### R1 — medio — Username ed email accettano un a-capo finale [T]

- **Dove**: `app/blueprints/auth/forms.py:326` (`Regexp(r"^[A-Za-z0-9_]+$")`), `:331` (email); `migrations/001_init.sql:63` (`ck_utenti_nome`).
- **Cosa**: in Python `$` vale anche prima di un a-capo finale, e `Regexp` di WTForms usa `re.match`. Il `CHECK` di MySQL (`REGEXP_LIKE`, ICU) fa lo stesso. Il campo non toglie gli spazi.
- **Prova**: `re.match(r"^[A-Za-z0-9_]+$", "Mario\n")` → trovato; su MySQL 8.0 `REGEXP_LIKE('Mario\n', '^[A-Za-z0-9_]{3,20}$', 'c')` = 1, e anche con `"Mario\r\n"`. Un `POST /auth/register` con `username="Revis\n"` (client di prova di Flask) ha passato il modulo ed è arrivato all'`INSERT`.
- **Scenario**: con una richiesta scritta a mano (non dal modulo della pagina) qualcuno registra `Mario\n`. La collation `utf8mb4_0900_as_cs` è NO PAD, quindi è diverso da `Mario`, ma nelle pagine si vede come "Mario": in chat, al tavolo, nelle richieste di amicizia. È un modo per farsi passare per un altro.
- **Correzione**: `\Z` al posto di `$` (o `fullmatch`) nelle due regole del modulo; un test con `"Mario\n"` e `"a@b.it\n"`. Il `CHECK` del database non si può cambiare in `001_init.sql` (migrazione già applicata): servirebbe una `002_…sql` con `'^[A-Za-z0-9_]{3,20}\\z'`, da concordare (DECISIONI, 28/09: "nella prima versione non sono previste altre migrazioni"). La correzione del modulo da sola basta, perché tutte le registrazioni passano da lì.
- **Decisioni**: nessuna in contrasto; è un difetto dell'attuazione di D7 (solo lettere, numeri e `_`).
- **File**: `app/blueprints/auth/forms.py`, `tests/api/test_auth.py`; facoltativo `migrations/002_….sql`.

### R2 — medio — Chi non arriva mai al tavolo non ha limite di tempo [L] · rischio residuo

- **Dove**: `app/realtime/room.py:17-19`, `:506-522` (il conto alla rovescia parte solo da `disconnect`, cioè per chi era seduto).
- **Scenario**: la coda abbina due giocatori; uno chiude la scheda proprio in quel momento e non fa mai `game:join`. L'altro gioca tutta la partita (fino a 500 punti) contro le mosse automatiche, 15 s a turno, oppure preme "Esci" e **perde per abbandono**, con il rating che scende a lui e non a chi è sparito.
- **Decisione**: è la scelta di Antonio del 28/09/2026 (P25, opzione b; scartati i 60 secondi dall'inizio). Resta da sapere, per la demo, che chi preme "Esci" in quel caso perde rating.
- **Correzione**: nessuna proposta nuova; se il gruppo vuole riaprirla, si riparte dalla decisione del 28/09.
- **File**: —

### R3 — medio — Suite dei test vicine al limite di 240 s [L] · in parte rischio residuo

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

### R13 — basso — In sviluppo il debugger di Werkzeug è acceso [D]

- **Dove**: `config.py:99-101` (`DEBUG = True`), `run.py:24`.
- **Scenario**: chi avvia in sviluppo con `HOST=0.0.0.0` (per provare dal telefono) espone il debugger interattivo alla rete locale (protetto da un PIN).
- **Correzione**: una riga in `.env.example`/`README.md`: in rete usare `APP_ENV=demo`; oppure `use_debugger=False` quando `HOST` non è locale.
- **File**: `.env.example`, `README.md` (o `run.py`).

### R14 — basso — Backup sullo stesso PC e non cifrati [L]

- **Dove**: `scripts/backup.py`, `docs/DEMO.md` passo 8.
- **Scenario**: se il disco del PC della demo si rompe, si perdono database e backup insieme. I file contengono email e hash delle password in chiaro (compressi).
- **Correzione**: copiare ogni tanto l'ultimo backup su un altro supporto; nella guida, dire dove tenerli e che contengono dati personali.
- **File**: `docs/DEMO.md`.

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
