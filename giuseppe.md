# Riepiloghi di Giuseppe

> **Questo file lo scrive solo Giuseppe** (Studente 1: motore e tempo reale). Christian lo legge dopo il `git pull` di `dev` e da qui aggiorna i documenti condivisi (`SCALETTA.md`, `CLAUDE.md`, `DECISIONI.md`, `DA-DECIDERE.md`). Nessun altro lo modifica, nemmeno per correggere un errore: si segnala a Giuseppe.
>
> **Come si aggiorna** (regola in `CLAUDE.md`, "Consegna"): a fine punto, nel branch del punto (`feature/…`, `fix/…`), Giuseppe aggiunge il riepilogo **in cima** alla sezione "Riepiloghi", nello stesso commit del punto; così arriva in `dev` con il merge. Il numero del commit non si scrive: lo si trova con `git log -- giuseppe.md`.

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

<!-- Il più recente in cima. I riepiloghi di P10–P13 li ha copiati Christian il 28/09/2026 dai messaggi di Giuseppe, senza cambiarli. -->

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
