# Scaletta — Cinquecento

> **Tracker attivo.** Ogni punto si fa su un **branch nuovo creato da `dev`**. Si spunta solo dopo l'ok dell'utente, il commit e il merge in `dev`. Chi spunta e aggiorna i documenti condivisi è ancora da decidere (D22). Accanto al punto si aggiunge una breve nota del lotto (data e cosa è stato fatto). **Chi fa cosa** è nella sezione 9.
>
> **Regola sui file:** chi lavora a un punto crea e modifica **solo i file elencati in quel punto**. Se serve toccarne un altro, ci si ferma e lo si concorda: è così che si evitano i conflitti tra i lavori dei tre membri. Dove l'elenco dei file **non è sicuro** lo dice il punto stesso.
>
> **Numerazione:** i numeri dei punti non cambiano mai, così i riferimenti restano validi. I punti aggiunti il 26/09/2026 (P40–P52) sono inseriti nella fase giusta, anche se il numero è più alto. I punti tolti il 27/09/2026 (P41, P49, P50, P51) restano nell'elenco, barrati.

## 1. Obiettivo

Una web-app per giocare online a **Cinquecento**, variante siciliana, con le carte siciliane. Si può giocare 1v1 o 2v2, a 150, 300 o 500 punti, con un matchmaking basato sul rating, account personali, statistiche, amici con chat e inviti a partita. Per ora è pensata per amici e compagni (meno di 50 persone connesse insieme). In futuro deve poter crescere fino a un gioco pubblico. Scadenza: circa una settimana (03/10/2026, vedi D1), con 3 persone.

**Prima versione usabile** = sul PC della demo, raggiungibile dagli altri dispositivi della stessa rete:
- ci si registra, si entra e si esce, si sceglie un avatar, si cancella il proprio account;
- dalla home si gioca 1v1 o 2v2 con **Partita Veloce** (coda di matchmaking) o **Gioca con un amico** (invito), con partite **complete fino al punteggio scelto** (150, 300 o 500) e tutte le regole di `docs/REGOLE-GIOCO.md`;
- si mandano e si accettano **richieste di amicizia**, si vede chi è online, si **chatta** con gli amici e li si **invita** a una 1v1 o 2v2;
- il rating si aggiorna per le partite dalla coda, compreso il 2v2 con un amico come compagno (non per il 1v1 contro un amico); le statistiche si vedono nel pannello dell'avatar;
- funziona bene da smartphone;
- tutte le suite di test passano, e c'è un backup ripristinabile.

**Com'è fatta l'interfaccia** (prototipo approvato il 27/09/2026 in `docs/prototipo/`, vedi `DECISIONI.md`, Interfaccia):
- **una sola pagina, la home, che non scorre mai**; niente bottom navbar, classifica, stanza privata, storico né pagina delle regole;
- **navbar trasparente e sfocata**: a sinistra l'avatar, che apre il pannello statistiche (con Impostazioni ed Esci); al centro il nome **Cinquecento**; a destra gli amici con il contatore, che aprono il pannello amici con la chat;
- **home**: "giocatori online" al centro; sezioni **Partita Veloce** e **Gioca con un amico**, ciascuna con due carte-pulsante 1v1 e 2v2; il modal chiede i punti (150, 300, 500) e, con un amico, chi invitare; sullo sfondo carte siciliane sparse; l'avviso "rientra in partita" quando serve.

**Legenda**
- *Filone*: A = motore di gioco, B = account e dati, C = interfaccia, I = integrazione (tempo reale).
- *Dimensione*: piccolo (fino a mezza giornata), medio (circa 1 giornata). I punti grandi sono già spezzati.
- *File*: **crea** = file nuovo; **modifica** = file che esiste già (creato da un punto precedente, indicato tra parentesi). I percorsi sono quelli della struttura nel `README.md`.

## 2. Tracker

### Fase 1 — Fondamenta
- [x] P1 (Fase 1): fine riga fissati — `.gitattributes` — *26/09: creato; i file tracciati sono `i/lf w/crlf`, un `.sh` nuovo resta LF; marcati binari anche jpeg, gif, font, gz e zip*
- [x] P2 (Fase 1): `.gitignore` completo — `.gitignore` — *26/09: aggiunti segreti (`.env`, `.env.*` tranne `.env.example`), `PRODUZIONE`, `backups/`, `logs/`, `*.sql.gz`, `*.dump`, file di sistema ed editor; provato con file finti*
- [ ] P3 (Fase 1): riga "Stato" e regola di consegna — `CLAUDE.md`
- [x] P4 (Fase 1): scheletro del progetto con tutti i file "segnaposto" — `run.py`, `config.py`, `app/`, `requirements*.txt`, `.env.example` — *27/09: 36 file dell'elenco, 39 librerie fissate con `==`, 31 test PASS (`python -m pytest tests/api/test_avvio.py`, finché P6 non aggiunge `conftest.py`), `ruff check .` pulito (D4); il controllo di MySQL sta in `run.py`, così i test di P4 non richiedono MySQL*
- [ ] P5 (Fase 1): database e prima migrazione — `scripts/setup_db.sql`, `migrations/001_init.sql`, `scripts/migrate.py`, `app/models/`
- [ ] P6 (Fase 1): runner dei test — `tests/esegui_tutti.py`, `tests/conftest.py`
- [ ] P7 (Fase 1): log ed errori di base — `app/logging_config.py`, `app/errors.py`, `app/templates/errors/`
- [ ] P8 (Fase 1): contratto tra server e pagine — `docs/CONTRATTO-SOCKET.md`, `app/static/dev/*.json`
- [ ] P9 (Fase 1): guida di installazione verificata — `README.md`
- [x] P52 (Fase 1, C): prototipo della home — `docs/prototipo/` — *27/09: approvato dopo varie prove: `index.html`, `prototipo.css`, `prototipo.js`, `LEGGIMI.md`, `img/` (carte siciliane da Wikimedia). Ritoccato lo stesso giorno su richiesta dell'utente: panno verde, navbar completamente trasparente, logo nuovo in CSS, animazioni dei pannelli statistiche e amici, carta 2v2 viola, sfondo tutto a cascata di carte (coppie Cavallo + Re, Assi, Tre e dorsi, con il dorso napoletano da Wikimedia), navbar e carte-pulsante in rilievo con i semi siciliani (`DECISIONI.md`, Interfaccia)*

### Fase 2 — Funzioni essenziali
- [ ] P10 (Fase 2, A): carte, mazzo, parametri delle regole — `app/game/engine/cards.py`, `deck.py`, `rules.py`, `errors.py`
- [ ] P11 (Fase 2, A): chi vince la presa — `app/game/engine/trick.py`
- [ ] P12 (Fase 2, A): cantare 40 e 20 — `app/game/engine/singing.py`
- [ ] P13 (Fase 2, A): svolgimento di una mano, 1v1 e 2v2 — `app/game/engine/state.py`, `actions.py`, `game.py`
- [ ] P14 (Fase 2, A): partita fino al punteggio scelto (150, 300, 500), pareggio, mazziere — `app/game/engine/game.py`, `state.py`
- [ ] P15 (Fase 2, A): vista per giocatore, mosse legali, mossa automatica — `app/game/engine/views.py`, `auto_move.py`
- [ ] P16 (Fase 2, B): registrazione, login, logout — `app/blueprints/auth/`, `auth_service.py`, `user_repo.py`, `app/templates/auth/`
- [ ] P17 (Fase 2, B): impostazioni: avatar e cancellazione dell'account — `app/blueprints/profile/`, `app/templates/profile/`, `app/services/avatars.py`
- [ ] P18 (Fase 2, B): backup e ripristino — `scripts/backup.py`, `scripts/ripristina.py`
- [ ] P19 (Fase 2, C): base grafica mobile-first — `app/templates/base.html`, `app/static/css/base/`
- [ ] P40 (Fase 2, C): navbar, pannello statistiche con dati finti, finestra "Accedi o registrati" — `partials/navbar.html`, `app/static/js/core/layout.js`, `StatsPanel.js`
- [ ] P20 (Fase 2, C): componenti carta e mano — `app/static/js/components/Card.js`, `Hand.js`
- [ ] P21 (Fase 2, C): tavolo di gioco con dati finti — `app/templates/game/table.html`, `app/static/js/pages/game.js`
- [ ] P22 (Fase 2, C): home con dati finti (carte-pulsante, modal, coda, rientro, online, sfondo) — `app/templates/main/index.html`, `app/static/js/pages/home.js`, `ModeModal.js`, `CardBackground.js`
- [ ] ~~P41 (Fase 2, C): pagina stanza privata con dati finti~~ — **tolto il 27/09/2026** per decisione dell'utente (vedi `DECISIONI.md`, Progetto e tempi)
- [ ] P45 (Fase 2, B): amicizie (richieste, accetta, rifiuta, rimuovi, lista) — `app/blueprints/friends/`, `friend_service.py`, `friend_repo.py`
- [ ] P46 (Fase 2, C): pannello amici e finestra chat con dati finti — `FriendsPanel.js`, `ChatWindow.js`
- [ ] P23 (Fase 2, I): collegamento in tempo reale, stanze, lock — `app/realtime/`, `app/sockets/connection_events.py`, `app/static/js/core/socket.js`
- [ ] P24 (Fase 2, I): stanze e partita completa — `app/realtime/room.py`, `room_manager.py`, `app/sockets/game_events.py`
- [ ] P25 (Fase 2, I): timer, riconnessione, abbandono — `app/realtime/room.py`, `app/sockets/game_events.py`
- [ ] P26 (Fase 2, B): salvataggio delle partite — `match_service.py`, `match_repo.py`
- [ ] P27 (Fase 2, B): rating Glicko-2 — `glicko2.py`, `rating_service.py`, `rating_repo.py`
- [ ] P28 (Fase 2, I): matchmaking 1v1, code per punteggio — `app/realtime/matchmaking.py`, `app/sockets/lobby_events.py`, `pages/home.js`, `ModeModal.js`
- [ ] P29 (Fase 2, I): matchmaking 2v2, anche con una coppia già formata — `app/realtime/matchmaking.py`, `pages/home.js`
- [ ] P44 (Fase 2, I): home con dati reali (online, rientro in partita) — `app/realtime/presence.py`, `app/sockets/home_events.py`
- [ ] P47 (Fase 2, I): amici online e inviti a partita — `app/realtime/invites.py`, `app/sockets/friends_events.py`, `ModeModal.js`
- [ ] P48 (Fase 2, B+I): chat tra amici — `chat_service.py`, `chat_repo.py`, `app/sockets/chat_events.py`
- [ ] P30 (Fase 2, B+C): pannello statistiche con dati reali — `stats_service.py`, `stats_repo.py`, `StatsPanel.js`
- [ ] ~~P49 (Fase 2, B+C): classifica~~ — **tolto il 27/09/2026** per decisione dell'utente (vedi `DECISIONI.md`, Progetto e tempi)
- [ ] ~~P50 (Fase 2, B+C): pagina "Partite" (storico)~~ — **tolto il 27/09/2026** per decisione dell'utente (vedi `DECISIONI.md`, Progetto e tempi)
- [ ] ~~P51 (Fase 2, C): pagina "Regole" con mini-tutorial~~ — **tolto il 27/09/2026** per decisione dell'utente (vedi `DECISIONI.md`, Progetto e tempi)

### Fase 3 — Robustezza
- [ ] P31 (Fase 3): test end-to-end con client simulati — `tests/e2e/`
- [ ] P32 (Fase 3): sicurezza di base — `config.py`, `app/__init__.py`, altri **da definire**
- [ ] P33 (Fase 3): errori e connessione nell'interfaccia — `Banner.js`, `app/static/js/core/socket.js`, altri **da definire**

### Fase 4 — Rifiniture e revisione
- [ ] P34 (Fase 4): rifinitura mobile e accessibilità — `app/static/css/`, `app/templates/` (**file precisi da definire**)
- [ ] P35 (Fase 4): carte vere — `app/static/img/cards/`, `Card.js`, `card.css`
- [ ] P42 (Fase 4): logo vero "Cinquecento" — `app/static/img/logo.*` (**formato da definire**), `partials/navbar.html`
- [ ] P43 (Fase 4): immagini degli avatar — `app/static/img/avatars/` (**file da definire**)
- [ ] P53 (Fase 4): tema scuro automatico — `app/static/css/base/variables.css`, altri **da definire**
- [ ] P36 (Fase 4): code review indipendente — `REVIEW.md`
- [ ] P37 (Fase 4): chiusura e archiviazione della scaletta — `docs/archivio/`, `REVIEW.md`, `CLAUDE.md`

### Fase 5 — Messa in servizio (demo locale)
- [ ] P38 (Fase 5): installazione demo separata e backup pianificato — `docs/DEMO.md` (il resto è fuori dal repository)
- [ ] P39 (Fase 5): accesso dagli altri dispositivi e prova generale — `docs/DEMO.md`

## 3. File condivisi: come evitare i conflitti

Un conflitto git nasce quando due persone modificano **le stesse righe dello stesso file** in branch diversi. Per evitarlo:

1. **P4 crea in anticipo tutti i file "di collegamento"** come segnaposto: funzioni vuote già chiamate da `create_app()`, blueprint già registrati, moduli socket già importati, tutte le chiavi di configurazione in `config.py` e `.env.example`, tutte le librerie in `requirements.txt`. Così i punti successivi **riempiono** i propri file e non toccano `app/__init__.py`.
2. I file toccati da più punti sono pochi, e quei punti sono **in sequenza** (uno dipende dall'altro). Quando vanno a studenti diversi, vale la regola: **chi fa il punto successivo inizia solo quando il precedente è già in `dev`**, e crea il suo branch da `dev` aggiornato. Così lavora sempre sulla versione più recente del file e non nasce nessun conflitto. Gli studenti indicati si riferiscono alla sezione 9.

| File | Punti che lo toccano (in ordine) | Nota |
|---|---|---|
| `app/__init__.py`, `config.py` | P4 → P32 | Dopo P4 li tocca solo P32 |
| `requirements.txt`, `requirements-dev.txt`, `.env.example`, `app/extensions.py` | P4 | Una libreria o una chiave nuova richiede di fermarsi e concordarla |
| `app/sockets/__init__.py` | P4 → P23 → P28 → P44 | Studente 1 → Studente 2 → Studente 1, ciascuno dopo che il punto precedente è in `dev` |
| `app/realtime/room.py` | P23 → P24 → P25 → P26 | Studente 1; P26 (Studente 2) aggiunge solo la chiamata al salvataggio, dopo che P25 è in `dev` |
| `app/realtime/room_manager.py` | P23 → P24 | Studente 1. P28, P29, P44 e P47 **usano** le funzioni che P24 espone, senza modificare il file |
| `app/sockets/connection_events.py` | P4 → P23 → P25 → P44 | Studente 1 |
| `app/sockets/lobby_events.py` | P4 → P28 → P29 | Studente 2 (da P24 non la tocca più nessun altro: niente stanze private) |
| `app/sockets/game_events.py` | P4 → P24 → P25 | Studente 1 |
| `app/sockets/friends_events.py` | P4 → P47 | Studente 1 |
| `app/sockets/chat_events.py` | P4 → P48 | Studente 2 |
| `app/static/js/pages/game.js` | P21 → P24 → P25 | Studente 3, poi Studente 1 dopo che P21 è in `dev` |
| `app/static/js/pages/home.js` | P22 → P28 → P29 → P44 | Studente 3 → Studente 2 → Studente 1, ciascuno dopo che il punto precedente è in `dev` |
| `app/static/js/components/ModeModal.js` | P22 → P28 → P47 | Studente 3 → Studente 2 (collega "Gioca" alla coda) → Studente 1 (lista amici e inviti), ciascuno dopo che il punto precedente è in `dev` |
| `app/static/js/components/StatsPanel.js` | P40 → P30 | Studente 3 (dati finti, poi dati veri) |
| `app/static/js/components/FriendsPanel.js` | P46 → P47 | Studente 3, poi Studente 1 dopo che P46 è in `dev` |
| `app/static/js/components/ChatWindow.js` | P46 → P48 | Studente 3, poi Studente 2 dopo che P46 è in `dev` |
| `app/static/js/core/layout.js` | P40 → P46 | Studente 3 |
| `app/static/js/core/socket.js` | P23 → P33 | — |
| `app/game/engine/game.py`, `state.py` | P13 → P14 | Studente 1 |
| `app/services/auth_service.py`, `app/repositories/user_repo.py` | P16 → P17 | Studente 2 |
| `app/services/match_service.py` | P26 → P27 | Studente 2 |
| `app/blueprints/*/routes.py` e `__init__.py` | P4 (segnaposto) → un solo punto per blueprint | `main/routes.py`: solo P22 (Studente 3) |
| `app/templates/base.html` | P19 → P40 → P33 | — |
| `app/templates/partials/navbar.html`, `app/static/css/components/navbar.css` | P40 → P42 → P43 | Studente 3 |
| `app/templates/main/index.html` | P4 → P19 → P22 | Studente 3 dopo P4 |
| `app/templates/errors/*.html` | P7 → P19 | — |
| `app/templates/profile/settings.html` | P17 → P43 | Studente 2, poi Studente 3 dopo che P17 è in `dev` |
| `app/static/js/components/Card.js`, `app/static/css/components/card.css` | P20 → P35 | Studente 3 |
| `docs/DEMO.md` | P38 → P39 | Studente 2 |
| `README.md` | P9 → P37 | Studente 3 |
| `docs/prototipo/*` | P52 | Dopo P52 nessuno lo modifica: P19, P40 e P22 lo **leggono** soltanto |
| `SCALETTA.md`, `CLAUDE.md` (riga Stato), `DECISIONI.md`, `DA-DECIDERE.md` | tutti | **Punto aperto (D22)**: con tre persone che li aggiornano, i conflitti sono quasi certi |

## 4. Fasi e dettaglio dei punti

### Fase 1 — Fondamenta (giorno 1)

**P1 — `.gitattributes`** · piccolo · decisione: no (già presa: CRLF, `.sh` in LF)
- *Cosa e perché*: dice a git quali fine riga usare, così il risultato non dipende dalle impostazioni del PC di ciascuno (su Windows c'è `core.autocrlf`). Si evitano modifiche "fantasma" in cui cambiano solo gli a capo.
- *Contenuto*: `* text=auto eol=crlf`, `*.sh text eol=lf`, e le immagini (`*.png`, `*.jpg`, `*.webp`, `*.ico`) marcate `binary`.
- *File*: crea `.gitattributes`. Certezza: **sicuro**.
- *Fatto quando*: `git ls-files --eol` mostra `i/lf w/crlf` per i file di testo [T]; un file appena creato ha il fine riga giusto dopo `git add`.
- *Dipende da*: nessuno. È il **primo punto in assoluto**.

**P2 — `.gitignore` completo** · piccolo · decisione: no
- *Cosa e perché*: evita che finiscano nel repository cose che non devono esserci. Il file attuale è quello standard di GitHub per Python: va completato.
- *Da aggiungere o controllare*: `.venv/`, `.env` (ma non `.env.example`), `PRODUZIONE`, `backups/`, `logs/`, `*.sql.gz`, i dump, `instance/`, `.pytest_cache/`, file di sistema (`Thumbs.db`, `desktop.ini`, `.DS_Store`), file degli editor (`.vscode/`, `.idea/`).
- *File*: modifica `.gitignore` (esiste già). Certezza: **sicuro**.
- *Fatto quando*: creando per prova `.env`, `PRODUZIONE`, `backups/x.sql.gz` e `logs/x.log`, `git status` non li mostra [T]. Poi i file di prova si cancellano. Va fatto **prima del primo commit di codice**.
- *Dipende da*: P1.

**P3 — Riga "Stato" e regola di consegna** · piccolo · decisione: no
- *Cosa e perché*: ogni sessione riparte dalla riga "Stato" (data, cosa è fatto, prossimo passo), da aggiornare **alla fine di ogni lotto**. La regola è scritta anche nella sezione "Consegna".
- *File*: modifica `CLAUDE.md`. Certezza: **sicuro**. *Preparato nel lotto della scaletta*: si spunta con l'ok. Come si gestisce la riga Stato con tre persone è la domanda D22.
- *Fatto quando*: `CLAUDE.md` ha la riga compilata e il passo 7 in "Consegna".
- *Dipende da*: nessuno.

**P4 — Scheletro del progetto** · medio · decisione: **D4** (lint)
- *Cosa e perché*: crea tutta la struttura del `README.md` con i file di collegamento **già pronti come segnaposto** (vedi sezione 3), così gli altri punti non devono toccare i file centrali. `config.py` contiene fin da subito **tutte** le chiavi: database, `SECRET_KEY`, `HOST`, `PORT`, secondi del turno (30), secondi di riconnessione (60), parametri del matchmaking, limiti della chat (lunghezza e frequenza dei messaggi), durata degli inviti, cartelle di log e backup, giorni di conservazione dei backup e dei messaggi. All'avvio si **controllano le versioni** (Python 3.14, MySQL 8.0) e ci si ferma con un messaggio chiaro se non corrispondono.
- *File* — crea:
  - radice: `run.py`, `config.py`, `.env.example`, `requirements.txt`, `requirements-dev.txt`
  - `app/__init__.py`, `app/extensions.py`, `app/checks.py`
  - segnaposto: `app/logging_config.py`, `app/errors.py`
  - pacchetti vuoti: `app/game/__init__.py`, `app/game/engine/__init__.py`, `app/realtime/__init__.py`, `app/services/__init__.py`, `app/repositories/__init__.py`, `app/models/__init__.py`
  - segnaposto socket: `app/sockets/__init__.py`, `connection_events.py`, `lobby_events.py`, `game_events.py`, `friends_events.py`, `chat_events.py`
  - segnaposto blueprint: `__init__.py` e `routes.py` in `app/blueprints/main/`, `auth/`, `profile/`, `game/`, `stats/`, `friends/`
  - `app/templates/main/index.html` (pagina "ok" provvisoria)
  - `tests/api/test_avvio.py`
- Certezza: **sicuro** per l'elenco. Le versioni esatte delle librerie si fissano durante il punto.
- *Fatto quando*: `python run.py` mostra la pagina "ok" su `http://localhost:5000` [T]; con una versione di Python diversa dalla 3.14 l'avvio si rifiuta; `pytest tests/api/test_avvio.py` passa.
- *Dipende da*: P1, P2.

**P5 — Database** · medio · decisione: **D6, D7, D23, D24, D38** (servono per scrivere le tabelle; la proposta completa delle tabelle è D38 in `DA-DECIDERE.md`)
- *Cosa e perché*: `setup_db.sql` crea i database `cinquecento_dev` e `cinquecento_test` con un utente MySQL dedicato, in `utf8mb4`/InnoDB. `001_init.sql` crea **tutte** le tabelle della prima versione: `users` (con l'avatar scelto), `ratings`, `matches` (con il punteggio per vincere: 150, 300 o 500), `match_players`, `match_events`, `friendships` (richieste e amicizie, con lo stato), `user_blocks` (solo se D23 = sì), `chat_messages`, `schema_version`. Il comportamento alla cancellazione di un utente (D6) si decide qui, con le chiavi esterne. `migrate.py` applica le migrazioni mancanti. I modelli Python rispecchiano le tabelle.
- *File* — crea: `scripts/setup_db.sql`, `migrations/001_init.sql`, `scripts/migrate.py`, `app/models/user.py`, `app/models/rating.py`, `app/models/match.py`, `app/models/friendship.py`, `app/models/chat_message.py`, `tests/db/test_migrate.py`. Certezza: **sicuro**. Se D23 = sì, il modello dei blocchi va in `app/models/friendship.py`.
- *Nota*: nella prima versione nessun altro punto aggiunge migrazioni. Se ne serve una, è un punto nuovo da concordare.
- *Fatto quando*: su un database vuoto `migrate.py` crea tutte le tabelle; rilanciato non fa niente [T].
- *Dipende da*: P4 per `migrate.py` e i modelli. I due file SQL possono partire in parallelo a P4.

**P6 — Runner dei test** · medio · decisione: no
- *Cosa e perché*: un solo comando lancia tutte le prove in sicurezza. Ogni suite è una cartella di `tests/` (`runner`, `engine`, `db`, `api`, `services`, `sockets`, `frontend`, `e2e`).
- *Requisiti*:
  - **si rifiuta di partire** se trova il file `PRODUZIONE` nella cartella del progetto, o se il database dei test non finisce con `_test`;
  - controlla che la **porta di test 5099** sia libera; se è occupata si ferma e lo dice;
  - esegue le suite **una dopo l'altra**, ognuna con un **tempo massimo** (es. 120 s); se lo supera la ferma e la segna FAIL;
  - prima di partire calcola un **hash** (un'impronta del contenuto) dei file protetti (`.env.example`, `migrations/*.sql`, `app/static/dev/*.json`) e ne fa una copia fuori dal progetto. **Dopo ogni suite** ricontrolla l'hash e, se un file è cambiato, lo ripristina e lo segnala;
  - alla fine **svuota il database di test**, cancella copie e file temporanei, e stampa un **riepilogo** con PASS/FAIL e la durata di ogni suite.
- *File* — crea: `tests/esegui_tutti.py`, `tests/conftest.py`, `tests/runner/test_esegui_tutti.py`. Certezza: **sicuro**.
- *Fatto quando*: test del runner per ogni caso [T]: `PRODUZIONE` presente → rifiuto; porta occupata → stop; suite troppo lunga → FAIL; file protetto modificato → ripristinato; riepilogo corretto.
- *Dipende da*: P4, P5.

**P7 — Log ed errori** · piccolo · decisione: no
- *Cosa e perché*: i log (il registro di cosa succede nel server) vanno in `logs/` con rotazione, cioè i file vecchi vengono sostituiti. Livelli distinti: INFO per gli eventi normali, WARNING/ERROR per le anomalie. **Mai** dati personali, password, token o **testo dei messaggi della chat** nei log. Pagine 404 e 500 in italiano; gli errori degli eventi socket vanno solo a chi li ha causati.
- *File* — modifica: `app/logging_config.py`, `app/errors.py` (segnaposto di P4). Crea: `app/templates/errors/404.html`, `app/templates/errors/500.html`, `tests/api/test_errori.py`. Certezza: **sicuro**.
- *Fatto quando*: pagina inesistente → 404; errore forzato → pagina 500 senza dettagli tecnici e riga ERROR nel log [T]; la password usata in un login di prova non compare nel log.
- *Dipende da*: P4, P6.

**P8 — Contratto tra server e pagine** · piccolo · **decisione: sì** (approvare il contratto)
- *Cosa e perché*: un documento che fissa i **nomi degli eventi socket** e i dati di ciascuno per: partita (`game:play_card`, `game:sing`, …), code di matchmaking (con modalità e punteggio), home (utenti online, rientro in partita), amici (presenza, richieste, inviti) e chat. Fissa anche il **formato della vista di gioco** (la tua mano, il numero di carte degli altri, il tavolo, la briscola, i punteggi, il punteggio per vincere, le mosse legali, il timer) e il formato dei dati di home, pannello statistiche e amici. Serve a far lavorare **in parallelo** i filoni.
- *File* — crea: `docs/CONTRATTO-SOCKET.md`, `app/static/dev/vista_1v1.json`, `app/static/dev/vista_2v2.json`, `app/static/dev/home_esempio.json`, `app/static/dev/amici_esempio.json`. Certezza: **sicuro**. Gli esempi stanno in `static/dev/` perché li usano sia le pagine (dati finti) sia i test.
- *Fatto quando*: l'utente ha approvato il contratto e i file di esempio lo rispettano.
- *Dipende da*: nessuno.

**P9 — Guida di installazione verificata** · piccolo · decisione: no
- *Cosa e perché*: il `README.md` ha già la struttura e i passi previsti. Qui si **verificano** e si correggono i comandi sul progetto vero.
- *File* — modifica: `README.md`. Certezza: **sicuro**.
- *Fatto quando*: un compagno, seguendo solo il README su un altro PC, avvia il gioco e fa passare i test.
- *Dipende da*: P4, P5, P6.

**P52 — Prototipo della home** · medio · decisione: no — **fatto il 27/09/2026**
- *Cosa e perché*: la home disegnata **prima di tutto il resto** come prototipo statico, che si apre con un doppio clic nel browser, senza Flask né database. È il **riferimento grafico** di P19, P40 e P22: il server non lo usa e **nessuno lo modifica**. Dopo alcune prove (un primo prototipo scartato, quattro palette a confronto) l'utente ha approvato la versione descritta in `DECISIONI.md`, sezione Interfaccia (27/09/2026): palette "Carretto siciliano", navbar trasparente e sfocata, home senza scorrimento con le carte-pulsante di Partita Veloce e Gioca con un amico, modal dei punti e degli inviti, pannelli statistiche e amici, sfondo di carte siciliane messe da uno script negli spazi vuoti.
- *File* — creati: `docs/prototipo/index.html`, `prototipo.css`, `prototipo.js`, `LEGGIMI.md`, `docs/prototipo/img/` (16 carte siciliane da Wikimedia, CC BY-SA 3.0, e il seme di denari, pubblico dominio).
- *Fatto quando*: `index.html` si apre con un doppio clic e mostra tutti gli stati (anche con `?apri=`); la pagina non scorre alle misure elencate in `LEGGIMI.md`; `LEGGIMI.md` elenca risorse esterne, font, licenze e quale punto riprende ciascuna parte. **Fatto** [T]: controlli con screenshot e misure a 9 dimensioni di schermo.
- *Dipende da*: P1.

### Fase 2 — Funzioni essenziali (giorni 2–6)

#### Motore di gioco (A)

**P10 — Carte, mazzo, parametri delle regole** · piccolo · decisione: no
- *Cosa e perché*: classi per carta, seme e valore; forza nella presa e punti; mazzo da 40 mescolato con un generatore casuale sicuro (`secrets.SystemRandom`), con un seme fisso nei test; `RuleSet` con i parametri della variante (tra cui i punteggi per vincere ammessi: 150, 300, 500); errori delle mosse non valide.
- *File* — crea: `app/game/engine/cards.py`, `deck.py`, `rules.py`, `errors.py`, `tests/engine/test_carte_mazzo.py`. Certezza: **sicuro**.
- *Fatto quando*: il mazzo ha 40 carte tutte diverse; la somma dei punti è 120; l'ordine di forza è A > 3 > R > C > F > 7 > 6 > 5 > 4 > 2.
- *Dipende da*: P4. I test del motore si possono lanciare con `pytest tests/engine` anche prima che il runner P6 sia pronto.

**P11 — Chi vince la presa** · piccolo · decisione: no
- *File* — crea: `app/game/engine/trick.py`, `tests/engine/test_presa.py`. Certezza: **sicuro**.
- *Fatto quando*: test per ogni caso: senza briscola vince la più forte del seme giocato per primo e le carte di altri semi non prendono; con la briscola vince la briscola più forte; con la briscola ma nessuna briscola giocata vince il seme giocato per primo; stessi casi con 4 carte (2v2).
- *Dipende da*: P10.

**P12 — Cantare 40 e 20** · medio · decisione: no
- *File* — crea: `app/game/engine/singing.py`, `tests/engine/test_canti.py`. Certezza: **sicuro**.
- *Fatto quando*: test: il primo canto vale 40 e fissa la briscola; il secondo vale 20 e non la cambia; due canti nello stesso turno sono ammessi; non si canta fuori turno o dopo aver giocato la carta; non si canta se il Re o il Cavallo di quel seme è già stato giocato; non si canta con una coppia divisa tra compagni; a mazzo finito si canta con 3 o più carte ma non con 2; lo stesso seme non si canta due volte.
- *Dipende da*: P10, P11.

**P13 — Svolgimento di una mano** · medio · decisione: no
- *Cosa e perché*: stato della mano e `apply(stato, azione) → nuovo stato`: turni in senso antiorario, pesca (prima chi ha vinto la presa), fine del mazzo senza cambiare le regole, fine mano e conteggio; squadre nel 2v2.
- *File* — crea: `app/game/engine/state.py`, `actions.py`, `game.py`, `tests/engine/test_mano.py`. Certezza: **sicuro**.
- *Fatto quando*: una mano 1v1 e una 2v2 giocate con seme fisso finiscono con 120 punti di carte in totale; l'ordine di pesca è corretto; una mossa non valida viene **rifiutata con un errore chiaro** e lo stato non cambia.
- *Dipende da*: P11, P12.

**P14 — Partita fino al punteggio scelto** · piccolo · decisione: **D11**
- *Cosa e perché*: la partita finisce quando qualcuno arriva al punteggio scelto all'inizio (150, 300 o 500, dal modal della home). Un punteggio diverso da questi tre viene rifiutato.
- *File* — modifica: `app/game/engine/game.py`, `app/game/engine/state.py` (P13). Crea: `tests/engine/test_partita.py`. Certezza: **sicuro**.
- *Fatto quando*: per ognuno dei tre punteggi, la partita finisce solo a fine mano; vince chi arriva ad almeno N (con N esatti si vince); se ci arrivano entrambi vince il più alto; a parità è pareggio; arrivare a N durante la mano con un canto non chiude la partita; un punteggio fuori elenco viene rifiutato.
- *Dipende da*: P13.

**P15 — Vista per giocatore, mosse legali, mossa automatica** · medio · decisione: **D12**
- *Cosa e perché*: dallo stato completo si ricava la vista di **un** giocatore, senza le carte degli altri né l'ordine del mazzo. È la difesa principale contro chi prova a imbrogliare.
- *File* — crea: `app/game/engine/views.py`, `auto_move.py`, `tests/engine/test_viste.py`, `tests/engine/test_mossa_automatica.py`. Certezza: **sicuro**.
- *Fatto quando*: la vista non contiene mai carte che il giocatore non può vedere (controllo su tutte le posizioni di una partita intera); le mosse legali coincidono con quelle che `apply` accetta; la mossa automatica è sempre legale; la vista ha lo stesso formato di `app/static/dev/vista_*.json`.
- *Dipende da*: P13, P8.

#### Account e dati (B)

**P16 — Registrazione, login, logout** · medio · decisione: **D7, D8**
- *Cosa e perché*: moduli con protezione CSRF (un codice segreto nel modulo che impedisce a un altro sito di inviarlo al posto dell'utente, tramite Flask-WTF), password salvate solo come hash, sessione con Flask-Login, messaggi chiari, limite ai tentativi di login ripetuti.
- *File* — modifica: `app/blueprints/auth/__init__.py`, `app/blueprints/auth/routes.py` (segnaposto di P4). Crea: `app/blueprints/auth/forms.py`, `app/services/auth_service.py`, `app/repositories/user_repo.py`, `app/templates/auth/login.html`, `app/templates/auth/register.html`, `tests/api/test_auth.py`. Certezza: **sicuro**. Lo stile viene dalle classi CSS di P19, senza modificarne i file.
- *Fatto quando*: registrazione ok; username duplicato → errore; password sbagliata → errore generico; dopo il logout le pagine protette rimandano al login; nel database non c'è la password in chiaro; dopo N tentativi sbagliati → attesa.
- *Dipende da*: P5, P7, P19.

**P17 — Impostazioni: avatar e cancellazione dell'account** · piccolo · decisione: **D6** (già applicata in P5), **D29**
- *Cosa e perché*: la pagina "Impostazioni" (dal link nel pannello statistiche dell'avatar) permette di **scegliere un avatar** da un set predefinito e di **cancellare l'account**. `avatars.py` contiene l'elenco degli avatar ammessi: il server rifiuta qualunque valore fuori elenco. Finché le immagini non ci sono (P43), la pagina mostra il nome o il numero di ogni avatar.
- *File* — modifica: `app/blueprints/profile/routes.py` (P4), `app/services/auth_service.py`, `app/repositories/user_repo.py` (P16). Crea: `app/services/avatars.py`, `app/templates/profile/settings.html`, `app/static/js/pages/profile.js`, `app/static/css/pages/profile.css`, `tests/api/test_impostazioni.py`. Certezza: **sicuro**.
- *Fatto quando*: l'avatar scelto viene salvato; un avatar fuori elenco viene rifiutato; dopo la conferma (con la finestra nella pagina di P19, non `confirm()`) l'utente non esiste più, il login fallisce, e le partite restano come deciso in D6.
- *Dipende da*: P16, P40.

**P18 — Backup e ripristino** · piccolo · decisione: **D10**
- *Cosa e perché*: `backup.py` lancia `mysqldump`, salva un file compresso con la data in `backups/` e cancella quelli più vecchi di D10 giorni. `ripristina.py` ricarica un backup **in un database indicato**, e chiede conferma se non è di test.
- *File* — crea: `scripts/backup.py`, `scripts/ripristina.py`, `tests/db/test_backup.py`. Certezza: **sicuro**.
- *Fatto quando*: sul database di test: backup → modifica dei dati → ripristino → dati identici a prima [T].
- *Dipende da*: P5, P6.

**P45 — Amicizie** · medio · decisione: **D23, D26, D33**
- *Cosa e perché*: cercare un utente per username e mandargli una **richiesta di amicizia**; accettare, rifiutare, annullare una richiesta; rimuovere un amico; vedere la lista degli amici e delle richieste in arrivo (con il numero per il contatore nella navbar). Sono richieste HTTP in JSON, protette da CSRF. Se D23 = sì, anche "blocca utente".
- *File* — modifica: `app/blueprints/friends/__init__.py`, `app/blueprints/friends/routes.py` (segnaposto di P4). Crea: `app/services/friend_service.py`, `app/repositories/friend_repo.py`, `tests/api/test_amicizie.py`. Certezza: **sicuro**.
- *Fatto quando*: test via HTTP: richiesta → accettazione → i due sono amici; una richiesta doppia o a sé stessi viene rifiutata; rimuovere un amico lo toglie per entrambi; un utente bloccato non può mandare richieste (se D23 = sì); si rispetta il limite di D26.
- *Dipende da*: P5, P16.

**P26 — Salvataggio delle partite** · piccolo · decisione: no
- *Cosa e perché*: a fine partita si salvano risultato, giocatori ed eventi **in una sola transazione** (o tutto o niente).
- *File* — crea: `app/services/match_service.py`, `app/repositories/match_repo.py`, `tests/services/test_match_service.py`. Modifica: `app/realtime/room.py` (P25), **solo** per aggiungere la chiamata al salvataggio a fine partita. Certezza: **sicuro**.
- *Fatto quando*: dopo una partita simulata, nel database di test ci sono partita, giocatori ed eventi in ordine; un errore a metà salvataggio non lascia dati parziali.
- *Dipende da*: P5 per service, repository e test; P25 solo per la modifica a `room.py`, che si fa per ultima.

**P27 — Rating Glicko-2** · medio · decisione: **D9**
- *File* — crea: `app/services/glicko2.py`, `app/services/rating_service.py`, `app/repositories/rating_repo.py`, `tests/services/test_glicko2.py`, `tests/services/test_rating_service.py`. Modifica: `app/services/match_service.py` (P26). Certezza: **sicuro**.
- *Fatto quando*: test contro l'esempio numerico ufficiale di Glicko-2 (documento di Glickman) [T]; il pareggio conta 0.5; il 1v1 contro un amico non cambia il rating, il 2v2 con un amico come compagno sì; il rating conta allo stesso modo a 150, 300 e 500 punti; 1v1 e 2v2 separati; aggiornamento nella stessa transazione del salvataggio.
- *Dipende da*: P26 (service e repository).

#### Interfaccia (C)

**P19 — Base grafica mobile-first** · medio · decisione: **D18** (solo per il tavolo di gioco)
- *Cosa e perché*: struttura comune delle pagine con lo spazio per la navbar (riempito da P40) e la pagina alta quanto lo schermo, senza scorrimento, variabili CSS (colori, spazi, font), messaggi, finestra di conferma riutilizzabile. Si progetta per **360 px di larghezza** e poi si allarga. **Colori (palette "Carretto siciliano"), font (Fredoka, Nunito) e spazi si prendono dal prototipo di P52** e si riscrivono come variabili CSS nei nostri file, per il **solo tema chiaro**: il tema scuro è rimandato alla fine (P53), ma i colori vanno usati **sempre tramite le variabili**, così P53 dovrà solo aggiungere i valori scuri. Le risorse esterne del prototipo (font, icone, librerie CSS da CDN) si caricano **una volta sola in `base.html`**, così valgono per tutte le pagine.
- *File* — crea: `app/templates/base.html`, `app/templates/partials/flash.html`, `app/static/css/base/reset.css`, `variables.css`, `typography.css`, `layout.css`, `app/static/css/components/button.css`, `form.css`, `modal.css`, `app/static/css/pages/auth.css`, `app/static/js/components/Modal.js`, `app/static/js/utils/dom.js`, `tests/frontend/test_base.py`. Modifica: `app/templates/main/index.html` (P4), `app/templates/errors/404.html`, `500.html` (P7). Certezza: **sicuro**.
- *Fatto quando*: a 360 px le pagine sono leggibili senza scorrimento orizzontale; i colori coincidono con quelli del prototipo; nei CSS non ci sono colori scritti a mano fuori da `variables.css`; il test controlla che ogni pagina abbia il `meta viewport`, carichi un solo script di pagina, e che le risorse esterne siano solo quelle elencate in `docs/prototipo/LEGGIMI.md`.
- *Dipende da*: P4, P7, P52.

**P40 — Navbar, pannello statistiche, finestra "Accedi o registrati"** · medio · decisione: no
- *Cosa e perché*: si parte dalla navbar del **prototipo di P52**. Il suo HTML va in `partials/navbar.html`, incluso da `base.html` con `{% include %}`: così compare in ogni pagina senza essere ricopiato. Lo stile va nei CSS dei componenti e il comportamento in `layout.js`. Dove il prototipo e le decisioni non coincidono, valgono le decisioni (`DECISIONI.md`, sezione Interfaccia).
  - **navbar trasparente e sfocata**: avatar a sinistra (per ora iniziali su un cerchio colorato), nome **"Cinquecento"** al centro con il seme di denari (il logo vero arriva in P42), pulsante amici a destra con il contatore (il pannello arriva in P46); su computer, accanto all'avatar e all'icona, il nome e la scritta "Amici";
  - **pannello statistiche**: si apre toccando l'avatar; mostra partite, vinte, perse, percentuale e rating 1v1 e 2v2 (per ora con i dati finti di `app/static/dev/home_esempio.json`, quelli veri arrivano in P30) e i link **Impostazioni** ed **Esci**; in fondo, piccola, la riga dei crediti delle immagini: "Carte dello sfondo: Matsoftware, CC BY-SA 3.0, da Wikimedia Commons" con il collegamento alla licenza;
  - **finestra "Accedi o registrati per giocare"**, riutilizzabile dalle altre pagine;
  - `core/layout.js`: il modulo che **ogni pagina importa** per far funzionare navbar, pannello statistiche e, più avanti, il pannello amici.
- *File* — crea: `app/templates/partials/navbar.html`, `app/static/css/components/navbar.css`, `stats-panel.css`, `app/static/js/core/layout.js`, `app/static/js/components/StatsPanel.js`, `app/static/js/components/LoginPrompt.js`, `app/static/img/seme-denari.svg` (dal prototipo), `tests/frontend/test_navbar.py`. Modifica: `app/templates/base.html` (P19). Certezza: **sicuro**.
- *Fatto quando*: a 360 px la navbar sta sullo schermo senza sovrapporsi al contenuto e ha l'aspetto del prototipo; il pannello statistiche si apre e si chiude anche con la tastiera e con Esc; ogni pulsante con sola icona ha un'etichetta accessibile; il test controlla che la navbar abbia avatar, nome del gioco e pulsante amici.
- *Dipende da*: P19.

**P20 — Componenti carta e mano** · medio · decisione: no
- *Cosa e perché*: la carta disegnata in CSS come segnaposto, il dorso, la mano che sta in uno schermo di telefono; componenti come funzioni che restituiscono elementi, sempre con `textContent`.
- *File* — crea: `app/static/js/components/Card.js`, `Hand.js`, `app/static/css/components/card.css`, `hand.css`, `app/static/dev/carte.html`, `app/static/dev/carte.js` (pagina di prova con le 40 carte). Certezza: **sicuro**.
- *Fatto quando*: la pagina di prova mostra le 40 carte e una mano da 5 a 360 px; ogni carta ha attributi `data-suit` e `data-rank` stabili.
- *Dipende da*: P19.

**P21 — Tavolo di gioco con dati finti** · medio · decisione: **D15**
- *Cosa e perché*: il tavolo (la tua mano, gli avversari coperti, la presa in corso, la briscola, i punteggi, il timer, i pulsanti "Canta 40/20"), disegnato da un'**unica funzione `render(vista)`** a partire da `app/static/dev/vista_*.json`. C'è un pulsante "esci" con conferma.
- *File* — crea: `app/templates/game/table.html`, `app/static/js/pages/game.js`, `app/static/js/components/Table.js`, `Trick.js`, `Scoreboard.js`, `Timer.js`, `SingButtons.js`, `app/static/css/components/table.css`, `trick.css`, `scoreboard.css`, `timer.css`, `app/static/css/pages/game.css`, `tests/api/test_pagina_tavolo.py`. Modifica: `app/blueprints/game/routes.py` (P4). Certezza: **sicuro**.
- *Fatto quando*: con `?demo=1v1` e `?demo=2v2` il tavolo si vede correttamente; i pulsanti delle mosse non legali sono disattivati; il test verifica che la pagina risponda e contenga i marcatori `data-*`.
- *Dipende da*: P8, P20, P40.

**P22 — Home con dati finti** · medio · decisione: no (specifiche dal prototipo approvato)
- *Cosa e perché*: la home del **prototipo di P52**, riscritta nei file del progetto:
  - "**giocatori online**" al centro, sotto la navbar;
  - sezioni **Partita Veloce** e **Gioca con un amico**, ciascuna con due **carte-pulsante 1v1 e 2v2** (rosso, verde, giallo, blu; icona, modalità e sottotitolo in bianco; forma di carta siciliana); su telefono una sotto l'altra, da 900 px affiancate; su telefono in orizzontale le quattro carte su una fila;
  - la pagina **non scorre mai**: le carte si rimpiccioliscono sugli schermi bassi (`--tile-h` del prototipo);
  - **modal della modalità**: punti per vincere (150, 300, 500) e "Gioca"; in "Gioca con un amico" anche la lista degli amici online con "Invita", e "Gioca" si attiva solo dopo che l'amico ha accettato (dati finti; la coda arriva in P28, gli inviti veri in P47);
  - **sfondo**: carte siciliane (coppie Cavallo + Re, Assi, Tre) messe negli spazi vuoti dallo script del prototipo, riscritto come componente;
  - la **schermata di attesa in coda** a tutto schermo (tempo trascorso, intervallo di rating, "Annulla") e l'avviso "**Hai una partita in corso: rientra**" (solo quando serve);
  - per chi non ha fatto il login, il tocco su una carta-pulsante apre la finestra "Accedi o registrati" (P40).

  Tutto funziona con `app/static/dev/home_esempio.json`. In `index.html` resta **solo il markup della home**, che estende `base.html`; niente blocchi `<style>` né codice JS nella pagina. Le immagini dello sfondo hanno licenza CC BY-SA 3.0: la riga di crediti sta in fondo al pannello statistiche (P40).
- *File* — crea: `app/static/js/pages/home.js`, `app/static/css/pages/home.css`, `app/static/js/components/ModeModal.js`, `app/static/css/components/mode-modal.css`, `app/static/js/components/CardBackground.js`, `app/static/css/components/card-background.css`, `app/static/img/cards-bg/` (le 16 carte del prototipo, con `LICENZA.md`), `app/static/js/components/QueueOverlay.js`, `app/static/css/components/queue-overlay.css`, `app/static/js/components/ResumeBanner.js`, `tests/api/test_pagina_home.py`. Modifica: `app/templates/main/index.html` (P19), `app/blueprints/main/routes.py` (P4). Certezza: **sicuro**.
- *Fatto quando*: la home ha l'aspetto del prototipo a 360 px, su tablet e su computer; la pagina non scorre a nessuna misura (stesse misure controllate in `docs/prototipo/LEGGIMI.md`); il modal si apre da ogni carta-pulsante e "Gioca" con un amico resta disattivato finché l'invito finto non è accettato; senza login il tocco apre la finestra di accesso; la schermata di coda si apre e si annulla; l'avviso di rientro compare solo se i dati finti lo prevedono; le carte dello sfondo non si sovrappongono e non coprono titoli e "giocatori online"; il test controlla che `index.html` non contenga blocchi `<style>` né script scritti nella pagina.
- *Dipende da*: P8, P40, P52.

**P41 — Pagina stanza privata con dati finti** · **tolto il 27/09/2026** per decisione dell'utente (vedi `DECISIONI.md`, Progetto e tempi). Le partite tra amici passano dagli inviti (P47).

**P46 — Pannello amici e finestra chat con dati finti** · medio · decisione: **D25**
- *Cosa e perché*: dal **prototipo di P52**. Al tocco sull'icona amici (in alto a destra) si apre un **pannello laterale** (a tutto schermo su telefono) con: campo per cercare uno username e mandare una richiesta, richieste in arrivo (accetta o rifiuta), lista amici con il pallino online o offline, e per ogni amico i pulsanti **Chatta**, **Invita 1v1** e **Invita 2v2**. "Chatta" apre la **finestra chat**, che su telefono occupa tutto lo schermo. Tutto con `app/static/dev/amici_esempio.json`. Il testo dei messaggi è sempre inserito con `textContent`.
- *File* — crea: `app/static/js/components/FriendsPanel.js`, `ChatWindow.js`, `app/static/css/components/friends-panel.css`, `chat.css`, `tests/frontend/test_pannello_amici.py`. Modifica: `app/static/js/core/layout.js` (P40). Certezza: **sicuro**.
- *Fatto quando*: il pannello si apre da qualsiasi pagina (tranne il tavolo, dove resta chiuso) e si chiude con "indietro" o con Esc; a 360 px la chat è leggibile e il campo di scrittura resta visibile; il test controlla che i componenti non usino `innerHTML` con dati esterni.
- *Dipende da*: P8, P40.

**P51 — Pagina "Regole" con mini-tutorial** · **tolto il 27/09/2026** per decisione dell'utente (vedi `DECISIONI.md`, Progetto e tempi).

#### Tempo reale e integrazione (I)

**P23 — Collegamento in tempo reale** · medio · decisione: **D14**
- *Cosa e perché*: Flask-SocketIO in modalità threading; si collega solo chi ha fatto il login; `RoomManager` tiene le stanze in memoria con **un lock per stanza**. Lato pagina, `core/socket.js` gestisce connessione e riconnessione automatica.
- *File* — crea: `app/realtime/events.py`, `room.py`, `room_manager.py`, `app/static/js/core/socket.js`, `app/static/js/core/events.js`, `app/static/js/vendor/socket.io.min.js` (versione fissa, annotata in testa al file), `tests/sockets/conftest.py`, `tests/sockets/test_connessione.py`, `tests/sockets/test_lock_stanza.py`. Modifica: `app/sockets/__init__.py`, `app/sockets/connection_events.py` (P4). Certezza: **sicuro**.
- *Fatto quando*: test con client simulati: un utente senza login viene rifiutato; due utenti nella stessa stanza ricevono gli eventi; 50 azioni inviate insieme vengono elaborate una alla volta senza errori.
- *Dipende da*: P16, P8.

**P24 — Stanze e partita completa** · medio · decisione: no
- *Cosa e perché*: il primo momento in cui **si gioca davvero**: il server crea una stanza con i giocatori, la modalità e il punteggio scelto, la partita parte e il server applica il motore. Ognuno riceve **solo la propria vista**. Non esistono più le stanze private con codice: le stanze le crea solo il server. `room_manager.py` **espone** due funzioni che poi usano altri punti senza modificare il file: `create_room(giocatori, modalità, punteggio)`, per la coda (P28, P29) e per gli inviti (P47), e `find_room_of_user(...)`, per il rientro in partita (P44).
- *File* — modifica: `app/realtime/room.py`, `room_manager.py` (P23), `app/sockets/game_events.py` (P4), `app/static/js/pages/game.js` (P21). Crea: `tests/sockets/test_partita.py`. Certezza: **sicuro**.
- *Fatto quando*: test con client simulati: una partita 1v1 e una 2v2 fino al punteggio (a 150 per fare prima), con la stanza creata da `create_room`; una mossa illegale riceve un errore e non cambia niente; le due funzioni esposte hanno un test. La prova a mano con due browser si fa da P28, quando c'è la coda.
- *Dipende da*: P15, P21, P23.

**P25 — Timer, riconnessione, abbandono** · medio · decisione: **D12, D13**
- *File* — modifica: `app/realtime/room.py` (P24), `app/sockets/game_events.py` (P24), `app/sockets/connection_events.py` (P23), `app/static/js/pages/game.js` (P24). Crea: `tests/sockets/test_timer_riconnessione.py`. Certezza: **sicuro**.
- *Fatto quando*: con i tempi ridotti dalla configurazione di test: a turno scaduto il server gioca la mossa automatica; chi si riconnette in tempo riceve di nuovo la sua vista; oltre il tempo la partita finisce per abbandono.
- *Dipende da*: P24.

**P28 — Matchmaking 1v1** · medio · decisione: **D16**
- *Cosa e perché*: "Gioca" nel modal di Partita Veloce mette il giocatore in coda per la modalità **e il punteggio** scelti (code separate); quando trova un avversario il server crea la stanza con `create_room` (P24) e porta entrambi al tavolo.
- *File* — crea: `app/realtime/matchmaking.py`, `tests/sockets/test_matchmaking_1v1.py`. Modifica: `app/sockets/lobby_events.py` (P4), `app/sockets/__init__.py` (P23, per avviare il controllo periodico delle code), `app/static/js/pages/home.js` e `app/static/js/components/ModeModal.js` (P22, per collegare "Gioca" e la schermata di coda). Certezza: **sicuro**.
- *Fatto quando*: due giocatori con rating vicino e stesso punteggio vengono abbinati subito; con punteggi diversi no; con rating lontani solo dopo che la tolleranza si è allargata; chi annulla esce dalla coda; lo stesso utente non può stare due volte in coda (doppio clic, due schede).
- *Dipende da*: P22, P24, P27.

**P29 — Matchmaking 2v2** · medio · decisione: **D17**
- *Cosa e perché*: la coda 2v2 accetta sia **giocatori singoli** sia **coppie già formate** (l'amico compagno invitato con "Gioca con un amico", P47). Una coppia resta sempre nella stessa squadra.
- *File* — modifica: `app/realtime/matchmaking.py`, `app/sockets/lobby_events.py`, `app/static/js/pages/home.js` (P28). Crea: `tests/sockets/test_matchmaking_2v2.py`. Certezza: **sicuro**.
- *Fatto quando*: 4 giocatori singoli formano una partita con squadre bilanciate; una coppia già formata viene abbinata a due avversari (singoli o un'altra coppia) e resta unita; chi esce dalla coda prima dell'abbinamento non blocca gli altri (se esce uno della coppia, esce tutta la coppia).
- *Dipende da*: P28.

**P44 — Home con dati reali** · piccolo · decisione: no
- *Cosa e perché*: la home riceve dal server, appena la pagina si collega, **quanti utenti sono online** e l'eventuale **partita in corso** da cui rientrare (tramite `find_room_of_user` di P24). `presence.py` tiene l'elenco di chi è online: lo usa anche P47 per il pallino degli amici.
- *File* — crea: `app/realtime/presence.py`, `app/sockets/home_events.py`, `tests/sockets/test_home_stato.py`. Modifica: `app/sockets/__init__.py` (P28, per registrare `home_events`), `app/sockets/connection_events.py` (P25, per segnare chi entra ed esce), `app/static/js/pages/home.js` (P29). Certezza: **sicuro**.
- *Fatto quando*: test con client simulati: il numero di utenti online sale e scende con le connessioni (lo stesso utente con due schede conta una volta sola); un utente con una partita in corso riceve il link per rientrare.
- *Dipende da*: P25, P29.

**P47 — Amici online e inviti a partita** · medio · decisione: **D27**
- *Cosa e perché*: il pannello amici mostra **chi è online** in tempo reale e riceve le richieste di amicizia senza ricaricare la pagina. Nel modal di **Gioca con un amico** la lista degli amici online diventa vera: "Invita" manda l'invito, l'amico lo riceve con un conto alla rovescia, e **"Gioca" si attiva solo quando ha accettato**. Poi:
  - **1v1**: il server crea subito la stanza con i due amici (`create_room` di P24);
  - **2v2**: i due amici entrano **insieme** nella coda 2v2 come coppia (P29), e gli avversari arrivano dal matchmaking.

  Il 1v1 contro un amico **non conta per il rating**; il 2v2 con un amico come compagno **conta**. Il pannello passa dai dati finti a quelli veri (API di P45 ed eventi socket).
- *File* — crea: `app/realtime/invites.py`, `tests/sockets/test_inviti.py`. Modifica: `app/sockets/friends_events.py` (P4), `app/static/js/components/FriendsPanel.js` (P46), `app/static/js/components/ModeModal.js` (P28). Certezza: **sicuro**.
- *Fatto quando*: test con client simulati: un amico che si collega appare online agli altri; un invito 1v1 accettato porta i due nella stessa stanza; un invito 2v2 accettato mette la coppia in coda; un invito scaduto o rifiutato avvisa chi l'ha mandato; non si può invitare chi non è amico o chi è già in partita.
- *Dipende da*: P24, P29, P44, P45, P46.

**P48 — Chat tra amici** · medio · decisione: **D24, D25, D26**
- *Cosa e perché*: messaggi in tempo reale **solo tra amici**, salvati nel database, con la cronologia che si carica all'apertura della chat e un contatore dei messaggi non letti. Protezioni: lunghezza massima e limite di frequenza (D26), testo sempre mostrato come testo, mai nei log; i messaggi più vecchi di D24 giorni vengono cancellati.
- *File* — crea: `app/services/chat_service.py`, `app/repositories/chat_repo.py`, `tests/sockets/test_chat.py`. Modifica: `app/sockets/chat_events.py` (P4), `app/static/js/components/ChatWindow.js` (P46). Certezza: **sicuro**.
- *Fatto quando*: test con client simulati: un messaggio arriva solo al destinatario; a chi non è amico il messaggio viene rifiutato; un messaggio troppo lungo o troppo frequente viene rifiutato con un avviso; un messaggio con `<script>` viene mostrato come testo; la cronologia si carica in ordine; la cancellazione dei messaggi vecchi funziona sul database di test.
- *Dipende da*: P23, P45, P46.

#### Pagine con i dati (B + C)

**P30 — Pannello statistiche con dati reali** · medio · decisione: no
- *Cosa e perché*: il pannello che si apre dall'avatar (P40) mostra i dati veri: partite giocate, vinte, perse, percentuale di vittorie, rating attuale 1v1 e 2v2. I dati arrivano da una richiesta JSON al server.
- *File* — crea: `app/services/stats_service.py`, `app/repositories/stats_repo.py`, `tests/api/test_statistiche.py`. Modifica: `app/blueprints/stats/routes.py` (P4), `app/static/js/components/StatsPanel.js` (P40). Certezza: **sicuro**.
- *Fatto quando*: dopo partite simulate note, le cifre del pannello coincidono con quelle attese; un utente vede solo le proprie statistiche; il pannello si legge bene a 360 px.
- *Dipende da*: P26, P27, P40.

**P49 — Classifica** · **tolto il 27/09/2026** per decisione dell'utente (vedi `DECISIONI.md`, Progetto e tempi).

**P50 — Pagina "Partite" (storico)** · **tolto il 27/09/2026** per decisione dell'utente (vedi `DECISIONI.md`, Progetto e tempi). Le partite si salvano comunque (P26) per statistiche e rating.

### Fase 3 — Robustezza (giorno 6)

**P31 — Test end-to-end** · medio · decisione: no
- *Cosa e perché*: server vero sulla porta 5099, client simulati che si registrano, diventano amici, si invitano, chattano, entrano in coda e giocano partite intere 1v1 e 2v2. Casi limite: doppio clic su "gioca carta", stesso utente in due schede, disconnessione a metà, mossa fuori turno.
- *File* — crea: `tests/e2e/conftest.py`, `tests/e2e/test_partita_1v1.py`, `tests/e2e/test_partita_2v2.py`, `tests/e2e/test_amici_inviti_chat.py`, `tests/e2e/test_casi_limite.py`. Certezza: **sicuro** per i file di test. Se i test trovano bug, le correzioni sono punti nuovi, con i loro file.
- *Fatto quando*: la suite `e2e` passa nel runner; la vista ricevuta da ciascun client non contiene mai carte altrui.
- *Dipende da*: P25, P29, P47, P48.

**P32 — Sicurezza di base** · medio · decisione: no — **file non tutti sicuri, vedi sezione 9.2**
- *Cosa e perché*: controllo generale: CSRF su tutti i moduli e le richieste JSON; cookie di sessione `HttpOnly` e `SameSite`; validazione sul server di **ogni** dato che arriva dagli eventi socket; limite di frequenza per gli eventi; intestazioni di sicurezza; testo degli utenti (username, chat) mai inserito come HTML.
- *Fatto quando*: un evento con dati malformati riceve un errore e non fa cadere la stanza; una richiesta senza token CSRF viene rifiutata; uno username o un messaggio con `<script>` viene mostrato come testo.
- *Dipende da*: P24, P16, P45, P48.

**P33 — Errori e connessione nell'interfaccia** · piccolo · decisione: no — **file non tutti sicuri, vedi sezione 9.2**
- *Fatto quando*: se la connessione cade compare un avviso nella pagina e i pulsanti si disattivano; al ritorno la vista si aggiorna da sola; nessun `alert`/`confirm`/`prompt` nel codice (controllato dal test).
- *Dipende da*: P23, P29, P44, P47, P48.

### Fase 4 — Rifiniture e revisione (giorni 6–7)

**P34 — Rifinitura mobile e accessibilità** · piccolo · decisione: no — **file da definire, vedi sezione 9.2**
- *Fatto quando*: tutte le pagine si usano a 360 px e su un telefono vero; i pulsanti con sola icona hanno un'etichetta accessibile (`aria-label`); il contrasto è sufficiente; si gioca anche con la tastiera.
- *Dipende da*: P30, P33.

**P35 — Carte vere** · piccolo · **decisione: sì** (D19) — **file non tutti sicuri, vedi sezione 9.2**
- *Cosa e perché*: come deciso, prima si prova un **set con licenza libera**, poi lo si confronta con le vostre immagini.
- *Fatto quando*: le 40 carte si vedono con le immagini scelte, la licenza è annotata, e il peso totale è sotto 1 MB.
- *Dipende da*: P20.

**P42 — Logo vero** · piccolo · decisione: no (logo "Cinquecento" disegnato da Claude in SVG, vedi `DECISIONI.md`) — **file non tutti sicuri, vedi sezione 9.2**
- *Cosa e perché*: il logo **"Cinquecento"** al centro della navbar, leggibile a 40 px di altezza, più l'icona della scheda del browser (favicon). Parte dal nome con il seme di denari del prototipo di P52.
- *Fatto quando*: il logo si vede nitido a 40 px su telefono e computer (anche in tema scuro, se P53 è già fatto); il tocco porta alla home.
- *Dipende da*: P40.

**P43 — Immagini degli avatar** · piccolo · **decisione: sì** (D29) — **file non tutti sicuri, vedi sezione 9.2**
- *Cosa e perché*: le immagini del set di avatar scelto in D29, mostrate nella navbar, nel pannello statistiche, nelle impostazioni e nella lista amici.
- *Fatto quando*: ogni avatar di `avatars.py` ha la sua immagine; chi non ne ha scelto uno vede le iniziali; il peso totale è contenuto (sotto 300 KB).
- *Dipende da*: P17, P40, P46.

**P53 — Tema scuro automatico** · piccolo · decisione: no — **file non tutti sicuri, vedi sezione 9.2**
- *Cosa e perché*: rimandato alla fine per scelta dell'utente (27/09/2026). Le pagine passano da sole ai colori scuri quando il telefono o il computer sono in tema scuro (`prefers-color-scheme`). Se P19 e gli altri punti hanno usato sempre le variabili CSS, basta aggiungere in `variables.css` i valori scuri della palette "Carretto siciliano".
- *Fatto quando*: con il dispositivo in tema scuro tutte le pagine (home, pannelli, modal, tavolo, impostazioni, accesso) sono leggibili e hanno contrasto sufficiente; le carte dello sfondo restano visibili ma non abbagliano; con il tema chiaro non cambia niente.
- *Dipende da*: P34 (dopo la rifinitura di tutte le pagine).

**P36 — Code review indipendente** · medio · decisione: no
- *Cosa e perché*: una revisione di tutto il progetto **prima della messa in servizio**, fatta "a occhi freschi". Prima si scrive la bozza dei finding **senza leggere `DECISIONI.md`**, per non farsi condizionare; poi si confronta con le decisioni. Un finding che contraddice una decisione non si scarta: si segna come "rischio residuo". Il risultato va in `REVIEW.md`, che **diventa il nuovo tracker attivo**.
- *File* — crea: `REVIEW.md`. Certezza: **sicuro**. La review non modifica il codice.
- *Fatto quando*: `REVIEW.md` ha finding numerati (R1, R2, …) ordinati per gravità (critico, alto, medio, basso), ognuno con evidenza [T]/[L]/[D]/[N], file e riga, e correzione proposta.
- *Prompt da usare* (in una sessione nuova):
  > Fai una code review indipendente di tutto il progetto Cinquecento. Leggi `CLAUDE.md`, `README.md` e `docs/REGOLE-GIOCO.md`, ma **non leggere `DECISIONI.md` finché non hai scritto la bozza dei finding**. Controlla in quest'ordine: (1) correttezza delle regole nel motore rispetto a `docs/REGOLE-GIOCO.md`; (2) fughe di informazioni (carte altrui nelle viste, messaggi o dati personali nei log); (3) concorrenza (lock per stanza, doppio clic, due schede, riconnessione, timer, inviti simultanei); (4) sicurezza (auth, CSRF, validazione, XSS in chat e username, limiti di frequenza, segreti); (5) integrità dei dati (transazioni, backup, cancellazione dell'account, amicizie e messaggi di utenti cancellati); (6) test (cosa manca, test fragili, rischio di toccare dati reali); (7) modularità, codice duplicato e rispetto della struttura delle cartelle. Per ogni finding indica gravità, evidenza [T]/[L]/[D]/[N], file:riga, scenario concreto di errore, correzione proposta e **file che la correzione modificherebbe**. Solo dopo, leggi `DECISIONI.md` e segna come "rischio residuo" i finding che contraddicono una decisione, senza riproporre soluzioni scartate. Scrivi tutto in `REVIEW.md` in italiano, numerato R1, R2, … per gravità, su un branch nuovo creato da `dev`, senza commit. Non modificare il codice.
- *Dipende da*: P31, P32, P33 (e P34 se c'è tempo).

**P37 — Chiusura e archiviazione della scaletta** · piccolo · decisione: no
- *Procedura* (quando nasce `REVIEW.md`, oppure quando tutti i punti sono spuntati):
  1. copiare i punti **non spuntati** di questa scaletta (per esempio P38 e P39) in fondo a `REVIEW.md`, con la loro numerazione originale e i loro file;
  2. spostare `SCALETTA.md` in `docs/archivio/SCALETTA-2026-09.md`, aggiungendo in cima: *"Archivio, non più aggiornato. Tracker attivo: `REVIEW.md`."*;
  3. aggiornare in `CLAUDE.md` la riga del tracker attivo e la riga "Stato";
  4. controllare che nessun documento (`README.md` compreso) rimandi ancora a `SCALETTA.md` come tracker attivo.
- *File* — sposta `SCALETTA.md` → `docs/archivio/SCALETTA-2026-09.md`; modifica `REVIEW.md` (P36), `CLAUDE.md`, `README.md` (sezione Documenti). Certezza: **sicuro**.
- *Fatto quando*: i quattro passi sono fatti e l'utente ha dato l'ok.
- *Dipende da*: P36.

### Fase 5 — Messa in servizio: demo locale (giorno 7)

**P38 — Installazione demo separata** · piccolo · decisione: **D20** — **file non tutti sicuri, vedi sezione 9.2**
- *Cosa e perché*: la demo usa **una cartella separata** (una seconda copia del repository) con il file `PRODUZIONE`, un `.env` proprio e il database `cinquecento`. Così il runner dei test non potrà mai partire lì, e lo sviluppo non tocca gli account veri. Il backup giornaliero si pianifica con l'Utilità di pianificazione di Windows.
- *Fatto quando*: nella cartella demo il runner si rifiuta di partire [T]; il backup pianificato produce un file; un ripristino di prova su `cinquecento_test` funziona.
- *Dipende da*: P18, P37.

**P39 — Accesso dagli altri dispositivi e prova generale** · piccolo · decisione: **D20**
- *Cosa e perché*: avviare il server in ascolto sulla rete locale (con `HOST` nel `.env` della demo, già previsto in P4), aprire la porta nel firewall di Windows (solo per le reti private), completare la lista di controllo del giorno della demo.
- *File* — modifica: `docs/DEMO.md` (P38). Certezza: **sicuro** per il repository. Firewall e `.env` della demo sono fuori dal repository.
- *Fatto quando*: tre telefoni sulla stessa rete Wi-Fi e un PC diventano amici, si invitano e giocano una partita 2v2 completa; la lista di controllo è stata seguita almeno una volta dall'inizio alla fine.
- *Dipende da*: P38.

## 5. Calendario indicativo (3 persone)

Segue la divisione della sezione 9. **Attenzione**: con amici, chat e prototipo i punti sono passati da 39 a 52; il 27/09/2026 ne sono stati tolti 4 (P41, P49, P50, P51), quindi ne restano 48. Una settimana resta **stretta** (vedi rischi e ordine di taglio).

| Giorno | Studente 1: motore e tempo reale | Studente 2: account, dati, amici, pagine dati | Studente 3: interfaccia e documenti |
|---|---|---|---|
| 1 — 27/09 | P1, P2, P4 | P5 (i file SQL subito, il resto dopo P4) | P3, P52 (dopo P1), P8 (il contratto si approva insieme) |
| 2 — 28/09 | P6, P10, P11, P12 | P7 (dopo P6), P18 | P19, P40 |
| 3 — 29/09 | P13, P14, P15 | P16, P17 (dopo P40) | P20, P22, P9 |
| 4 — 30/09 | P23 | P45, P26 (service, repository e test), P27 | P21, P46 |
| 5 — 01/10 | P24, P25 | P28 (dopo P24), chiamata di P26 in `room.py` (dopo P25) | P30 |
| 6 — 02/10 | P44 (dopo P29), P47 | P29, P48 | P33, P34, P35 |
| 7 — 03/10 | P31, P32 | P38, P39 | P42, P43, P53 (se c'è tempo), P36, P37 |

I giorni sono indicativi. La regola che conta è quella delle dipendenze: un punto inizia solo quando i punti da cui dipende sono già in `dev`.

**Se il tempo stringe**, ordine di taglio proposto (da confermare, D31): P53 (resta solo il tema chiaro) → P43 e P42 (restano iniziali e nome testuale) → P35 (restano le carte CSS) → P48 (chat) → P29 (niente 2v2: senza la coda 2v2 non si può giocare nemmeno in coppia con un amico) → P34. **Non si tagliano mai** P6, P15, P24, P31 e P32.

## 6. Mappa dei file

Chi crea ogni file. I file creati da P4 come segnaposto e poi riempiti da altri sono nella tabella della sezione 3.

| Cartella / file | Creato da |
|---|---|
| `.gitattributes` | P1 |
| `run.py`, `config.py`, `.env.example`, `requirements*.txt`, `app/__init__.py`, `app/extensions.py`, `app/checks.py`, segnaposto | P4 |
| `scripts/setup_db.sql`, `scripts/migrate.py`, `migrations/001_init.sql`, `app/models/*` | P5 |
| `tests/esegui_tutti.py`, `tests/conftest.py`, `tests/runner/*` | P6 |
| `app/templates/errors/*` | P7 |
| `docs/CONTRATTO-SOCKET.md`, `app/static/dev/*.json` | P8 |
| `docs/prototipo/*` | P52 |
| `app/game/engine/*` | P10–P15 (vedi i singoli punti) |
| `app/blueprints/auth/forms.py`, `app/templates/auth/*`, `auth_service.py`, `user_repo.py` | P16 |
| `app/services/avatars.py`, `app/templates/profile/*`, `pages/profile.js`, `pages/profile.css` | P17 |
| `scripts/backup.py`, `scripts/ripristina.py` | P18 |
| `base.html`, `partials/flash.html`, `css/base/*`, `button/form/modal.css`, `Modal.js`, `utils/dom.js` | P19 |
| `partials/navbar.html`, `navbar.css`, `stats-panel.css`, `core/layout.js`, `StatsPanel.js`, `LoginPrompt.js`, `img/seme-denari.svg` | P40 |
| `Card.js`, `Hand.js`, `card.css`, `hand.css`, `static/dev/carte.*` | P20 |
| `game/table.html`, `pages/game.js`, `Table/Trick/Scoreboard/Timer/SingButtons.js` e relativi CSS | P21 |
| `pages/home.js`, `pages/home.css`, `ModeModal.js`, `mode-modal.css`, `CardBackground.js`, `card-background.css`, `img/cards-bg/*`, `QueueOverlay.js`, `queue-overlay.css`, `ResumeBanner.js` | P22 |
| `friend_service.py`, `friend_repo.py` | P45 |
| `FriendsPanel.js`, `ChatWindow.js`, `friends-panel.css`, `chat.css` | P46 |
| `app/realtime/events.py`, `room.py`, `room_manager.py`, `js/core/socket.js`, `js/core/events.js`, `js/vendor/*` | P23 |
| `match_service.py`, `match_repo.py` | P26 |
| `glicko2.py`, `rating_service.py`, `rating_repo.py` | P27 |
| `app/realtime/matchmaking.py` | P28 |
| `app/realtime/presence.py`, `app/sockets/home_events.py` | P44 |
| `app/realtime/invites.py` | P47 |
| `chat_service.py`, `chat_repo.py` | P48 |
| `stats_service.py`, `stats_repo.py` | P30 |
| `tests/e2e/*` | P31 |
| `Banner.js`, `banner.css` | P33 |
| `app/static/img/cards/*` | P35 |
| `app/static/img/logo.*` | P42 |
| `app/static/img/avatars/*` | P43 |
| `REVIEW.md` | P36 |
| `docs/archivio/*` | P37 |
| `docs/DEMO.md` | P38 |

## 7. Rischi e come la scaletta li affronta

| Rischio | Come lo affrontiamo |
|---|---|
| **Tempo**: 48 punti in una settimana per tre persone sono molti, e amici e chat sono il blocco più grosso aggiunto | Filoni paralleli grazie al contratto P8 e ai dati finti (P21, P22, P46); tolti classifica, stanza privata, storico e regole (27/09); ordine di taglio proposto (D31); punti piccoli |
| **Conflitti git tra i tre** | Ogni punto elenca i suoi file; P4 prepara i segnaposto; file condivisi in sequenza (sezione 3 e colonna "Attende" della sezione 9); documenti condivisi da regolare (D22) |
| **Regole implementate male** | `docs/REGOLE-GIOCO.md` come riferimento unico; un test per ogni regola (P11–P14); controllo delle regole nella code review (P36) |
| **Carte avversarie visibili dal browser** | Vista per giocatore (P15), controllata in tutte le posizioni e poi end-to-end (P31) |
| **Chat: messaggi dannosi, spam, contenuti offensivi** | Solo tra amici (D25), testo mai come HTML, limiti di lunghezza e frequenza (P48), blocco utente (D23), messaggi fuori dai log (P7) |
| **Errori quando più cose succedono insieme** (doppio clic, due schede, timer che scade mentre arriva una mossa, due inviti accettati insieme) | Un lock per stanza (P23), test di concorrenza (P23, P28, P47, P31) |
| **Python 3.14 molto recente**: qualche libreria potrebbe non funzionare | Modalità `threading` senza gevent; versioni esatte in `requirements.txt` (P4); piano B in D5 |
| **I test cancellano dati veri** | Runner con controllo `PRODUZIONE` e del nome del database (P6); cartella demo separata (P38) |
| **Demo che non parte il giorno della consegna** (firewall, rete) | Prova generale con lista di controllo (P39) e backup pronto (P18, P38) |
| **Perdita di dati** | Backup giornaliero con prova di ripristino (P18, P38) |
| **Pagine vere diverse dal prototipo**, o prototipo da rifare se lo stile non convince | Il prototipo (P52) è già diviso nelle parti che diventano file separati, con gli stessi nomi di classe e colori e font come variabili CSS; P19, P40 e P22 spostano i pezzi senza ridisegnarli, e i test controllano che `index.html` non abbia CSS o JS scritti dentro. Passare dallo stile siciliano a quello classico cambia solo le variabili |
| **Risorse caricate da CDN** (font, icone, librerie CSS): se internet o il CDN non rispondono, le pagine perdono lo stile | Ammesse per scelta dell'utente (tutti hanno internet); caricate solo da `base.html` e solo quelle elencate in `LEGGIMI.md` |

## 8. Fuori dalla prima versione

| Idea | Motivo del rinvio |
|---|---|
| Pubblicazione su VPS o hosting gestito (D21) | Per la consegna basta la demo locale; richiede configurazione e costi |
| Verifica dell'email e recupero della password | Serve un servizio di invio email; si aggiunge se avanza tempo |
| Caricamento di una foto profilo | Servono spazio per i file, controllo dei contenuti e privacy: si usa un set di avatar predefiniti |
| Più processi server e Redis (gioco pubblico) | Con meno di 50 utenti basta un processo; l'architettura non lo impedisce |
| Bot che sostituisce chi abbandona, partite contro il computer | Utile quando ci sono pochi giocatori, ma non necessario per la consegna |
| Chat di gruppo e chat durante la partita | Per ora la chat è solo tra due amici (D25) |
| Segnalazione di utenti e moderazione | Con un gruppo di amici basta il blocco (D23) |
| Replay delle partite | Gli eventi vengono già salvati (P26): si potrà aggiungere dopo |
| Notifiche push sul telefono | Richiedono configurazione in più; per ora bastano i contatori nella pagina |
| Salvataggio delle partite in corso (per non perderle se il server si riavvia) | Con la demo locale il rischio è basso |
| Docker, `uv` | Scartati per ora per semplicità (vedi `DECISIONI.md`) |
| Classifica (ex P49) | Tolta il 27/09/2026 per scelta dell'utente |
| Stanza privata con codice (ex P41) | Tolta il 27/09/2026: tra amici si gioca con "Gioca con un amico" |
| Storico delle partite, pagina "Partite" (ex P50) | Tolto il 27/09/2026; le partite si salvano comunque per statistiche e rating |
| Pagina delle regole con mini-tutorial (ex P51) | Tolta il 27/09/2026; il regolamento resta in `docs/REGOLE-GIOCO.md` |

## 9. Divisione del lavoro tra i tre studenti

Chi è lo Studente 1, 2 o 3 lo decidete voi (D3).

### 9.1 Punti con file sicuri

Qui ci sono solo i punti di cui conosco **con certezza** tutti i file. Sono divisi in modo che:
- i punti che toccano **gli stessi file nello stesso periodo** vadano allo **stesso studente**;
- quando due studenti toccano lo stesso file, lo fanno **uno dopo l'altro**: nella colonna "Attende" c'è il punto che deve essere **già in `dev`** prima di iniziare. Rispettando quella colonna non nascono conflitti.

Due studenti che lavorano in parallelo non toccano mai gli stessi file, con un'unica eccezione: i documenti condivisi (`SCALETTA.md`, riga Stato di `CLAUDE.md`, `DECISIONI.md`, `DA-DECIDERE.md`), che dipendono dalla domanda D22.

**Studente 1 — motore di gioco e tempo reale:** P1, P2, P4, P6, P10, P11, P12, P13, P14, P15, P23, P24, P25, P44, P47, P31

**Studente 2 — account, dati, amici:** P5, P7, P16, P17, P18, P45, P26, P27, P28, P29, P48, P39

**Studente 3 — interfaccia e documenti:** P3, P52, P8, P9, P19, P40, P20, P21, P22, P46, P30, P36, P37 (più P53 in 9.2)

| Punto | Studente | File condivisi con punti di altri studenti | Attende (già in `dev`) |
|---|---|---|---|
| P1, P2 | 1 | nessuno | — |
| P3 | 3 | `CLAUDE.md` (poi P37, sempre Studente 3) | — |
| P4 | 1 | crea i segnaposto che altri riempiranno | P1, P2 |
| P5 | 2 | nessuno | P4 (solo per `migrate.py` e i modelli) |
| P6 | 1 | nessuno | P4, P5 |
| P7 | 2 | `logging_config.py`, `errors.py` (segnaposto di P4); crea `templates/errors/*` che poi modifica P19 | P4, P6 |
| P8 | 3 | nessuno | — |
| P9 | 3 | `README.md` (poi P37, sempre Studente 3) | P4, P5, P6 |
| P52 | 3 | nessuno (crea solo `docs/prototipo/*`) | P1 |
| P10–P15 | 1 | nessuno (tutto in `app/game/engine/`) | P4; P15 attende anche P8 |
| P16 | 2 | `blueprints/auth/*` (segnaposto di P4) | P5, P7, P19 |
| P17 | 2 | `blueprints/profile/routes.py` (segnaposto di P4); crea `profile/settings.html` che poi modifica P43 | P16, P40 |
| P18 | 2 | nessuno | P5, P6 |
| P19 | 3 | `templates/main/index.html` (P4), `templates/errors/*` (P7) | P4, P7, P52 |
| P40 | 3 | nessuno di altri studenti (`base.html` è dello Studente 3) | P19 |
| P20 | 3 | nessuno | P19 |
| P21 | 3 | `blueprints/game/routes.py` (P4); crea `pages/game.js` che poi modifica P24 | P8, P20, P40 |
| P22 | 3 | `blueprints/main/routes.py` (P4); crea `pages/home.js` (poi P28, P29, P44) e `ModeModal.js` (poi P28, P47) | P8, P40, P52 |
| P45 | 2 | `blueprints/friends/*` (segnaposto di P4) | P5, P16 |
| P46 | 3 | crea `FriendsPanel.js` (poi P47) e `ChatWindow.js` (poi P48) | P8, P40 |
| P23 | 1 | `sockets/__init__.py`, `connection_events.py` (P4) | P8, P16 |
| P24 | 1 | `pages/game.js` (P21), `game_events.py` (P4) | P15, P21, P23 |
| P25 | 1 | nessuno di altri studenti in parallelo | P24 |
| P26 | 2 | `realtime/room.py` (solo la chiamata al salvataggio) | P5; **P25** per la modifica a `room.py` |
| P27 | 2 | nessuno | P26 (service e repository) |
| P28 | 2 | `lobby_events.py`, `sockets/__init__.py` (dopo lo Studente 1), `pages/home.js` e `ModeModal.js` (dopo lo Studente 3) | P22, P24, P27 |
| P29 | 2 | nessuno di altri studenti in parallelo | P28 |
| P44 | 1 | `sockets/__init__.py` e `pages/home.js` (dopo lo Studente 2) | P25, P29 |
| P47 | 1 | `FriendsPanel.js` (dopo lo Studente 3), `ModeModal.js` (dopo lo Studente 2), `friends_events.py` (P4) | P24, P29, P44, P45, P46 |
| P48 | 2 | `ChatWindow.js` (dopo lo Studente 3), `chat_events.py` (P4) | P23, P45, P46 |
| P30 | 3 | `blueprints/stats/routes.py` (segnaposto di P4), `StatsPanel.js` (P40, sempre Studente 3) | P26, P27, P40 |
| P31 | 1 | nessuno (crea solo `tests/e2e/*`) | P25, P29, P47, P48 |
| P36 | 3 | nessuno (crea solo `REVIEW.md`) | P31, P32, P33 |
| P37 | 3 | `CLAUDE.md`, `README.md` (P3 e P9, sempre Studente 3) | P36 |
| P39 | 2 | `docs/DEMO.md` (creato da P38, sempre Studente 2) | P38 |

**Controlli di parallelismo** [D]: questi punti avvengono negli stessi giorni ma toccano file diversi. La verifica vale finché ognuno resta nei file elencati nel suo punto.
- P25 (Studente 1) ∥ P28 (Studente 2): `room.py`, `game_events.py`, `connection_events.py`, `game.js` contro `matchmaking.py`, `lobby_events.py`, `sockets/__init__.py`, `home.js`.
- P47 (Studente 1) ∥ P48 (Studente 2): `invites.py`, `friends_events.py`, `FriendsPanel.js` contro `chat_service.py`, `chat_repo.py`, `chat_events.py`, `ChatWindow.js`.
- P44 (Studente 1) ∥ P33 (Studente 3): P33 può toccare `home.js` (vedi 9.2), quindi **P33 attende che P44 sia in `dev`**.

### 9.2 Punti con file NON sicuri

Per questi punti non posso dire adesso con certezza quali file verranno toccati. Per ognuno indico i file che penso tocchi, perché non sono sicuro, e a chi lo assegnerei. **Regola:** all'inizio del punto chi lo fa scrive qui la lista definitiva dei file e la comunica agli altri. Se uno di quei file è in uso da un altro studente, aspetta che l'altro abbia finito e fatto il merge in `dev`.

**P32 — Sicurezza di base** · proposto: Studente 1 (giorno 7)
- *Sicuri*: `config.py`, `app/__init__.py` (creati da P4), `tests/api/test_sicurezza.py`, `tests/sockets/test_validazione_eventi.py`.
- *Probabili*: `app/sockets/connection_events.py`, `lobby_events.py`, `game_events.py`, `friends_events.py`, `chat_events.py`, `home_events.py`; `app/blueprints/auth/forms.py`; `app/blueprints/friends/routes.py`; forse `app/templates/auth/*.html`.
- *Perché non sono sicuro*: il punto corregge **quello che manca** nel codice scritto da P16–P50. Se i gestori validano già bene i dati, non vanno toccati; se no, sì. Lo si sa solo leggendo il codice quando esiste. Diversi di quei file sono dello Studente 2 (`lobby_events.py` dopo P28–P29, `chat_events.py`, `friends/routes.py`): vanno toccati solo dopo che i punti dello Studente 2 sono in `dev`.

**P33 — Errori e connessione nell'interfaccia** · proposto: Studente 3 (giorno 6)
- *Sicuri*: crea `app/static/js/components/Banner.js`, `app/static/css/components/banner.css`, `tests/frontend/test_niente_alert.py`; modifica `app/static/js/core/socket.js` (P23), `app/templates/base.html` (P40).
- *Probabili*: `app/static/js/pages/game.js`, `home.js`, `app/static/js/components/ModeModal.js`, `FriendsPanel.js`, `ChatWindow.js`.
- *Perché non sono sicuro*: bisogna disattivare i pulsanti quando la connessione cade. Se le pagine usano già un'unica funzione `render(vista)` che legge lo stato della connessione, basta toccare `socket.js`; altrimenti vanno modificate anche le pagine e i componenti. Quei file sono stati modificati da Studente 1 e Studente 2: si inizia solo dopo che P25, P44, P47 e P48 sono in `dev`.

**P34 — Rifinitura mobile e accessibilità** · proposto: Studente 3 (giorno 6–7)
- *Probabili*: qualunque file in `app/static/css/` e `app/templates/`.
- *Perché non sono sicuro*: i problemi si scoprono solo provando le pagine su un telefono vero. **Regola:** mentre P34 è aperto, nessun altro modifica file dell'interfaccia.

**P35 — Carte vere** · proposto: Studente 3
- *Sicuri*: modifica `app/static/js/components/Card.js`, `app/static/css/components/card.css` (P20, sempre Studente 3); crea `app/static/img/cards/LICENZA.md`.
- *Probabili*: 40 immagini (più il dorso) in `app/static/img/cards/`.
- *Perché non sono sicuro*: nomi e formato dei file (`.webp`, `.png`, `.svg`) dipendono dal set che sceglierete (D19). Nessun conflitto con gli altri studenti: sono tutti file dello Studente 3.

**P42 — Logo vero** · proposto: Studente 3
- *Sicuri*: modifica `app/templates/partials/navbar.html`, `app/static/css/components/navbar.css` (P40, sempre Studente 3).
- *Probabili*: `app/static/img/logo.svg` (oppure `.png`), `app/static/img/favicon.ico`; forse `app/templates/base.html` per la favicon.
- *Perché non sono sicuro*: il logo è un SVG disegnato da Claude, ma la favicon può servire in più formati o no, in base a come la inserite.

**P43 — Immagini degli avatar** · proposto: Studente 3
- *Sicuri*: crea la cartella `app/static/img/avatars/`.
- *Probabili*: un file per avatar (nomi e formato da D29); modifica `app/templates/partials/navbar.html`, `app/static/js/components/StatsPanel.js` (P30), `FriendsPanel.js` (P47), `app/templates/profile/settings.html` (P17).
- *Perché non sono sicuro*: dipende da **quanti** avatar e **che formato** (D29), e da come le altre pagine hanno già previsto lo spazio per l'avatar: se usano un unico componente o una macro del template, basta modificare quello. `settings.html` e `FriendsPanel.js` sono di altri studenti: si inizia solo dopo che P17 e P47 sono in `dev`.

**P53 — Tema scuro automatico** · proposto: Studente 3 (giorno 7, se c'è tempo)
- *Sicuri*: modifica `app/static/css/base/variables.css` (P19).
- *Probabili*: i CSS dei componenti e delle pagine che hanno ombre, trasparenze o immagini da regolare al buio (per esempio `navbar.css`, `card-background.css`, `table.css`).
- *Perché non sono sicuro*: dipende da quanto i punti precedenti hanno usato solo le variabili. **Regola:** come per P34, mentre P53 è aperto nessun altro modifica file dell'interfaccia.

**P38 — Installazione demo separata** · proposto: Studente 2 (giorno 7)
- *Sicuri*: crea `docs/DEMO.md`.
- *Probabili*: forse `scripts/pianifica_backup.ps1`, uno script che crea l'attività pianificata di Windows per il backup.
- *Perché non sono sicuro*: l'attività pianificata si può creare anche a mano seguendo le istruzioni di `docs/DEMO.md`, e allora lo script non serve. Si decide all'inizio del punto. Il resto (cartella demo, `.env`, `PRODUZIONE`, firewall) è fuori dal repository e non crea conflitti.

**Nota su P31** (Studente 1): i file di test sono sicuri. Se però i test trovano dei bug, le correzioni toccheranno altri file: ogni correzione diventa un punto nuovo, con la sua lista di file.
