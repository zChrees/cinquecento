# Scaletta — Cinquecento

> **Tracker attivo.** Ogni punto si fa su un **branch nuovo creato da `dev`**. Si spunta solo dopo l'ok dell'utente, il commit e il merge in `dev`. I documenti condivisi (questo file, la riga "Stato" di `CLAUDE.md`, `DECISIONI.md`, `DA-DECIDERE.md`) li aggiorna, a fine giornata, **chi il gruppo sceglie** tra i tre, su un branch `docs/…` (regola del 28/09/2026, sostituisce D22): durante la giornata ognuno, finito un punto, scrive solo un breve riepilogo nel proprio file (`christian.md`, `giuseppe.md`, `antonio.md`). Accanto al punto si aggiunge una breve nota del lotto (data e cosa è stato fatto). **Chi fa cosa** è nella sezione 9.
>
> **Regola sui file:** chi lavora a un punto crea e modifica **solo i file elencati in quel punto**. Se serve toccarne un altro, ci si ferma e lo si concorda: è così che si evitano i conflitti tra i lavori dei tre membri. Dove l'elenco dei file **non è sicuro** lo dice il punto stesso.
>
> **Numerazione:** i numeri dei punti non cambiano mai, così i riferimenti restano validi. I punti aggiunti il 26/09/2026 (P40–P52) sono inseriti nella fase giusta, anche se il numero è più alto. I punti tolti il 27/09/2026 (P41, P49, P50, P51) restano nell'elenco, barrati.

## 1. Obiettivo

Una web-app per giocare online a **Cinquecento**, variante siciliana, con le carte siciliane. Si può giocare 1v1 o 2v2, a 150, 300 o 500 punti, con un matchmaking basato sul rating, account personali, statistiche, amici con chat e inviti a partita. Per ora è pensata per amici e compagni (meno di 50 persone connesse insieme). In futuro deve poter crescere fino a un gioco pubblico. Scadenza: prima prevista intorno al 03/10/2026, **spostata il 01/10/2026** (nuova data da fissare, vedi D1), con 3 persone.

**Prima versione usabile** = sul PC della demo, raggiungibile dagli altri dispositivi della stessa rete:
- ci si registra, si entra e si esce, si sceglie un avatar, si cancella il proprio account;
- dalla home si gioca 1v1 o 2v2 con **Partita Veloce** (coda di matchmaking) o **Gioca con un amico** (invito), con partite **complete fino al punteggio scelto** (150, 300 o 500) e tutte le regole di `docs/REGOLE-GIOCO.md`;
- si mandano e si accettano **richieste di amicizia**, si vede chi è online, si **chatta** con gli amici e li si **invita** a una 1v1 o 2v2;
- il rating si aggiorna per le partite dalla coda, compreso il 2v2 con un amico come compagno (non per il 1v1 contro un amico); le statistiche si vedono nel pannello dell'avatar;
- funziona bene da smartphone;
- tutte le suite di test passano, e c'è un backup ripristinabile.

**Com'è fatta l'interfaccia** (prototipo approvato il 27/09/2026 in `docs/prototipo/`, vedi `DECISIONI.md`, Interfaccia):
- **una sola pagina, la home, che non scorre mai**; niente bottom navbar, classifica, stanza privata, storico né pagina delle regole;
- **navbar completamente trasparente**, con le scritte direttamente sul panno: a sinistra l'avatar, che apre il pannello statistiche (con Impostazioni ed Esci); al centro il logo (due carte che ogni tanto si girano e il nome **Cinquecento**); a destra gli amici con il contatore, che aprono il pannello amici con la chat;
- **home**: su un **panno verde** con una **cascata di carte siciliane** che cade; "giocatori online" al centro; sezioni **Partita Veloce** e **Gioca con un amico**, ciascuna con due carte-pulsante 1v1 e 2v2; toccandone una, la carta **vola al centro e si gira** e diventa il modal, che chiede i punti (150, 300, 500) e, con un amico, chi invitare; l'avviso "rientra in partita" quando serve.

**Legenda**
- *Filone*: A = motore di gioco, B = account e dati, C = interfaccia, I = integrazione (tempo reale).
- *Dimensione*: piccolo (fino a mezza giornata), medio (circa 1 giornata). I punti grandi sono già spezzati.
- *File*: **crea** = file nuovo; **modifica** = file che esiste già (creato da un punto precedente, indicato tra parentesi). I percorsi sono quelli della struttura nel `README.md`.

## 2. Tracker

### Fase 1 — Fondamenta
- [x] P1 (Fase 1): fine riga fissati — `.gitattributes` — *26/09: creato; i file tracciati sono `i/lf w/crlf`, un `.sh` nuovo resta LF; marcati binari anche jpeg, gif, font, gz e zip*
- [x] P2 (Fase 1): `.gitignore` completo — `.gitignore` — *26/09: aggiunti segreti (`.env`, `.env.*` tranne `.env.example`), `PRODUZIONE`, `backups/`, `logs/`, `*.sql.gz`, `*.dump`, file di sistema ed editor; provato con file finti*
- [x] P3 (Fase 1): riga "Stato" e regola di consegna — `CLAUDE.md` — *28/09: spuntato; la riga "Stato" e i passi di "Consegna" esistono dal primo CLAUDE.md, adattati il 27/09 al lavoro in tre (D22)*
- [x] P4 (Fase 1): scheletro del progetto con tutti i file "segnaposto" — `run.py`, `config.py`, `app/`, `requirements*.txt`, `.env.example` — *27/09: 36 file dell'elenco, 39 librerie fissate con `==`, 31 test PASS (`python -m pytest tests/api/test_avvio.py`, finché P6 non aggiunge `conftest.py`), `ruff check .` pulito (D4); il controllo di MySQL sta in `run.py`, così i test di P4 non richiedono MySQL*
- [x] P5 (Fase 1): database e prima migrazione — `scripts/setup_db.sql`, `migrations/001_init.sql`, `scripts/migrate.py`, `app/models/` — *28/09 (Christian al posto di Antonio, commit `976dec5`): 55 test nuovi, 658 PASS in tutto; le colonne `VIRTUAL` delle amicizie funzionano, quindi "una riga per coppia" resta nel database e non passa a P45; le 4 colonne a elenco senza valore predefinito sono testo esatto con un `CHECK` invece di `ENUM` (modifica a D38); la password dell'utente MySQL `cinquecento` la genera MySQL; `docs/proposta-tabelle.sql` cancellata. Ognuno, dopo il pull, lancia una volta `setup_db.sql` e `migrate.py` (`README.md`, Installazione)*
- [x] P6 (Fase 1): runner dei test — `tests/esegui_tutti.py`, `tests/conftest.py` — *28/09 (Giuseppe, commit `c69f5ed`): 13 test nuovi, 671 PASS in tutto; `python tests/esegui_tutti.py` (solo alcune suite: `python tests/esegui_tutti.py engine db`), 120 s al massimo per suite, file protetti ripristinati dopo ogni suite con controllo dell'hash, uscita 0 / 1 / 2 (tutto PASS / almeno un FAIL / rifiuto); `conftest.py` ripete i rifiuti anche per chi lancia `pytest` a mano. Lo stesso giorno, fuori scaletta, `fix/checks-database` (commit `47d2aee`): il controllo di MySQL all'avvio non si collega più a `DB_NAME` (`url._replace(database=None)`), 1 test nuovo, 672 PASS*
- [x] P7 (Fase 1): log ed errori di base — `app/logging_config.py`, `app/errors.py`, `app/templates/errors/` — *28/09 (Antonio, commit `fe5c0f7`): 19 test nuovi (`tests/api/test_errori.py`), 809 PASS in tutto; log in `logs/cinquecento.log` (rotazione a 1 MB, 5 file vecchi, livello da `LOG_LEVEL`), senza le righe delle singole richieste (contengono l'IP) e con i valori delle query nascosti da `SafeFormatter`; pagine 404 e 500 senza navbar, con "Torna alla home" (se nemmeno la 500 si può mostrare, una pagina minima scritta in `errors.py`); errori delle richieste JSON nella forma del contratto (1.2); errori imprevisti degli eventi socket nel log con il solo nome dell'evento. Nessun file fuori elenco*
- [x] P8 (Fase 1): contratto tra server e pagine — `docs/CONTRATTO-SOCKET.md`, `app/static/dev/*.json` — *28/09: contratto approvato dai tre (eventi socket, richieste HTTP, vista di gioco, dati di home, statistiche e amici) e 5 file di esempio, controllati con uno script; in `dev` dopo un rebase su P10 e P11; 106 test PASS*
- [ ] P9 (Fase 1): guida di installazione verificata — `README.md` — *03/10/2026: una prima parte (README verificato da Claude su un clone nuovo) è stata fatta e annullata lo stesso giorno su richiesta di Christian (revert in `dev`): si rifà da capo quando lo dice lui*
- [x] P52 (Fase 1, C): prototipo della home — `docs/prototipo/` — *27/09: approvato dopo varie prove: `index.html`, `prototipo.css`, `prototipo.js`, `LEGGIMI.md`, `img/` (carte siciliane da Wikimedia). Ritoccato lo stesso giorno su richiesta dell'utente: panno verde, navbar completamente trasparente, logo nuovo in CSS, animazioni dei pannelli statistiche e amici, carta 2v2 viola, sfondo tutto a cascata di carte (coppie Cavallo + Re, Assi, Tre e dorsi, con il dorso napoletano da Wikimedia), navbar e carte-pulsante in rilievo con i semi siciliani (`DECISIONI.md`, Interfaccia). Versione finale (27/09, in `dev` dallo stesso giorno): scritte sul panno come il logo al posto del vetro liquido, navbar larga con icone più grandi su computer, Assi a sagoma, spessore crema solo in basso, modal a forma di carta che si gira, niente scorrimento tranne la lista degli amici da invitare. Lo stesso giorno P22, P40, P42 e il riassunto in cima sono stati allineati alla versione finale; le immagini del prototipo passano a P40*

### Fase 2 — Funzioni essenziali
- [x] P10 (Fase 2, A): carte, mazzo, parametri delle regole — `app/game/engine/cards.py`, `deck.py`, `rules.py`, `errors.py` — *28/09 (Giuseppe, commit `3052632`): 45 test nuovi, 76 PASS in tutto; punteggi 150/300/500 sia in `config.py` sia in `RuleSet`, tenuti uguali da un test*
- [x] P11 (Fase 2, A): chi vince la presa — `app/game/engine/trick.py` — *28/09 (Giuseppe, commit `121aea7`): 30 test nuovi (tutte le coppie di carte e 2.000 prese da 4), 106 PASS in tutto; `trick_winner` restituisce la posizione nella presa, P13 la trasforma nel giocatore*
- [x] P12 (Fase 2, A): cantare 40 e 20 — `app/game/engine/singing.py` — *28/09 (Giuseppe, commit `b5d7123`): 23 test nuovi, 129 PASS in tutto; fuori elenco, con l'ok di Giuseppe, `errors.py` (suo, P10) con `NotYourTurnError`, così P24 risponde `not_your_turn` come chiede il contratto*
- [x] P13 (Fase 2, A): svolgimento di una mano, 1v1 e 2v2 — `app/game/engine/state.py`, `actions.py`, `game.py` — *28/09 (Giuseppe, commit `448da13`): 283 test nuovi (mani intere con 100 semi fissi per modalità), 412 PASS in tutto; `legal_actions(stato, posto)` in `game.py`; `new_hand` riceve mazzo mescolato e chi comincia (mescolare e D11 spettano a P14)*
- [x] P14 (Fase 2, A): partita fino al punteggio scelto (150, 300, 500), pareggio, mazziere — `app/game/engine/game.py`, `state.py` — *28/09 (Giuseppe, commit `2092904`): 108 test nuovi, 533 PASS in tutto; il mazziere non si salva, si ricava da chi comincia; a fine mano la mano dopo parte subito (la pausa del riepilogo spetta alla stanza, P24); l'abbandono resta a P24/P25*
- [x] P15 (Fase 2, A): vista per giocatore, mosse legali, mossa automatica — `app/game/engine/views.py`, `auto_move.py` — *28/09 (Giuseppe, commit `6f7517e`): 70 test nuovi, 603 PASS in tutto; `player_view(partita, posto)` dà i campi di gioco del contratto (3.3), i campi della stanza (elencati in `ROOM_FIELDS`, `ROOM_PLAYER_FIELDS`, `ROOM_TURN_FIELDS`) li aggiunge P24/P25; la conversione da `{"suit", "rank"}` a carta per le azioni della pagina la fa P24*
- [x] P16 (Fase 2, B): registrazione, login, logout — `app/blueprints/auth/`, `auth_service.py`, `user_repo.py`, `app/templates/auth/` — *28/09 (punto di Antonio, fatto da Giuseppe con il suo permesso, commit `91cb9bf`): 30 test nuovi, 717 PASS in tutto; login solo con lo username; dopo 5 errori sullo stesso username 5 minuti di blocco (conteggio in memoria); stesso messaggio per username o password sbagliati; username ed email doppi li rifiuta il vincolo unico di MySQL; `/auth/logout` solo in POST con CSRF. È la logica: la grafica di `login.html` e `register.html` la rifinisce Giuseppe. Lo stesso giorno, fuori scaletta, `fix/migrate-connessione` (commit `e7d4f05`): `migrate.py` dà il suo messaggio invece del traceback se MySQL rifiuta la connessione, 2 test nuovi*
- [x] P17 (Fase 2, B): impostazioni: avatar e cancellazione dell'account — `app/blueprints/profile/`, `app/templates/profile/`, `app/services/avatars.py` — *28/09 (Antonio, commit `1f74f97`): 30 test nuovi (`tests/api/test_impostazioni.py`), 866 PASS in tutto; `GET /profile/settings`, `POST /profile/avatar`, `POST /profile/delete` con login e CSRF; i 12 codici degli avatar in `avatars.py` (D29), più "Iniziale" (nessun avatar); per cancellare l'account si riscrive la password in una finestra nella pagina, e gli errori contano come quelli del login; chi ha una partita in corso non si può cancellare (`find_room_of_user` di P24). Nessun file fuori elenco*
- [x] P18 (Fase 2, B): backup e ripristino — `scripts/backup.py`, `scripts/ripristina.py` — *28/09 (Antonio, commit `85db5b6`): 27 test nuovi (`tests/db/test_backup.py`), 836 PASS in tutto; `python scripts/backup.py` salva il database del `.env` in `backups/<database>_AAAA-MM-GG_HHMMSS.sql.gz` e cancella solo i backup con quella forma del nome più vecchi di `BACKUP_RETENTION_DAYS` (14, provvisorio: D10); `python scripts/ripristina.py <file> <database>` su un database che non finisce con `_test` chiede di scriverne il nome; password in un file di opzioni temporaneo, mai sulla riga di comando; la suite `db` ora vuole anche `mysqldump` e `mysql` (cercati anche in `C:\Program Files\MySQL\MySQL Server 8.0\bin`). Restano a P38: il `GRANT` sul database della demo e il backup giornaliero programmato. Nessun file fuori elenco*
- [x] P19 (Fase 2, C): base grafica mobile-first — `app/templates/base.html`, `app/static/css/base/` — *28/09 (Christian, commit `03648ef`): `base.html`, messaggi flash, CSS di base e dei componenti dal prototipo (colori solo in `variables.css`, uguali al prototipo), `Modal.js` e `dom.js`; 13 test nuovi, 425 PASS in tutto dopo il rebase su P12 e P13; foto a 360×640, 360×560 e 1440×900*
- [x] P40 (Fase 2, C): navbar, pannello statistiche con dati finti, finestra "Accedi o registrati" — `partials/navbar.html`, `app/static/js/core/layout.js`, `StatsPanel.js` — *28/09 (Christian, commit `9e9d445`): 15 test nuovi, 687 PASS in tutto dopo il rebase su P6; senza login avatar e amici aprono "Accedi o registrati"; "Esci" è un modulo POST con il token CSRF verso `/auth/logout`, "Accedi" e "Registrati" portano a `/auth/login` e `/auth/register` (P16), "Impostazioni" a `/profile/settings` (P17); 21 immagini in `app/static/img/cards-bg/`, identiche al prototipo, con `LICENZA.md`. Fuori elenco, con l'ok di Christian: `pages/home.js` (minimo: avvia `layout.js`; P22 lo modifica invece di crearlo) e `main/index.html` che lo carica, 6 variabili "(P40)" in `variables.css`, 2 controlli di `test_base.py` (9 CSS in `base.html`; link `<a href>` esterni ammessi nei template, le risorse esterne restano solo in `base.html`). Foto a 360×640, 1366×657, 1440×900 e 1920×1080*
- [x] P20 (Fase 2, C): componenti carta e mano — `app/static/js/components/Card.js`, `Hand.js` — *28/09 (Christian, commit `d69f517`): 16 test nuovi (`tests/frontend/test_carte.py`), 736 PASS in tutto dopo il rebase su P16; carta segnaposto crema con il valore negli angoli (A, 2–7, F, C, R) nel colore del seme e l'Asso del seme al centro, dorso di `img/cards-bg/`; mano in fila dritta, giocabili solo le carte di `legal.play`; `HiddenHand(n)` per le carte coperte degli avversari; una carta fuori elenco si rifiuta con "Carta non valida."; pagina di prova `/static/dev/carte.html`. Nello stesso branch, commit separato `74e3727`: **D39**, crediti delle immagini anche nella finestra "Accedi o registrati" (opzione `footer` in `Modal.js`)*
- [x] P21 (Fase 2, C): tavolo di gioco con dati finti — `app/templates/game/table.html`, `app/static/js/pages/game.js` — *28/09 (Christian, commit `450bb53`): 13 test nuovi, 761 PASS in tutto dopo il rebase su P23; `/game/<game_id>` con login, `?demo=1v1` e `?demo=2v2` solo in sviluppo e nei test; un'unica `render(vista)` in `game.js`; navbar nascosta al tavolo, "Esci" con conferma; posti verso destra (nel 2v2 compagno in alto); anello del tempo attorno all'avatar, rosso sotto i 10 secondi; mazzo con il numero e briscola (o "Carte franche"); carte giocabili solo quelle di `legal.play`, pulsanti "Canta" solo per i semi di `legal.sing`. Il test apre il tavolo anche in Chrome o Edge senza finestra (saltato se mancano). Restano a P24/P25: ultima presa mostrata per un momento, riepilogo di fine mano, carte del canto per 3 secondi. Fuori elenco: `Hand.js` e `carte.html`, solo il commento `legal.play` (era scritto `legal.cards`)*
- [x] P22 (Fase 2, C): home con dati finti (carte-pulsante, modal, coda, rientro, online, sfondo) — `app/templates/main/index.html`, `app/static/js/pages/home.js`, `ModeModal.js`, `CardBackground.js` — *28/09 (Christian, commit `9ae2f99`, più `09a184d` per il test): 38 test nuovi (`tests/api/test_pagina_home.py`), 904 PASS in tutto dopo il rebase su P7, P18 e P17; la home ha l'aspetto del prototipo (confrontata a 360×640); un'unica `render(state)` in `home.js`; dati finti di `app/static/dev/` solo in sviluppo e nei test, `?demo=rientro` per l'avviso di rientro; `ModeModal.js` non parla con il server: la pagina gli passa `onPlay`, `onInvite`, `onCancelInvite` e gli risponde con `setInviteStatus(user_id, status)` (P28 e P47 cambiano solo questi); schermata di coda e avviso di rientro disegnati da zero (il prototipo non li aveva, `DECISIONI.md`). Il test apre la home in Chrome o Edge senza finestra e misura: nessuno scorrimento alle 9 misure di `LEGGIMI.md`, carta-modal delle 4 modalità a 10 misure con ogni parte dentro la cornice, invito finto, coda, rientro, finestra di accesso senza login. Fuori elenco, con l'ok di Christian: 2 variabili "(P22)" in `variables.css` (`--on-tile`, `--ink`) e il controllo dei CSS di `test_base.py` (conta solo quelli di `base.html`)*
- [ ] ~~P41 (Fase 2, C): pagina stanza privata con dati finti~~ — **tolto il 27/09/2026** per decisione dell'utente (vedi `DECISIONI.md`, Progetto e tempi)
- [x] P45 (Fase 2, B): amicizie (richieste, accetta, rifiuta, rimuovi, lista) — `app/blueprints/friends/`, `friend_service.py`, `friend_repo.py` — *28/09 (Antonio, commit `434c19a`): 59 test nuovi (`tests/api/test_amicizie.py`), 963 PASS in tutto (calcolato: 904 dell'ultimo giro più i 59 di P45; Antonio ne ha contati 925 su una base senza P22); `presence` già calcolata (`in_game` con `find_room_of_user`, `online` con una scheda nel canale `user:<id>`, altrimenti `offline`), gli avvisi quando cambia restano a P47; ogni scrittura lavora in READ COMMITTED (`_write` in `friend_service.py`), perché con REPEATABLE READ due richieste incrociate davano `Duplicate entry`; `request_id` ricordato 10 minuti in memoria (`RecentRequests`); senza login le richieste rispondono `not_logged_in` (401) in JSON. Dettagli che il contratto 2.2 non fissava: nel riepilogo di `antonio.md`*
- [x] P46 (Fase 2, C): pannello amici e finestra chat con dati finti — `FriendsPanel.js`, `ChatWindow.js` — *28/09 (Christian, commit `392e3ea`): 10 test nuovi (`tests/frontend/test_pannello_amici.py`), 990 controlli in tutto dopo il rebase su P25; il pannello usa già i **dati veri** di P45 (lista, contatore, richieste, accetta, rifiuta, annulla, rimuovi, blocca, sblocca, con CSRF e `request_id`); la chat usa i dati finti in sviluppo e nei test (quella vera è di P48); niente "Invita" nel pannello; "Altro" su ogni amico (rimuovi, blocca, con conferma) e sezione "Bloccati"; si chiude con X, Esc, tocco fuori e "indietro". Contratto 2.2 completato con i dettagli di P45 (accordo dei tre). Il test risponde al posto del server nel browser, senza MySQL, con il modulo comune `tests/browser.py` (usato anche da `test_pagina_home.py`). Fuori elenco, con l'ok di Christian: `base.html` (2 CSS), `test_base.py`, `navbar.html`, `mode-modal.css` (avatar piccoli spostati in `friends-panel.css`)*
- [x] P23 (Fase 2, I): collegamento in tempo reale, stanze, lock — `app/realtime/`, `app/sockets/connection_events.py`, `app/static/js/core/socket.js` — *28/09 (Giuseppe, commit `9b6526f`): 12 test nuovi nella suite nuova `sockets` (server vero sulla porta 5099, vuole MySQL), 748 PASS in tutto; ogni evento di una stanza passa da `room.run(...)` (lock della stanza); canali `user:<id>` e `room:<game_id>`, `game_id` casuale di 12 caratteri; risposte con la forma unica di `events.py`; client Socket.IO 4.8.1 (versione ES module) in `js/vendor/socket.io.min.js`, importato da `core/socket.js`; `send()` senza connessione risponde subito `no_connection` (codice solo della pagina). D14 (`game:replaced`) la fa P24*
- [x] P24 (Fase 2, I): stanze e partita completa — `app/realtime/room.py`, `room_manager.py`, `app/sockets/game_events.py` — *28/09 (Giuseppe, commit `51387a6`): 29 test nuovi nella suite `sockets` (partite 1v1 e 2v2 intere fino a 150 con client simulati), 790 PASS in tutto; `create_room(...)` e `find_room_of_user(...)` in `room_manager.py` (li usano P28, P29, P44, P47 senza modificarlo); `version` parte da 1 e sale a ogni mossa e a ogni cambio di scheda; D14 fatta (`game:replaced`, le mosse della scheda vecchia ricevono `not_allowed`); `game.js` collegato al server (in prova con `?demo=` no): mosse con `version`, pulsanti disattivati fino alla risposta, errori nella riga di stato, `game:sang` come scritta per 3 secondi. Restano: timer che gioca da solo, riconnessione e abbandono (P25); ultima presa, riepilogo di fine mano e carte del canto disegnate (P57, Christian)*
- [x] P25 (Fase 2, I): timer, riconnessione, abbandono — `app/realtime/room.py`, `app/sockets/game_events.py` — *28/09 (punto di Giuseppe, fatto da Antonio con il suo permesso, commit `6be3bc1`): 17 test nuovi nella suite `sockets`, 980 PASS in tutto; timer del turno per stanza (`threading.Timer` con `_turn_token`, mossa automatica sotto il lock); conta solo lo scollegamento della scheda al tavolo, rientro entro `RECONNECT_SECONDS`, poi abbandono; `game:leave` e abbandono con `result.reason = "abandon"` (D13); a partita finita le mosse rispondono `not_allowed`; "Esci" al tavolo manda `game:leave` dopo la conferma. Chi non arriva mai al tavolo non ha limite di tempo (decisione di Antonio). Test instabile `test_turno_scaduto_il_server_gioca_la_mossa_automatica` corretto il 28/09 da Giuseppe (commit `a64849a`): l'errore era nel test (le mosse automatiche partivano prima che i giocatori fossero seduti); nello stesso commit `on_join`, `on_play_card` e `on_sing` rispondono `invalid_data` a un evento senza dati; 1031 PASS in tutto*
- [x] P26 (Fase 2, B): salvataggio delle partite — `match_service.py`, `match_repo.py` — *28/09 (Antonio, commit `cbf65be`): 15 test nuovi nella suite nuova `services`, 995 PASS in tutto; a fine partita la stanza prepara un `MatchRecord` e `match_service.save_match` scrive `partite`, `giocatori_partita` e `mosse_partita` in una sola transazione, una volta sola (in `Room._apply` e `Room.abandon`); `room.py` tiene anche l'elenco delle mosse (`_moves`), più della sola chiamata prevista (scelta 1a di Antonio); formato delle mosse in `DECISIONI.md`; se il salvataggio fallisce i giocatori vedono comunque il risultato (ERROR nel log). `create_room` va chiamata dentro Flask, altrimenti la partita non si salva*
- [x] P27 (Fase 2, B): rating Glicko-2 — `glicko2.py`, `rating_service.py`, `rating_repo.py` — *28/09 (Antonio, commit `263312b`): 23 test nuovi nella suite `services`, 1028 PASS in tutto; calcolo di Glickman confrontato con l'esempio del documento; ogni partita è un periodo a sé; nel 2v2 la squadra avversaria vale come un solo avversario (scelta di Antonio); il 1v1 contro un amico non conta; nell'abbandono 2v2 scende solo chi ha abbandonato (D13); il rating si aggiorna in `save_match`, nella stessa transazione della partita. Le colonne `DOUBLE` arrivano come `Decimal`: vanno convertite (P28, P30). Segnalato un blocco occasionale della suite `api` (615 s invece di 120), non ripetuto*
- [x] P28 (Fase 2, I): matchmaking 1v1, code per punteggio — `app/realtime/matchmaking.py`, `app/sockets/lobby_events.py`, `pages/home.js`, `ModeModal.js` — *28/09 (punto di Antonio, fatto da Giuseppe con il suo permesso, commit `dce6741`): 39 test nuovi nella suite `sockets`, 1092 PASS e 1 FAIL (test della home di Christian, corretto da lui in `6ca0aab`); code in memoria per modalità e punteggio, un thread prova gli abbinamenti ogni secondo e dopo ogni `queue:join`; abbinamento solo se i due si accettano a vicenda; chi chiude tutte le schede esce dalla coda; la partita si crea dentro `app.app_context()`, quindi si salva. Non toccati `sockets/__init__.py` e `ModeModal.js`; fuori elenco, con l'ok di Giuseppe: `rating_repo.py` (`get_value`, sola lettura), `connection_events.py`, `core/events.js`, `tests/sockets/conftest.py`*
- [x] P29 (Fase 2, I): matchmaking 2v2, anche con una coppia già formata — `app/realtime/matchmaking.py`, `pages/home.js` — *28/09 (punto di Antonio, fatto da Giuseppe, commit `34729f8`): 23 test nuovi nella suite `sockets`, 1146 PASS; D17 chiusa (squadre con le medie più vicine); in coda singoli o coppie già formate (`matchmaker.join_pair`, usata da P47); se esce uno della coppia esce tutta la coppia (`"partner_left"`). Nello stesso branch, commit a parte `1a457b5`: correzione di `tests/browser.py` (leggeva `DevToolsActivePort` mentre Chrome lo scriveva), più `tests/frontend/test_avvio_browser.py`, 5 test*
- [x] P44 (Fase 2, I): home con dati reali (online, rientro in partita) — `app/realtime/presence.py`, `app/sockets/home_events.py` — *28/09 (Giuseppe, commit `ccd2172`): 8 test nuovi nella suite `sockets`, 1153 PASS e 1 FAIL (test della home di Christian, corretto da lui in `c6bb536`); `home:status` vero sempre, anche in sviluppo (finto solo con `?demo=rientro`); a fine partita i giocatori ricevono subito `resume: null`; chi è online si conta da `presence.py`. Fuori elenco, suoi: `room.py` (`finish_listeners`, fuori dal lock della stanza) e `core/events.js`*
- [x] P47 (Fase 2, I): amici online e inviti a partita — `app/realtime/invites.py`, `app/sockets/friends_events.py`, `ModeModal.js` — *28/09 (Giuseppe, commit `b7f3a03`): 31 test nuovi (27 `sockets`, 4 `frontend`), 1195 PASS e 2 FAIL (test dell'invito finto della home, tolti da Christian in `a4329e7`); inviti in memoria che scadono dopo 60 secondi (dopo "Accetta" non scadono più); 1v1 → `create_room(..., rated=False)`, 2v2 → `join_pair`; `friends:presence` e `friends:changed`; invito ricevuto solo nella home (`InviteDialog.js`, nuovo). `ModeModal.js` non toccato; fuori elenco, con l'ok di Giuseppe: `InviteDialog.js`, `home.js`, `room.py` e `room_manager.py` (`start_listeners`), `connection_events.py`, `home_events.py`, `core/events.js`, e con il permesso di Antonio `friend_service.py` e una riga di `tests/api/test_amicizie.py`*
- [x] P48 (Fase 2, B+I): chat tra amici — `chat_service.py`, `chat_repo.py`, `app/sockets/chat_events.py` — *28/09 (punto di Antonio, fatto da Giuseppe, commit `dc48e7a`): 28 test nuovi (25 `sockets`, 3 `frontend`), 1228 PASS e 2 FAIL (due test di Christian in `tests/frontend/test_pannello_amici.py` provavano la chat finta, che non c'è più: sistemati da Christian il 29/09, commit `f37945c`, con il file nuovo `tests/frontend/test_chat_pannello.py` e senza `data-chat-demo-url` nella navbar, 1305 PASS); amicizia e blocchi controllati nella stessa transazione della scrittura, in READ COMMITTED; 1 messaggio al secondo; `chat:history` a pagine da 50. Proposto `cannot_write` nel contratto 5.4 (D41). Fuori elenco, con l'ok di Giuseppe: `FriendsPanel.js`, `core/events.js`, `tests/frontend/test_chat_vera.py`*
- [ ] ~~P54 (Fase 2, B): frasi del tavolo: elenco e salvataggio~~ — **tolto il 27/09/2026**: le frasi del tavolo non si salvano (D24)
- [x] P55 (Fase 2, I): frasi del tavolo in tempo reale — `app/realtime/table_phrases.py`, `app/sockets/game_events.py`, `config.py` — *28/09 (Giuseppe, commit `523e222`): 23 test nuovi nella suite `sockets`, 1054 PASS in tutto; le 19 frasi di D24 in `table_phrases.PHRASES`, mandate con `game:phrases` a ogni `game:join`, prima di `game:state`; `game:send_phrase` `{game_id, code}` sotto il lock della stanza, solo dalla scheda al tavolo; `game:phrase` `{seat, code}` a tutti al tavolo; limite di 3 secondi per giocatore (`TABLE_PHRASE_MIN_INTERVAL_SECONDS`), `too_fast` con `retry_after` in secondi interi; si possono mandare anche a partita finita; testo e codice mai nel log né nel database. Fuori elenco, con l'ok di Giuseppe: `room.py` (campo `phrase_times`) e `tests/sockets/test_partita.py` (l'utente "Quarto" si registra solo se non c'è)*
- [x] P56 (Fase 2, C): frasi del tavolo nella pagina — `TablePhrases.js`, `table-phrases.css`, `pages/game.js` — *28/09 (Christian, commit `9e6c098`): 12 test nuovi in `tests/frontend/test_frasi_pagina.py` (non `test_frasi_tavolo.py`: il nome c'è già in `tests/sockets/`), 1131 PASS; pulsante "Frasi" in alto a destra, elenco a pillole, fumetto per 4 secondi accanto all'avatar, pulsante spento 3 secondi dopo l'invio, frasi anche a partita finita. Fuori elenco, con l'ok di Christian: `Table.js`, `table.html`, `test_momenti_tavolo.py`*
- [x] P57 (Fase 2, C): momenti del tavolo: ultima presa, riepilogo di fine mano, carte del canto — `HandSummary.js`, `Table.js`, `pages/game.js` — *28/09 (Christian, commit `449eb0a`): 12 test nuovi (`tests/frontend/test_momenti_tavolo.py`), 1066 PASS; ultima presa al centro per 1,5 secondi, riepilogo di fine mano per 5 secondi (o "Ok"), fine partita dopo l'ultima presa, carte del canto per `show_seconds`; mai alla prima vista. L'ultima presa della mano non arriva alla pagina: la porta P58. Fuori elenco, con l'ok di Christian: `table.html`*
- [x] P30 (Fase 2, B+C): pannello statistiche con dati reali — `stats_service.py`, `stats_repo.py`, `StatsPanel.js` — *28/09 (Christian, commit `3419247`): 14 test nuovi (`tests/api/test_statistiche.py`), 1119 PASS; `GET /stats/me` sempre, anche in sviluppo; "provvisorio" contato da `giocatori_partita` e `partite.conta_per_rating`; nel 2v2 la partita in cui il compagno abbandona non conta per il "provvisorio" di chi resta. Fuori elenco, con l'ok di Christian: `navbar.html` (`data-stats-url`), `tests/frontend/test_navbar.py`*
- [x] P58 (Fase 2, A): ultima presa della mano nella vista — `app/game/engine/state.py`, `game.py`, `views.py`, `docs/CONTRATTO-SOCKET.md` (3.3), `app/static/dev/vista_*.json` — *aggiunto il 28/09/2026, approvato dai tre. 28/09 (Giuseppe, commit `4dd9e5e`): `HandResult.last_trick`, `last_hand.last_trick` nella vista con la stessa forma di `last_trick`, contratto 3.3 ed esempio 1v1 (`vista_2v2.json` ha `last_hand` null); 10 test nuovi nella suite `engine`, 1243 PASS e 2 FAIL (quelli noti di Christian); il test "nessuna carta nascosta" ora controlla `last_hand` a parte (il mazzo si rimescola: una carta dell'ultima presa può essere adesso in mano a un altro). La pagina l'ha adattata Christian il 29/09 (commit `a220b0e`): a fine mano `game.js` mostra l'ultima presa della mano per 1,5 secondi, poi il riepilogo (subito, se nel frattempo si gioca la prima carta della mano nuova); 2 test nuovi in `test_momenti_tavolo.py`, e corretti due test instabili (`test_chat_pannello.py`, `test_icone.py`) che chiudevano o aprivano la chat prima del collegamento al tempo reale; 1313 PASS*
- [x] P59 (Fase 2, I): 2v2 con più amici invitati — **file non tutti sicuri, vedi sezione 9.2** — *aggiunto il 28/09/2026, approvato dai tre. 29/09 (Giuseppe, commit `b984e2a`): nel 2v2 "Gioca con un amico" fino a **tre amici** agli stessi punti; "Gioca" si accende appena uno accetta e annulla gli inviti in attesa; con un amico la coppia va in coda (conta per il rating), con due il gruppo di tre va in coda come una voce sola (due a sorte fanno coppia, il quarto dalla coda; conta per il rating), con tre la partita parte subito con squadre a sorte e non conta. Contratto: `opponents` in `queue:status`, 5.3 riscritto (ok di Giuseppe e Christian). 19 test nuovi (16 `sockets`, 3 `frontend`), 1353 PASS. Fuori elenco, con l'ok di Christian: `ModeModal.js`, `QueueOverlay.js`, `tests/api/test_pagina_home.py`. Commit a parte `f294db6`: il runner dà **240 s** per suite (prima 120), 1359 PASS*
- [x] P64 (Fase 2, A): niente canto nella prima presa della mano (regola nuova) — `app/game/engine/singing.py`, `docs/REGOLE-GIOCO.md`, `tests/engine/test_canti.py` (**file da confermare**, vedi 9.2) — *aggiunto il 29/09/2026 dalla prova a mano sul telefono (Christian e un amico). 29/09 (Giuseppe, commit `f6cc57f`): nella prima presa di **ogni** mano nessuno canta (interpretazione confermata da Giuseppe); `singable_suits` e `sing` hanno il parametro `first_trick`, ricavato da `last_trick is None`; messaggio "Nella prima presa della mano non si canta."; regolamento aggiornato. 7 test nuovi e 6 cambiati, 1404 PASS*
- [x] P67 (Fase 2, A): punti della mano in corso nella vista, di tutte e due le squadre (D44) — `app/game/engine/views.py`, `docs/CONTRATTO-SOCKET.md` (3.3), `app/static/dev/*.json`, `tests/engine/test_viste.py` — *aggiunto il 29/09/2026 dalla prova a mano sul telefono (Christian e un amico). 30/09 (Giuseppe, commit `bfe9cc5`): campo `hand_points`, stessa forma di `scores`, uguale per tutti i giocatori, da 0 a ogni mano (carte prese più canti; la presa in corso non conta finché non si chiude); esempi aggiornati; 14 test nuovi, 1455 PASS. Il contratto 3.3 l'ha aggiornato Christian il 01/10, di turno sui documenti, con l'ok di tutti e due*
- [x] P72 (Fase 2, C): i punti della mano in corso al tavolo, aggiornati in tempo reale — `Table.js`, `pages/game.js`, `table.css` (lista definitiva in 9.2) — *aggiunto il 29/09/2026 dalla prova a mano sul telefono (Christian e un amico). 01/10 (Christian, commit `4edbb5f`): i tuoi punti accanto al seme della briscola sopra la mano; nel 1v1 quelli dell'avversario a sinistra del suo avatar, nel 2v2 quelli degli avversari una volta sola sopra il giocatore a sinistra; sul telefono solo il numero, da 1024 px "N punti"; a fine mano restano i punti della mano chiusa finché si vedono ultima presa e riepilogo. 8 test nuovi (`tests/api/test_punti_mano.py`, nella suite `api` per il tempo di `frontend`); suite `api` e `frontend` PASS*
- [x] P68 (Fase 2, A+I): partita contro la CPU: mosse e stanza — **file non sicuri, vedi sezione 9.2**; D43 decisa il 04/10/2026 (strategia da rifare) — *aggiunto il 29/09/2026 dalla prova a mano sul telefono (Christian e un amico). 30/09 (Giuseppe, commit `a7b1346`): in `dev` la CPU (`cpu_move` in `app/game/engine/cpu.py`, dalla sola vista della CPU), la stanza con la CPU al posto 1 (`user_id` 0, non membro, gioca con un timer sotto il lock) e l'evento `cpu:start` (in `lobby_events.py`); solo 1v1, partita non salvata; 71 test nuovi, 1526 PASS. **Non spuntare**: il 01/10/2026 Christian ha scartato la strategia "giocatore medio" (contro la CPU si vince troppo facilmente) e D43 resta aperta; contratto di `cpu:start` ancora da approvare; Christian preferisce `cpu: true` per giocatore nella vista; **04/10 (Giuseppe, commit `1b8990e`): fatto** con la strategia di D43: "simulazione" (tante distribuzioni immaginate delle carte che non vede, giocate fino in fondo), calcolo esatto a mazzo finito nel 1v1, memoria delle carte uscite presa solo dalle sue viste, pensa fuori dal lock, attesa di circa 1–2 s; `cpu: true` nella vista; contratto (4.1 `cpu:start`, `cpu` per giocatore) approvato da Christian il 04/10. Contro il giocatore medio vince 81 partite su 100. La forza vera si prova a mano con P73*
- [ ] P73 (Fase 2, C): partita contro la CPU nella home — **file non sicuri, vedi sezione 9.2**; D43 decisa il 04/10/2026, attende P68 rifatto e P59 — *aggiunto il 29/09/2026 dalla prova a mano sul telefono (Christian e un amico)*
- [x] P75 (Fase 2, A): la carta che sta vincendo la presa nella vista — `app/game/engine/views.py`, `docs/CONTRATTO-SOCKET.md` (3.3), `app/static/dev/*.json`, `tests/engine/test_viste.py` — *aggiunto il 01/10/2026 dalla prova a mano (Christian e Giuseppe); cambio del contratto già approvato dai due. 01/10 (Giuseppe, commit `abdd5ca`): dentro `trick` il campo **`winning_seat`**, il posto della carta che vincerebbe la presa se finisse adesso (`null` senza carte), uguale per tutti; lo calcola `winning_position` di `trick.py`, che usa anche `trick_winner`. Fuori elenco, con l'ok di Giuseppe, `app/game/engine/trick.py` e `tests/engine/test_presa.py`; 27 test nuovi, 1561 PASS. Nome del campo approvato da Christian il 02/10*
- [x] P84 (Fase 2, A+I): "Cala le carte": regola, motore e stanza — **file non sicuri, vedi sezione 9.2**; D45 decisa il 04/10/2026 — *aggiunto il 01/10/2026 dalla prova a mano (Christian e Giuseppe). 04/10 (Giuseppe, commit `dab158d`): azione nuova `LayDownAction`; `legal.lay_down` vero o falso; calando la mano finisce subito, le carte rimaste vanno alla squadra di chi cala e i 20 del compagno diventano canti veri del compagno; il controllo "giocando bene" è esatto (`lay_down.team_wins_all`, 2v2 al massimo 98 ms con 5 carte a testa); mossa salvata `cala_carte`. Contratto (`game:lay_down`, `legal.lay_down`, `last_hand.laid_down`) approvato da Christian il 04/10. 28 test nuovi; giro completo 1676 PASS (un giro con 1 FAIL raro in `table`, poi `table` da sola PASS)*
- [x] P85 (Fase 2, C): "Cala le carte": pulsante e carte calate al tavolo — **file non sicuri, vedi sezione 9.2**; attende P84 — *aggiunto il 01/10/2026 dalla prova a mano (Christian e Giuseppe). 04/10 (Christian, commit `e246b77`): "Cala le carte" accanto ai pulsanti "Canta", solo con `legal.lay_down`; con una calata, per 3 s (`LAID_DOWN_MS`, uguale al server) i ventagli degli altri **entrano scoperti nel tavolo** con la scritta "Turi cala le carte" ("Hai calato le carte"), poi il riepilogo; 10 test nuovi (`tests/table/test_calata.py`)*
- [x] P92 (Fase 2, A+I): carte del compagno scoperte a mazzo finito e consiglio: regola, vista ed evento — **file non sicuri, vedi sezione 9.2**; D46 decisa il 04/10/2026, meglio dopo P84 — *aggiunto il 04/10/2026 da Christian. 04/10 (Giuseppe, commit `9f34bac`): `partner_hand` nella vista del 2v2 da quando ci sono **insieme** briscola e mazzo finito, fino a fine mano; `game:advise` / `game:advice` e `advice` nella vista (il consiglio sta nella stanza, arriva solo al compagno, sparisce quando gioca o a fine mano); la CPU usa le carte del compagno quando le vede; contratto approvato da Christian il 04/10*
- [x] P93 (Fase 2, C): carte del compagno scoperte e consiglio al tavolo — **file non sicuri, vedi sezione 9.2**; D46 decisa il 04/10/2026, attende P92 — *aggiunto il 04/10/2026 da Christian. 04/10 (Christian, commit `e8f4c30`): il ventaglio del compagno entra **scoperto** (52 px sul telefono, 80 da computer), con "Mazzo finito: ora vedi le carte di …" per 2,5 s; il compagno si sposta per non farsi coprire; toccando una sua carta parte il consiglio (carta sollevata e bordata, la stessa carta lo toglie); il consiglio ricevuto segna la carta nella tua mano ("consiglio di …")*
- [x] P94 (Fase 3, I): turno da 15 secondi, che parte dopo le pause del tavolo — **file non sicuri, vedi sezione 9.2** — *aggiunto il 04/10/2026 dalla prova di Christian (telefono e computer). 04/10 (Giuseppe, commit `e3cef4b`): turno da **15 s** che parte dopo la pausa del tavolo (`table_pause` in `room.py`: 1,5 s dopo una presa nel 1v1, 2,4 nel 2v2, circa 8–10 s a mano nuova), con le durate di `game.js` confrontate da un test; durante la pausa la vista dice il turno pieno; 14 test nuovi (`tests/sockets/test_turno.py`)*
- [x] P95 (Fase 3, C): partita interrotta dal riavvio del server: avviso e ritorno alla home — **file non sicuri, vedi sezione 9.2** — *aggiunto il 04/10/2026 dalla prova di Christian. 04/10 (Christian, commit `6ca02df`): con `not_found` al rientro, al posto del tavolo il riquadro "La partita è stata interrotta" con "Torna alla home", e ritorno alla home da soli dopo 5 s; il server rispondeva già giusto*
- [x] P96 (Fase 3, B): login con nome utente o email — **file non sicuri, vedi sezione 9.2** — *aggiunto il 04/10/2026 dalla prova di Christian. 04/10 (Giuseppe, commit `223dd84`): un campo solo, "Nome utente o email" (con `@` è un'email); tentativi contati per account (alternando username ed email il blocco non si aggira); messaggio "Nome utente, email o password non corretti."*
- [x] P97 (Fase 4, C): le carte della propria mano "lampeggiano" — **file non sicuri, vedi sezione 9.2** — *aggiunto il 04/10/2026 dalla prova di Christian. 05/10 (Christian, commit `c33bbc5`): causa [T] la carta sotto il puntatore, ridisegnata, nasceva abbassata e si rialzava; il sollevamento al passaggio vale solo con un puntatore vero (`@media (hover: hover)`) e da computer la carta sotto il mouse nasce già sollevata (`keepHover`)*
- [x] P98 (Fase 4, C): zoom con il doppio tocco al tavolo su iPhone (Safari) — **file non sicuri, vedi sezione 9.2** — *aggiunto il 04/10/2026 dalla prova di Christian. 05/10 (Christian, commit `b6fa064`): `touch-action: manipulation` su ogni elemento del tavolo (Safari non lo eredita); su iPhone **non bastava**: completato da **P104** (provato da Christian il 05/10)*
- [x] P99 (Fase 4, C): lancio della propria carta più realistico — **file non sicuri, vedi sezione 9.2** — *aggiunto il 04/10/2026 dalla prova di Christian. 05/10 (Christian, commit `73ff9e2`): la tua carta parte dal suo posto nella mano, si solleva, vola ad arco girando di circa 14° e si posa con un piccolo assestamento, in **0,55 s**; server invariato (la pausa conta ancora 0,4 s per il volo: scelta di Christian)*
- [x] P100 (Fase 4, C): mazzo del 1v1: più a destra da computer, più grande sul telefono — **file non sicuri, vedi sezione 9.2** — *aggiunto il 04/10/2026 dalla prova di Christian. 05/10 (Christian, commit `df99ff2`, insieme a P102): da computer il mazzo del 1v1 sta **sopra la pillola "Frasi"** e la presa va al centro; sul telefono il mazzo del 1v1 è da 64 px; nel 2v2 non cambia*
- [x] P101 (Fase 4, C): frasi del tavolo sul telefono aperte sopra le proprie carte — **file non sicuri, vedi sezione 9.2** — *aggiunto il 04/10/2026 dalla prova di Christian. 05/10 (Christian, commit `e594e16`): sul telefono l'elenco aperto copre solo la zona delle tue carte, sotto la tua riga, e scorre; tablet e computer come prima. Posizione rifatta in **P112***
- [x] P102 (Fase 4, C): indicatore della briscola nell'angolo (telefono) e accanto al tabellone (computer) — **file non sicuri, vedi sezione 9.2** — *aggiunto il 04/10/2026 dalla prova di Christian. 05/10 (Christian, commit `df99ff2`, insieme a P100): tondo della briscola da 52 px in vetro scuro, nell'angolo in alto a destra sul telefono e a sinistra del tabellone da computer, solo con la briscola; a mazzo finito uno spazio vuoto al posto del mazzo. **Cambiato lo stesso giorno da P108** (Cavallo e Re del seme, solo nell'angolo)*
- [x] P103 (Fase 4, C): suoni al tavolo — **file non sicuri, vedi sezione 9.2** — *aggiunto il 04/10/2026 dalla prova di Christian. 05/10 (Christian, commit `d3850e5`): suoni creati nel browser (Web Audio) per i momenti del tavolo e interruttore "Suoni al tavolo" nelle impostazioni (scelta nel browser, accesi all'inizio); **rifatti lo stesso giorno con suoni registrati (P109)**. Corretto in P109 un difetto: il contesto audio creato durante un ridisegno bloccava la pagina*
- [x] P104 (Fase 4, C): zoom con il doppio tocco su iPhone, bloccato in JavaScript — **file non sicuri, vedi sezione 9.2** — *aggiunto il 05/10/2026 dalla prova di Christian (P98 non bastava). 05/10 (Christian, commit `2d457c5`): un tocco con un dito entro 0,3 s dal precedente blocca lo zoom e la pagina manda da sé il clic al pulsante o alla carta toccata, così due tocchi veloci non si perdono; lo zoom con due dita resta. Provato su iPhone*
- [x] P105 (Fase 4, C): coda: l'intervallo di rating cambia senza lampo — **file non sicuri, vedi sezione 9.2** — *aggiunto il 05/10/2026 da Christian. 05/10 (Christian, commit `3e93249`): a ogni `queue:status` della stessa coda la schermata resta aperta e i numeri dell'intervallo scorrono in 0,5 s dal valore vecchio al nuovo (prima la schermata si chiudeva e riapriva)*
- [x] P106 (Fase 4, C): la mano non cambia misura quando restano meno carte — **file non sicuri, vedi sezione 9.2** — *aggiunto il 05/10/2026 da Christian. 05/10 (Christian, commit `1e9950a`): ogni carta della mano è larga come in una mano piena (5 carte); con meno carte quelle rimaste si ricentrano e niente si sposta (prima sul telefono il tavolo saliva di circa 30 px a ogni carta)*
- [x] P107 (Fase 4, C): lancio della carta degli avversari più realistico — **file non sicuri, vedi sezione 9.2** — *aggiunto il 05/10/2026 da Christian. 05/10 (Christian, commit `e1bb131`): la carta di un avversario o del compagno parte dal suo ventaglio, grande e girata come quello, si stacca, vola ad arco e si posa come la tua, in 0,4 s (server invariato)*
- [x] P108 (Fase 4, C): briscola solo nell'angolo, con Cavallo e Re del seme — **file non sicuri, vedi sezione 9.2** — *aggiunto il 05/10/2026 da Christian (cambia P102). 05/10 (Christian, commit `07824c3`): al posto del tondo, **Cavallo e Re** della briscola a ventaglio di ±10° come nel logo, fermi, alti 44 px sul telefono (come "Esci") e 56 da computer; niente seme sul mazzo, la sua etichetta dice solo "Mazzo: N carte"*
- [x] P109 (Fase 4, C): suoni registrati dal vero al tavolo, e un suono per le frasi — **file non sicuri, vedi sezione 9.2** — *aggiunto il 05/10/2026 da Christian (i suoni di P103 erano poco realistici). 05/10 (Christian, commit `633dead`): file MP3 dei pacchetti Kenney "Casino Audio" e "Interface Sounds" (**CC0**, `app/static/sounds/LICENZA.md`), circa 120 kB: carta che si posa, pescata, mescolata, distribuzione, presa, calata, canto, frase al tavolo (nuovo), ticchettio, fine partita; il contesto audio si crea solo al primo gesto. Completato lo stesso giorno (commit `ed0029a`): **tolto il suono di "tocca a te"** (un "ding" di vetro) e presa raccolta più pulita (`card-gather.mp3`). **Da approvare dai tre** con P113*
- [x] P110 (Fase 4, C): l'elenco delle frasi non lampeggia durante i lanci — **file non sicuri, vedi sezione 9.2** — *aggiunto il 05/10/2026 da Christian. 05/10 (Christian, commit `8a9f2a9`): causa [T] l'elenco ricreato a ogni ridisegno faceva ripartire la sua entrata da trasparente (2 volte per lancio); ora usa il ritardo negativo come le altre animazioni (P70) e, sul telefono, resta allo scorrimento di prima*
- [x] P111 (Fase 3, I): matchmaking più veloce — `config.py`, test della coda (di Giuseppe, con il suo ok) — *aggiunto il 05/10/2026 da Christian (circa 20 s per trovare un avversario). 05/10 (Christian, commit `c925359`): causa [T] l'intervallo di tutti e due partiva da ±100 e cresceva di 50 ogni 10 s (con 200 punti di differenza 20 s); ora **±150, +100 ogni 5 s fino a ±400, chiunque dopo 30 s** (opzione A, decisa da Christian e Giuseppe; cambia D16). `matchmaking.py` non cambia*
- [x] P112 (Fase 4, C): sul telefono l'elenco delle frasi si apre al suo posto e non si muove — **file non sicuri, vedi sezione 9.2** — *aggiunto il 05/10/2026 dalla prova di Christian su iPhone (l'elenco compariva sopra la tua riga e poi scendeva). 05/10 (Christian, commit `6c1d531`): causa non riprodotta [N] (Chrome e WebKit per Windows lo aprivano già al posto giusto); correzione difensiva: sotto 640 px la posizione la misura `game.js` prima del disegno, non più la griglia, e l'entrata è solo una dissolvenza. Provato da Christian su iPhone*
- [ ] P114 (Fase 3, C): suite `table` sotto il limite di tempo — i test del tavolo spostati (di Christian); `tests/esegui_tutti.py` non cambia — *aggiunto il 05/10/2026: nel giro completo dopo P112 la suite `table` è stata fermata a 240 s; da sola fa 131 PASS in 294 s (nessun test bloccato: è cresciuta con i test del 04–05/10)*
- [ ] P113 (Fase 4, C): pagina per ascoltare e confrontare i suoni del tavolo — **file non sicuri, vedi sezione 9.2** — *aggiunto il 05/10/2026 da Christian: il 06/10 i tre vogliono sentire suoni diversi da quelli di P109 e scegliere quelli che piacciono di più (D47)*
- [x] P88 (Fase 2, A+I): rating dei giocatori nella vista — `room.py` o `room_manager.py`, `docs/CONTRATTO-SOCKET.md` (3.3), `app/static/dev/*.json`, test; contratto approvato da Giuseppe e Christian (02/10/2026) — *aggiunto il 01/10/2026 dalla prova a mano (Christian e Giuseppe, seconda lista). 01/10 (Giuseppe, commit `d3b36f6`): ogni giocatore della vista ha **`rating`** = `{"value", "provisional"}` nella modalità della partita, come il pannello statistiche (`stats_service.stats_of`), letto una volta in `create_room` e fermo per tutta la partita; `null` per la CPU, fuori da Flask o se il database non risponde (la partita parte lo stesso). File `room_manager.py`, `room.py`, `views.py` (`ROOM_PLAYER_FIELDS`), contratto 3.3, esempi della vista, `tests/sockets/test_rating_vista.py`; 7 test nuovi, 1571 PASS. Contratto approvato da Christian il 02/10*
- [ ] ~~P49 (Fase 2, B+C): classifica~~ — **tolto il 27/09/2026** per decisione dell'utente (vedi `DECISIONI.md`, Progetto e tempi)
- [ ] ~~P50 (Fase 2, B+C): pagina "Partite" (storico)~~ — **tolto il 27/09/2026** per decisione dell'utente (vedi `DECISIONI.md`, Progetto e tempi)
- [ ] ~~P51 (Fase 2, C): pagina "Regole" con mini-tutorial~~ — **tolto il 27/09/2026** per decisione dell'utente (vedi `DECISIONI.md`, Progetto e tempi)

### Fase 3 — Robustezza
- [x] P31 (Fase 3): test end-to-end con client simulati — `tests/e2e/` — *29/09 (Giuseppe, commit `7378ef9`, più `c9e1aaa` per le correzioni): suite nuova `e2e`, 12 test; il server è un **processo a parte** (`python run.py` con `APP_ENV=testing`) e i test passano solo dagli ingressi veri (moduli con CSRF, rotte degli amici, Socket.IO, `GET /stats/me`); partite intere 1v1 e 2v2 dalla coda senza carte altrui nelle viste, amicizia, chat, blocco, inviti 1v1 e 2v2 (con abbandono), casi limite. In più `tests/e2e/helpers.py` (aiuti comuni, importati come `tests.e2e.helpers`). **Tre bug trovati e corretti** (commit a parte): amici "in partita" per sempre dopo una partita (`room.notify`), ora dei messaggi di chat e delle richieste di amicizia diversa tra risposta e liste (MySQL arrotonda i decimali: `chat_repo` e `friend_repo` ora tagliano l'ora alla precisione della colonna). 1255 PASS e 2 FAIL*
- [x] P32 (Fase 3): sicurezza di base — `config.py`, `app/__init__.py`, altri (lista in 9.2) — *29/09 (Giuseppe, commit `b38c56b`): intestazioni di sicurezza con CSP su ogni risposta; limite di frequenza per scheda sugli eventi in tempo reale (20 di fila, poi 10 al secondo); "Esci" e cancellazione dell'account scollegano tutte le schede (la cancellazione toglie anche dalla coda e annulla gli inviti); `not_logged_in` a una scheda di un account che non esiste più. I gestori validavano già tutto: 15 eventi × 18 dati sbagliati, mai `server_error`. 46 test nuovi (`tests/api/test_sicurezza.py`, `tests/sockets/test_validazione_eventi.py`, `tests/frontend/test_csp.py`), 1301 PASS e 2 FAIL (quelli noti di Christian)*
- [x] P33 (Fase 3): errori e connessione nell'interfaccia — `Banner.js`, `banner.css`, `core/socket.js`, pagine e componenti (lista in 9.2) — *29/09 (Christian, commit `b3de874`): avviso comune in cima alla pagina, deciso da `socket.js`: "Connessione persa: riprovo a collegarmi…", "Sei stato scollegato… ricarica la pagina." con **Ricarica** (P32), "Collegamento al server in corso…" solo se il primo collegamento supera 3 secondi; senza connessione spenti solo i pulsanti del tempo reale (carte, canti e frasi al tavolo, "Gioca", "Invita", "Accetta"/"Rifiuta", "Invia" della chat); al ritorno home, pannello amici e chat si aggiornano da soli; quando la connessione cade la schermata di coda si chiude e un invito mandato si considera annullato. 7 test nuovi (`test_niente_alert.py`, `test_banner_connessione.py`), 1320 PASS. Non provati nel browser: carte spente al tavolo e pulsanti dell'invito ricevuto*
- [x] P61 (Fase 3, B): regole della password (D8) — `app/blueprints/auth/forms.py`, `app/templates/auth/register.html`, `tests/api/test_auth.py` (lista definitiva in 9.2: `config.py` non serviva) — *aggiunto il 29/09/2026 (D8 chiusa da Christian). 29/09 (Giuseppe, commit `b52cc72`): almeno 8 caratteri, una maiuscola, un numero e un simbolo (qualunque segno, non lo spazio); un messaggio per ogni regola mancante; sotto il campo la riga con le regole; il login non le controlla. 14 test nuovi, 1334 PASS*
- [x] P63 (Fase 3, B): richiesta di amicizia con spazi prima o dopo il nome — `app/services/friend_service.py`, `tests/api/test_amicizie.py` — *aggiunto il 29/09/2026 dalla prova a mano sul telefono (Christian e un amico). 29/09 (Giuseppe, commit `0e5c932`): `check_username` toglie spazi, tab e a capo all'inizio e alla fine; uno spazio in mezzo si rifiuta come prima. 6 test nuovi dalla rotta vera, 1389 PASS*
- [x] P65 (Fase 3, I): amico bloccato, sbloccato e di nuovo amico che non compare più online nella carta-pulsante — **file non sicuri, vedi sezione 9.2** — *aggiunto il 29/09/2026 dalla prova a mano sul telefono (Christian e un amico). 29/09 (Giuseppe, commit `986e876`): due cause [T]: `friends:changed` arrivava solo all'altro utente, mai a chi faceva il cambiamento (ora a tutti e due; `"blocked"` solo a chi blocca o sblocca: contratto 5.2, ok di Giuseppe e Christian); in `home.js` una risposta vecchia di `GET /friends/` poteva sovrascrivere la lista nuova (ora vale solo l'ultima lettura). 7 test nuovi, 1370 PASS*
- [x] P66 (Fase 3, I): mossa automatica dei 30 secondi che non parte più dopo essere usciti dal browser e rientrati — `app/realtime/room.py`, altri (**file non sicuri**, vedi 9.2) — *aggiunto il 29/09/2026 dalla prova a mano sul telefono (Christian e un amico). 29/09 (Giuseppe, commit `7a31362`): la causa non era il rientro [T]: il timer ripartiva solo se cambiava il posto di turno, quindi chi chiudeva e vinceva una presa restava senza timer. Ora riparte dopo ogni carta (non dopo un canto). 4 test nuovi, 1363 PASS*
- [x] P69 (Fase 3, C): tocchi e clic al tavolo (zoom sul telefono, carta giocata durante il riepilogo, frasi ripetute) — **file non sicuri, vedi sezione 9.2** — *aggiunto il 29/09/2026 dalla prova a mano sul telefono (Christian e un amico). 29/09 (Christian, commit `d2ed7f9`): al tavolo niente zoom con il doppio tocco né menù con il tocco lungo (lo zoom con due dita resta); a fine mano carte e canti spenti finché si vedono ultima presa e riepilogo. Le **frasi a raffica** non si riproducono (un test con clic veri ne conferma una per pausa): da riprovare dal telefono. 6 test nuovi, 1340 PASS*
- [x] P79 (Fase 3, C): carte bianche per qualche secondo al tavolo — **file non sicuri, vedi sezione 9.2** — *aggiunto il 01/10/2026 dalla prova a mano (Christian e Giuseppe). 02/10 (Christian, commit `94a9f3c`): la causa [T] era l'immagine di ogni carta scaricata solo la prima volta che la carta compariva. Ora `preloadCardImages` (`Card.js`), dopo il `load` della pagina (`game.js`), scarica le 40 facce, il dorso e i 4 assi "figura"; marcatore `data-cards-ready`. Test `tests/api/test_carte_pronte.py` (3, con la rete rallentata); suite `api` 291 e `frontend` 183 PASS*
- [x] P81 (Fase 3, C): la tastiera del telefono si chiude a ogni messaggio della chat — `app/static/js/components/ChatWindow.js`, un test in `tests/frontend/` — *aggiunto il 01/10/2026 dalla prova a mano (Christian e Giuseppe). 02/10 (Christian, commit `ced1fa3`): la causa [T] non era la casella spenta, ma il fuoco che passava al pulsante "Invia" (anche spento, durante l'invio). Ora il modulo blocca il `mousedown` fuori dalla casella, e in `app/static/css/components/chat.css` (fuori elenco, con l'ok di Christian) un pulsante spento lascia passare il tocco; 2 test nuovi in `tests/frontend/test_chat_pannello.py`; `frontend` 185 PASS*
- [ ] P82 (Fase 3, I): giocatori online veri nella home anche senza login — **file non sicuri, vedi sezione 9.2** — *aggiunto il 01/10/2026 dalla prova a mano (Christian e Giuseppe)*
- [x] P83 (Fase 3, I): invito accettato e poi annullato: chi ha accettato resta ad aspettare — **file non sicuri, vedi sezione 9.2** — *aggiunto il 01/10/2026 dalla prova a mano (Christian e Giuseppe). 01/10 (Giuseppe, commit `df8af69`): la causa [T] era la connessione di chi aveva accettato che cade in silenzio (schermo bloccato, cambio di app o di rete): il server annullava l'invito, ma la pagina non lo sapeva. Ora, quando cade la connessione, anche l'invito ricevuto si considera annullato ("La connessione è caduta: l'invito è stato annullato.", poi la finestra si chiude dopo 4 s); stato solo della pagina, nessun cambio al contratto. File `home.js` (4 righe, con l'ok di Christian), `InviteDialog.js`, `tests/frontend/test_inviti_2v2.py`; 3 test nuovi, 1564 PASS*
- [x] P91 (Fase 3, C): suite `frontend` sotto il limite di tempo — **file non sicuri, vedi sezione 9.2** — *aggiunto il 02/10/2026 da Christian (due giri della suite fermati al limite di 240 s). Giro completo del 03/10: `frontend` 206 s su 240; trovato un altro test instabile, `test_frasi_pagina.py::test_tocchi_rapidi_una_frase_per_pausa` (legge il fumetto subito dopo un clic, senza aspettarlo; riepilogo di P78 in `christian.md`)* — *fatto il 03/10/2026 (Claude, per Christian che era via): misurate le suite, `frontend` 226 s e anche `api` 221 s, quindi spostare in `api` non bastava; nuova suite **`table`** (`tests/table/`, il runner la trova da solo, `tests/esegui_tutti.py` non è cambiato) con 9 file lunghi del tavolo nel browser presi da `frontend` e `api`; rete lenta di `test_carte_pronte.py` a 300 ms; corretto in `game.js` un difetto vero (in Chrome `setTimeout` a volte scatta in anticipo: i segni delle animazioni e il pulsante delle frasi spento restavano fino alla vista successiva; ora `redrawAfter`, 20 ms di margine, con il test nuovo `test_timer_in_anticipo.py`); il test delle frasi aspetta il fumetto. Tre giri: `frontend` 110–121 s, `api` 152–173 s, `table` 160–176 s; giro completo **1647 PASS** in 9 suite. Resta un fallimento raro non identificato nella suite `table` (1 giro su 7; riepilogo in `christian.md`)*

### Fase 4 — Rifiniture e revisione
- [x] P34 (Fase 4): rifinitura mobile e accessibilità — `app/static/css/`, `app/templates/` (**file precisi da definire**) — *29/09/2026: le correzioni del tavolo trovate con la prova sul telefono sono diventate P69–P72; in P34 restano accessibilità, le altre pagine e il difetto di "indietro" nel pannello amici. 29/09 (Christian, commit `7cb3e97`): controllate 9 pagine a 360×640 e 390×844 e con axe-core [T]; titolo `<h1>` per i lettori di schermo in home e tavolo, `role="img"` sulle icone dei canti, "indietro" dopo un ricaricamento con il pannello amici aperto corretto; 8 test nuovi. Il 03/10 Christian lo segna **fatto**: la prova su un telefono vero è quella del 29/09 (Christian e un amico), da cui sono nati P63–P73 e le correzioni del tavolo dei giorni dopo*
- [x] P70 (Fase 4, C): animazioni del tavolo (lancio della carta, mescolata e distribuzione, carte degli avversari, carte bianche per un attimo) — **file non sicuri, vedi sezione 9.2** — *aggiunto il 29/09/2026 dalla prova a mano sul telefono (Christian e un amico). 29/09 (Christian, in tre lotti, commit `2026165`, `a038f14`, `a6e4dc6`): lancio della carta (0,4 s, ruota); le carte degli avversari sono ventagli dal bordo dello schermo (quello in alto dietro la barra) con la pescata animata, prima chi ha preso; a ogni mano nuova, dopo il riepilogo, mescolata (0,6 s) e distribuzione una carta alla volta; un ridisegno a metà non fa ripartire le animazioni; con "riduci movimento" niente animazioni. Carte bianche: le immagini si riusano a ogni ridisegno (`reuseCardImages`), da riprovare sul telefono. 21 test nuovi, 1397 PASS*
- [x] P71 (Fase 4, C): grafica del tavolo (briscola sul mazzo, niente "Carte franche" né "mazziere", mazzo e carte più grandi sul telefono, pulsante delle frasi) — **file non sicuri, vedi sezione 9.2** — *aggiunto il 29/09/2026 dalla prova a mano sul telefono (Christian e un amico). 29/09 (Christian, commit `ea40958`): seme della briscola sopra il mazzo, senza nome, e in un tondo sopra la mano a sinistra (dal 40 a fine mano); via "Carte franche" e "mazziere"; pulsante delle frasi sopra la mano a destra, elenco verso l'alto; al telefono carte della presa da 60 px e mazzo da 56 px (nel 1v1 sul bordo destro, nel 2v2 in alto a destra). 6 test nuovi (`tests/api/test_grafica_tavolo.py`)*
- [x] P74 (Fase 4, C): tavolo da computer: avatar, carte degli avversari, "Esci", tabellone e propri punti — **file non sicuri, vedi sezione 9.2** — *aggiunto il 01/10/2026 dalla prova a mano (Christian e Giuseppe). 02/10 (Christian, commit `640ce4d`): da 1024 px "Esci" in alto a sinistra e tabellone in alto a destra, carte degli avversari da 72 px, avatar e nome accanto ai ventagli (in alto a sinistra del ventaglio), il tuo avatar a sinistra della mano e i tuoi punti a destra, fumetti che non coprono niente (scelte di Christian in `DECISIONI.md`). Lista definitiva in 9.2; 10 test nuovi; `api` 320 e `frontend` 185 PASS. **Correzione** del 03/10 (Christian, commit `df89f36`, trovata durante P76): da computer la mano sta in una colonna larga quanto il contenuto, e finché le immagini non arrivavano le carte in mano erano larghe 27 px e presa e mazzo "saltavano" (il test del mazzo finito falliva una volta su sei); ora la mano da computer è larga sempre 5 carte. 6 test nuovi in `test_grafica_tavolo.py`*
- [x] P76 (Fase 4, C): presa con le carte affiancate e la carta che vince evidenziata — **file non sicuri, vedi sezione 9.2**; attende P75 — *aggiunto il 01/10/2026 dalla prova a mano (Christian e Giuseppe). 03/10 (Christian, commit `45d4329`): carte della presa (in corso e chiusa) **a croce senza coprirsi**; la carta di `trick.winning_seat` ha il bordo giallo ed è sollevata e un po' più grande, "Sta vincendo" per i lettori di schermo (scelte di Christian in `DECISIONI.md`); nel 2v2 sul telefono le carte della presa si misurano sulla colonna centrale (container query). Lista definitiva in 9.2; 5 test nuovi (`tests/api/test_presa_affiancata.py`). Nel punto trovato e corretto un difetto di P74 (vedi P74)*
- [x] P77 (Fase 4, C): briscola solo sul mazzo, anche a mazzo finito — **file non sicuri, vedi sezione 9.2** — *aggiunto il 01/10/2026 dalla prova a mano (Christian e Giuseppe). 02/10 (Christian, commit `9eff96e`): via il tondo con il seme sopra la mano; a mazzo finito il seme resta al posto del mazzo, con la sua misura (`[data-deck-empty]`), fino a fine mano. Lista definitiva in 9.2; 5 test nuovi al posto di uno; `api` 310 e `frontend` 185 PASS*
- [x] P78 (Fase 4, C): animazioni più realistiche (pescata una carta alla volta, lanci in fila) — **file non sicuri, vedi sezione 9.2** — *aggiunto il 01/10/2026 dalla prova a mano (Christian e Giuseppe). 03/10 (Christian, commit `6da2e09`): **lanci in fila** (una carta arrivata mentre un'altra vola parte quando quella si posa, e fino ad allora non si vede); **pescata una alla volta** (0,5 s ciascuna, scelta di Christian), prima chi ha preso, dopo che si è posata la carta che ha chiuso la presa. Lista definitiva in 9.2; 2 test nuovi (`tests/api/test_animazioni_in_fila.py`, falliscono senza P78), 2 aggiornati in `test_carte_avversari.py`*
- [x] P80 (Fase 4, C): frasi del tavolo aperte di lato, da computer — **file non sicuri, vedi sezione 9.2** — *aggiunto il 01/10/2026 dalla prova a mano (Christian e Giuseppe). 03/10 (Christian, commit `4f39a2f`): da 1024 px l'elenco è un **pannello sul bordo destro**, dal tabellone fino sopra la tua riga, che scorre al suo interno; presa, mazzo, mano, compagno e avversario di sinistra restano cliccabili; nel 2v2, mentre è aperto, copre l'avversario di destra (scelta di Christian in `DECISIONI.md`). Solo `table-phrases.css`; 7 test nuovi (`tests/api/test_frasi_di_lato.py`)*
- [x] P86 (Fase 4, C): mazzo più grande, da computer — **file non sicuri, vedi sezione 9.2** — *aggiunto il 01/10/2026 dalla prova a mano (Christian e Giuseppe, seconda lista). 03/10 (Christian, commit `e70eb21`): da 1024 px il mazzo è largo **88 px** (prima 60; scelta di Christian), anche a mazzo finito; sul telefono 56 px. Misurato prima a 4 misure di computer: non tocca niente. Una regola in `trick.css`; `test_grafica_tavolo.py` misura la misura nuova*
- [x] P87 (Fase 4, C): "Esci" e punti più moderni e minimal — **file non sicuri, vedi sezione 9.2** — *aggiunto il 01/10/2026 dalla prova a mano (Christian e Giuseppe, seconda lista). 03/10 (Christian, commit `6818677`): "Esci", tabellone e punti della mano in **vetro scuro** (fondo semitrasparente sfocato, bordo sottile chiaro, scritte crema; i tuoi punti in giallo; scelta di Christian), con tre colori nuovi in `variables.css` (`--glass`, `--glass-hover`, `--glass-edge`); contrasto almeno 4,5:1 anche sul panno più chiaro. Lista definitiva in 9.2; 4 test nuovi (`tests/api/test_stile_tavolo.py`)*
- [x] P89 (Fase 4, C): rating dei giocatori al tavolo, da computer — **file non sicuri, vedi sezione 9.2**; attende P88 — *aggiunto il 01/10/2026 dalla prova a mano (Christian e Giuseppe, seconda lista). 03/10 (Christian, commit `bee62f6`): da 1024 px una **pillola con il rating** accanto al nome di ogni giocatore, **tratteggiata** se provvisorio ("provvisorio" per i lettori di schermo); niente pillola con `rating` null (CPU); sul telefono e sul tablet non si vede (scelte di Christian in `DECISIONI.md`). Lista definitiva in 9.2; 14 test nuovi (`tests/api/test_rating_tavolo.py`)*
- [x] P90 (Fase 4, C): tavolo sul telefono: via il tabellone, "Esci" che non si sovrappone — **file non sicuri, vedi sezione 9.2** — *aggiunto il 01/10/2026 dalla prova a mano (Christian e Giuseppe, seconda lista). 02/10 (Christian, commit `a5f47f3`): sotto 1024 px niente tabellone (il punteggio resta nel riepilogo di fine mano) ed "Esci" è un tondo con la sola icona (scelta di Christian); prima, a 320 px, "Esci" copriva una carta dell'avversario [T]. Lista definitiva in 9.2; 15 test nuovi (`tests/api/test_tavolo_telefono.py`); `api` 306 e `frontend` 185 PASS*
- [x] P35 (Fase 4): carte vere — `app/static/img/cards/`, `Card.js`, `card.css` — *28/09 (Christian, commit `71460b4`): 40 carte `<seme>-<valore>.webp` (316 KB) ritagliate dalle scansioni di Matsoftware (CC BY-SA 3.0, D19 chiusa), con `LICENZA.md`; niente valore negli angoli; 1167 PASS. Fuori elenco, suoi: `tests/frontend/test_carte.py`, titolo di `dev/carte.html`*
- [x] P42 (Fase 4): logo vero "Cinquecento" — `app/static/img/logo.*` (**formato da definire**), `partials/navbar.html` — *28/09 (Christian, commit `86157d3`): il logo resta quello di P40 (`navbar.html` e `navbar.css` non cambiano); icona della scheda in `app/static/img/` (`favicon.svg`, `favicon-32.png`, `apple-touch-icon.png`) collegata da `base.html`; 8 test nuovi (`tests/frontend/test_logo.py`), 1202 PASS. Fuori elenco, suo: `tests/frontend/test_base.py`*
- [x] P62 (Fase 4, C): font delle icone nel progetto (D40) — `app/static/fonts/`, `base.html`, `typography.css` — *aggiunto e fatto il 29/09/2026 (Christian, commit `7b7a8b7`): il font Material Symbols completo di Google (5,4 MB, le icone comparivano dopo secondi) diventa `material-symbols-rounded.woff2` (6 KB) con solo le 31 icone di `icone.txt`, precaricato da `base.html`; passi per aggiungere un'icona in `docs/prototipo/LEGGIMI.md` ("Icone"); `test_icone.py`, 6 test; 1311 PASS. Fuori elenco, suoi: `LEGGIMI.md`, `test_base.py` (un commento)*
- [x] P43 (Fase 4): immagini degli avatar — `app/static/img/avatars/` (lista definitiva in 9.2) — *30/09 (Christian, commit `ce7a588`): 12 avatar SVG disegnati da Claude (18 KB), stile piatto: tondo del colore del seme con il simbolo, o la figura (Re, Cavallo, Fante) con un piccolo seme; un solo componente `Avatar.js` per tavolo, pannello amici, carta-modal e coda, e la macro `partials/avatar.html` per navbar, statistiche e impostazioni; senza avatar resta l'iniziale. 22 test nuovi; suite `api` 280 e `frontend` 180 PASS*
- [ ] ~~P53 (Fase 4): tema scuro automatico~~ — **tolto il 30/09/2026** per decisione dei tre: resta solo il tema chiaro (vedi `DECISIONI.md`, Interfaccia)
- [ ] ~~P60 (Fase 4): togliere le viste finte (`?demo=`) dalla versione consegnata~~ — **tolto il 29/09/2026** da Christian: il server accetta `?demo=` solo in sviluppo e nei test e nella demo risponde 404, quindi i dati finti nella demo già non si vedono (vedi `DECISIONI.md`, Processo)
- [ ] P36 (Fase 4): code review indipendente — `REVIEW.md`
- [ ] P37 (Fase 4): chiusura e archiviazione della scaletta — `docs/archivio/`, `REVIEW.md`, `CLAUDE.md`

### Fase 5 — Messa in servizio (demo locale)
- [ ] P38 (Fase 5): installazione demo separata e backup pianificato — `docs/DEMO.md` (il resto è fuori dal repository) — *28/09, **fatto a metà** (punto di Antonio, fatto da Giuseppe, commit `87d38f4`): nel repository `docs/DEMO.md` (vale anche per la parte scritta di P39) e `scripts/pianifica_backup.ps1` (attività di Windows ogni giorno alle 3:00), 5 test nuovi (`tests/db/test_demo.py`), 1233 PASS e 2 FAIL (quelli di P48). **Non spuntare** finché sul PC della demo non sono fatti i passi 1–9 di `DEMO.md` e i tre controlli del "Fatto quando" (aspetta D20)*
- [ ] P39 (Fase 5): accesso dagli altri dispositivi e prova generale — `docs/DEMO.md`

## 3. File condivisi: come evitare i conflitti

Un conflitto git nasce quando due persone modificano **le stesse righe dello stesso file** in branch diversi. Per evitarlo:

1. **P4 crea in anticipo tutti i file "di collegamento"** come segnaposto: funzioni vuote già chiamate da `create_app()`, blueprint già registrati, moduli socket già importati, tutte le chiavi di configurazione in `config.py` e `.env.example`, tutte le librerie in `requirements.txt`. Così i punti successivi **riempiono** i propri file e non toccano `app/__init__.py`.
2. I file toccati da più punti sono pochi, e quei punti sono **in sequenza** (uno dipende dall'altro). Quando vanno a studenti diversi, vale la regola: **chi fa il punto successivo inizia solo quando il precedente è già in `dev`**, e crea il suo branch da `dev` aggiornato. Così lavora sempre sulla versione più recente del file e non nasce nessun conflitto. Gli studenti indicati si riferiscono alla sezione 9.

| File | Punti che lo toccano (in ordine) | Nota |
|---|---|---|
| `app/__init__.py`, `config.py` | P4 → P55 → P32 | Dopo P4: P55 (Giuseppe) aggiunge una chiave a `config.py`, concordata nel punto; poi solo P32. Il 28/09/2026 Christian ha aggiornato commenti e chiavi di `config.py` alle decisioni prese, prima che partissero i punti; lo stesso giorno, dopo D9, D16, D26 e D27, ha aggiornato di nuovo i commenti (solo i commenti, non i valori). P61 alla fine non ha toccato `config.py` (`PASSWORD_MIN` c'era già) |
| `requirements.txt`, `requirements-dev.txt`, `.env.example`, `app/extensions.py` | P4 | Una libreria o una chiave nuova richiede di fermarsi e concordarla |
| `app/sockets/__init__.py` | P4 → P23 → P44 | Giuseppe (P28 non l'ha toccato) |
| `app/realtime/room.py` | P23 → P24 → P25 → P26 → P55 → P44 → P47 → P31 → P66 → P68 | Giuseppe; P25 e P26 li ha fatti Antonio (salvataggio ed elenco delle mosse, `_moves`); P55 `phrase_times`, P44 `finish_listeners`, P47 `start_listeners`, P31 la correzione di `notify` |
| `app/realtime/events.py`, `app/realtime/presence.py` | P23 → P44 → P32 | Giuseppe (P32: controllo del login e limite nel decoratore `handler`, `disconnect_user`) |
| `app/realtime/room_manager.py` | P23 → P24 → P47 | Giuseppe. P28, P29 e P44 **usano** le funzioni che P24 espone; P47 ha aggiunto `start_listeners` |
| `app/sockets/connection_events.py` | P4 → P23 → P25 → P28 → P44 → P47 | Giuseppe |
| `app/sockets/lobby_events.py` | P4 → P28 → P29 → P68 | Giuseppe, sui punti di Antonio (niente stanze private); P68: `cpu:start` |
| `app/sockets/game_events.py` | P4 → P24 → P25 → P55 | Giuseppe |
| `app/sockets/friends_events.py` | P4 → P47 | Giuseppe |
| `app/sockets/chat_events.py` | P4 → P48 | Giuseppe, sul punto di Antonio |
| `app/static/js/pages/game.js` | P21 → P24 → P25 → P57 → P56 → P58 → P33 → P69 → P71 → P70 → P72 | Christian, poi Giuseppe (P24) e Antonio (P25), poi Christian (P58: l'ultima presa della mano; P33: connessione) |
| `app/static/js/pages/home.js` | P40 → P22 → P28 → P29 → P44 → P47 → P33 → P59 → P65 → P73 | Christian, poi Giuseppe (P28 e P29 al posto di Antonio), poi Christian (P33); P59 dopo il pull di P33 |
| `app/static/js/components/ModeModal.js`, `QueueOverlay.js` | P22 → P33 → P59 → P43 → P73 | Christian (P33: `setModeModalOnline`); P28 e P47 non l'hanno toccato (bastava `home.js`); P59 (Giuseppe, con l'ok di Christian): più amici nel 2v2; P43: `Avatar.js` |
| `app/static/js/components/InviteDialog.js` | P47 → P33 → P59 | Giuseppe, poi Christian (P33: `setOnline`), poi Giuseppe (P59) |
| `app/static/js/components/StatsPanel.js` | P40 → P30 | Christian (dati finti, poi dati veri) |
| `app/static/js/components/FriendsPanel.js` | P46 → P47 → P48 → P33 → P34 → P43 | Christian, poi Giuseppe, poi Christian (P33, P34, P43) |
| `app/static/js/components/ChatWindow.js` | P46 → P48 → P33 | Christian, poi Giuseppe (P48 al posto di Antonio), poi Christian (P33: `setChatOnline`) |
| `app/static/js/core/events.js` | P23 → P28 → P44 → P47 → P48 | Giuseppe (i nomi degli eventi) |
| `app/static/js/core/layout.js` | P40 → P46 | Christian |
| `app/static/js/core/socket.js` | P23 → P33 | Giuseppe, poi Christian (P33: l'avviso della connessione) |
| `app/game/engine/game.py`, `state.py`, `views.py` | P13 → P14 → P15 → P58 → P64 → P67 | Giuseppe (P68 non li ha toccati: la CPU sta in `cpu.py`) |
| `app/blueprints/auth/forms.py`, `app/templates/auth/*` | P16 → P61 | Giuseppe (P61: regole della password, D8) |
| `app/services/auth_service.py`, `app/repositories/user_repo.py` | P16 → P17 → P32 | Giuseppe (P16), Antonio (P17), Giuseppe (P32: cancellazione dell'account con coda e inviti) |
| `app/services/match_service.py` | P26 → P27 | Antonio |
| `app/services/friend_service.py` | P45 → P47 → P65 → P63 | Antonio, poi Giuseppe con il suo permesso |
| `app/repositories/chat_repo.py`, `friend_repo.py` | P48, P45 → P31 | Giuseppe (P31: l'ora tagliata alla precisione della colonna) |
| `tests/browser.py` | P46 → P29 | Christian; Giuseppe ha corretto l'attesa della porta di Chrome (P29, commit a parte) |
| `tests/esegui_tutti.py` | P6 → P59 | Giuseppe (commit a parte di P59: 240 s per suite) |
| `app/static/js/components/Table.js`, `Hand.js`, `Trick.js`, `Card.js` e i loro CSS | P21 → P57 → P56 → P69 → P71 → P70 → P34 → P43 → P72 | Christian |
| `app/blueprints/*/routes.py` e `__init__.py` | P4 (segnaposto) → un solo punto per blueprint | `main/routes.py`: solo P22 (Christian) |
| `app/templates/base.html` | P19 → P40 → P46 → P42 → P62 → P33 | Christian |
| `app/templates/partials/navbar.html`, `app/static/css/components/navbar.css` | P40 → P42 → P43 | Christian (P43: macro `partials/avatar.html`; le regole `.avatar--img` stanno in `navbar.css` ma valgono per tutti gli avatar) |
| `app/templates/main/index.html` | P4 → P19 → P22 | Christian dopo P4 |
| `app/templates/errors/*.html` | P7 | Creati da P7 già basati su `base.html` (P19 viene prima di P7) |
| `app/templates/profile/settings.html` | P17 → P43 | Antonio, poi Christian dopo che P17 è in `dev` |
| `app/static/js/components/Card.js`, `app/static/css/components/card.css` | P20 → P35 | Christian |
| `docs/DEMO.md` | P38 → P39 | Giuseppe (P38 al posto di Antonio; P39 riassegnato il 28/09/2026) |
| `README.md` | P9 → P37 | Christian |
| `docs/prototipo/*` | P52 | Dopo P52 nessuno lo modifica: P19, P40 e P22 lo **leggono** soltanto (il 28/09/2026 Christian ha corretto solo un rimando nel `LEGGIMI.md`: le immagini arrivano con P40) |
| `SCALETTA.md`, `CLAUDE.md` (riga Stato), `DECISIONI.md`, `DA-DECIDERE.md` | a turno | Li aggiorna, a fine giornata, **chi il gruppo sceglie**, su un branch `docs/…` da `dev` (28/09/2026, sostituisce D22). Nei branch dei punti non si toccano; ognuno scrive il riepilogo di ogni punto nel proprio file |
| `christian.md`, `giuseppe.md`, `antonio.md` | ciascuno il suo | Ognuno scrive **solo** il proprio file di riepiloghi, nel branch del punto; gli altri due lo leggono dopo il pull di `dev` |

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
- *File*: modifica `CLAUDE.md`. Certezza: **sicuro**. *Preparato nel lotto della scaletta*: si spunta con l'ok. La riga Stato la aggiorna chi è di turno sui documenti (28/09/2026, sostituisce D22).
- *Fatto quando*: `CLAUDE.md` ha la riga compilata e il passo 7 in "Consegna".
- *Dipende da*: nessuno.

**P4 — Scheletro del progetto** · medio · decisione: **D4** (lint)
- *Cosa e perché*: crea tutta la struttura del `README.md` con i file di collegamento **già pronti come segnaposto** (vedi sezione 3), così gli altri punti non devono toccare i file centrali. `config.py` contiene fin da subito **tutte** le chiavi: database, `SECRET_KEY`, `HOST`, `PORT`, secondi del turno (30), secondi di riconnessione (60), parametri del matchmaking, limiti della chat (lunghezza e frequenza dei messaggi), durata degli inviti, cartelle di log e backup, giorni di conservazione dei backup (e dei messaggi: tolta il 28/09/2026, perché i messaggi non si cancellano, D24). All'avvio si **controllano le versioni** (Python 3.14, MySQL 8.0) e ci si ferma con un messaggio chiaro se non corrispondono.
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

**P5 — Database** · medio · decisione: **D6, D7, D23, D24, D26, D38 prese il 27/09/2026** (le tabelle approvate erano in `docs/proposta-tabelle.sql`; dal 28/09 sono in `migrations/001_init.sql`) — **fatto il 28/09/2026**
- *Cosa e perché*: `setup_db.sql` crea i database `cinquecento_dev` e `cinquecento_test` con un utente MySQL dedicato, in `utf8mb4`/InnoDB. `001_init.sql` crea **tutte** le tabelle della prima versione, con i nomi in italiano (D38): `utenti`, `rating`, `partite`, `giocatori_partita`, `mosse_partita`, `amicizie`, `blocchi`, `messaggi`, `versione_schema`. **Parte da `docs/proposta-tabelle.sql`** (approvata il 27/09/2026, aggiornata il 28/09 con il salvataggio a fine partita) e la cancella. Il comportamento alla cancellazione di un utente (D6) sta nelle chiavi esterne del file. `migrate.py` applica le migrazioni mancanti. I modelli Python rispecchiano le tabelle.
- *File* — crea: `scripts/setup_db.sql`, `migrations/001_init.sql`, `scripts/migrate.py`, `app/models/user.py`, `app/models/rating.py`, `app/models/match.py`, `app/models/friendship.py`, `app/models/chat_message.py`, `tests/db/test_migrate.py`. Certezza: **sicuro**. Il modello dei blocchi (D23) va in `app/models/friendship.py`.
- *Nota*: nella prima versione nessun altro punto aggiunge migrazioni. Se ne serve una, è un punto nuovo da concordare.
- *Fatto quando*: su un database vuoto `migrate.py` crea tutte le tabelle; rilanciato non fa niente [T]. In più, test delle **regole del database** su `cinquecento_test` (28/09/2026): cancellando un utente spariscono il suo rating, le amicizie, i blocchi e i messaggi, mentre in `giocatori_partita` la riga resta con `utente_id` vuoto (D6); un nome utente troppo corto, troppo lungo, con lettere accentate o con spazi viene rifiutato, `Mario` e `mario` possono esistere tutti e due, due email uguali a parte le maiuscole no (D7); lo stesso utente non può sedere due volte nella stessa partita; una seconda amicizia tra gli stessi due utenti, anche in direzione opposta, viene rifiutata (se MySQL non accetta le colonne calcolate, il test lo documenta e il controllo passa a P45); un punteggio per vincere diverso da 150, 300 e 500 viene rifiutato; una partita senza data o motivo di fine viene rifiutata (si salva solo a fine partita); un messaggio più lungo di 1000 caratteri viene rifiutato (D26).
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
- *Cosa e perché*: i log (il registro di cosa succede nel server) vanno in `logs/` con rotazione, cioè i file vecchi vengono sostituiti. Livelli distinti: INFO per gli eventi normali, WARNING/ERROR per le anomalie. **Mai** dati personali, password, token o **testo dei messaggi della chat** nei log. Pagine 404 e 500 in italiano, **già basate su `base.html`** (P19: dal 27/09/2026 P19 viene prima di P7, vedi `DECISIONI.md`); gli errori degli eventi socket vanno solo a chi li ha causati.
- *File* — modifica: `app/logging_config.py`, `app/errors.py` (segnaposto di P4). Crea: `app/templates/errors/404.html`, `app/templates/errors/500.html`, `tests/api/test_errori.py`. Certezza: **sicuro**.
- *Fatto quando*: pagina inesistente → 404; errore forzato → pagina 500 senza dettagli tecnici e riga ERROR nel log [T]; la password usata in un login di prova non compare nel log; le due pagine estendono `base.html`.
- *Dipende da*: P4, P6, P19.

**P8 — Contratto tra server e pagine** · piccolo · **decisione: sì** (approvare il contratto)
- *Cosa e perché*: un documento che fissa i **nomi degli eventi socket** e i dati di ciascuno per: partita (`game:play_card`, `game:sing`, …, e le **frasi del tavolo**: l'invio di una frase, la frase che arriva a tutti, l'elenco delle frasi con codice e testo all'ingresso nella stanza, D24), code di matchmaking (con modalità e punteggio), home (utenti online, rientro in partita), amici (presenza, richieste, inviti) e chat. Fissa anche il **formato della vista di gioco** (la tua mano, il numero di carte degli altri, il tavolo, la briscola, i punteggi, il punteggio per vincere, le mosse legali, il timer) e il formato dei dati di home, pannello statistiche e amici. Serve a far lavorare **in parallelo** i filoni.
- *File* — crea: `docs/CONTRATTO-SOCKET.md`, `app/static/dev/vista_1v1.json`, `app/static/dev/vista_2v2.json`, `app/static/dev/home_esempio.json`, `app/static/dev/amici_esempio.json`, `app/static/dev/statistiche_esempio.json` (aggiunto il 28/09/2026: i dati del pannello statistiche in un file separato, scelta dell'utente). Certezza: **sicuro**. Gli esempi stanno in `static/dev/` perché li usano sia le pagine (dati finti) sia i test.
- *Fatto quando*: l'utente ha approvato il contratto e i file di esempio lo rispettano.
- *Dipende da*: nessuno.

**P9 — Guida di installazione verificata** · piccolo · decisione: no
- *Cosa e perché*: il `README.md` ha già la struttura e i passi previsti. Qui si **verificano** e si correggono i comandi sul progetto vero.
- *File* — modifica: `README.md`. Certezza: **sicuro**.
- *Fatto quando*: un compagno, seguendo solo il README su un altro PC, avvia il gioco e fa passare i test.
- *Dipende da*: P4, P5, P6.

**P52 — Prototipo della home** · medio · decisione: no — **fatto il 27/09/2026**
- *Cosa e perché*: la home disegnata **prima di tutto il resto** come prototipo statico, che si apre con un doppio clic nel browser, senza Flask né database. È il **riferimento grafico** di P19, P40 e P22: il server non lo usa e **nessuno lo modifica**. Dopo alcune prove (un primo prototipo scartato, quattro palette a confronto) l'utente ha approvato la versione descritta in `DECISIONI.md`, sezione Interfaccia (27/09/2026), e poi la **versione finale** dello stesso giorno ("Versione finale del prototipo"): palette "Carretto siciliano" su un panno verde da tavolo con una cascata di carte siciliane che cade; navbar completamente trasparente, con avatar, amici, "giocatori online" e titoli scritti direttamente sul panno come il nome del logo; logo con due carte che ogni tanto si girano; carte-pulsante in rilievo con l'Asso a sagoma e lo spessore crema solo in basso; modal della modalità a forma di carta, che vola al centro e si gira; pannelli statistiche e amici; niente scorrimento, tranne la lista degli amici da invitare.
- *File* — creati: `docs/prototipo/index.html`, `prototipo.css`, `prototipo.js`, `LEGGIMI.md`, `docs/prototipo/img/` (16 carte siciliane e 4 Assi a sagoma ricavati dalle scansioni di Matsoftware, CC BY-SA 3.0; il dorso e il seme di denari, pubblico dominio; il seme di denari non è più usato).
- *Fatto quando*: `index.html` si apre con un doppio clic e mostra tutti gli stati (anche con `?apri=`); la pagina non scorre alle misure elencate in `LEGGIMI.md`; `LEGGIMI.md` elenca risorse esterne, font, licenze e quale punto riprende ciascuna parte. **Fatto** [T]: controlli con screenshot e misure a 9 dimensioni di schermo; nella versione finale il modal a forma di carta è stato misurato con uno script nelle 4 modalità a 17 misure di schermo (68 casi).
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

**P14 — Partita fino al punteggio scelto** · piccolo · decisione: **D11** (decisa il 28/09/2026: regola in `docs/REGOLE-GIOCO.md`, "Chi comincia")
- *Cosa e perché*: la partita finisce quando qualcuno arriva al punteggio scelto all'inizio (150, 300 o 500, dal modal della home). Un punteggio diverso da questi tre viene rifiutato.
- *File* — modifica: `app/game/engine/game.py`, `app/game/engine/state.py` (P13). Crea: `tests/engine/test_partita.py`. Certezza: **sicuro**.
- *Fatto quando*: per ognuno dei tre punteggi, la partita finisce solo a fine mano; vince chi arriva ad almeno N (con N esatti si vince); se ci arrivano entrambi vince il più alto; a parità è pareggio; arrivare a N durante la mano con un canto non chiude la partita; un punteggio fuori elenco viene rifiutato; nella prima mano il primo giocatore è scelto a caso (con un seme fisso nei test) e il mazziere è quello alla sua sinistra; dalla seconda mano comincia il giocatore alla destra di chi aveva cominciato la mano prima, e il mazziere è sempre alla sinistra di chi comincia.
- *Dipende da*: P13.

**P15 — Vista per giocatore, mosse legali, mossa automatica** · medio · decisione: **D12** (decisa il 28/09/2026: regola in `docs/REGOLE-GIOCO.md`, "Tempo per turno")
- *Cosa e perché*: dallo stato completo si ricava la vista di **un** giocatore, senza le carte degli altri né l'ordine del mazzo. È la difesa principale contro chi prova a imbrogliare.
- *File* — crea: `app/game/engine/views.py`, `auto_move.py`, `tests/engine/test_viste.py`, `tests/engine/test_mossa_automatica.py`. Certezza: **sicuro**.
- *Fatto quando*: la vista non contiene mai carte che il giocatore non può vedere (controllo su tutte le posizioni di una partita intera); le mosse legali coincidono con quelle che `apply` accetta; la mossa automatica è sempre legale, non canta mai e sceglie la carta come deciso in D12 (meno punti, poi non di briscola, poi la più debole, poi a caso: un test per ogni passo, con un seme fisso per il caso); la vista ha lo stesso formato di `app/static/dev/vista_*.json`.
- *Dipende da*: P13, P8.

#### Account e dati (B)

**P16 — Registrazione, login, logout** · medio · decisione: **D7, D8**
- *Cosa e perché*: moduli con protezione CSRF (un codice segreto nel modulo che impedisce a un altro sito di inviarlo al posto dell'utente, tramite Flask-WTF), password salvate solo come hash, sessione con Flask-Login, messaggi chiari, limite ai tentativi di login ripetuti.
- *File* — modifica: `app/blueprints/auth/__init__.py`, `app/blueprints/auth/routes.py` (segnaposto di P4). Crea: `app/blueprints/auth/forms.py`, `app/services/auth_service.py`, `app/repositories/user_repo.py`, `app/templates/auth/login.html`, `app/templates/auth/register.html`, `tests/api/test_auth.py`. Certezza: **sicuro**. Lo stile viene dalle classi CSS di P19, senza modificarne i file.
- *Fatto quando*: registrazione ok; username duplicato → errore; password sbagliata → errore generico; dopo il logout le pagine protette rimandano al login; nel database non c'è la password in chiaro; dopo N tentativi sbagliati → attesa.
- *Dipende da*: P5, P7, P19.

**P17 — Impostazioni: avatar e cancellazione dell'account** · piccolo · decisione: **D6** (già applicata in P5), **D29** (in parte: 12 avatar in SVG, decisi il 28/09/2026; restano quali figure, autore e licenza)
- *Cosa e perché*: la pagina "Impostazioni" (dal link nel pannello statistiche dell'avatar) permette di **scegliere un avatar** da un set predefinito e di **cancellare l'account**. `avatars.py` contiene l'elenco degli avatar ammessi: il server rifiuta qualunque valore fuori elenco. Finché le immagini non ci sono (P43), la pagina mostra il nome o il numero di ogni avatar.
- *File* — modifica: `app/blueprints/profile/routes.py` (P4), `app/services/auth_service.py`, `app/repositories/user_repo.py` (P16). Crea: `app/services/avatars.py`, `app/templates/profile/settings.html`, `app/static/js/pages/profile.js`, `app/static/css/pages/profile.css`, `tests/api/test_impostazioni.py`. Certezza: **sicuro**.
- *Fatto quando*: l'avatar scelto viene salvato; un avatar fuori elenco viene rifiutato; dopo la conferma (con la finestra nella pagina di P19, non `confirm()`) l'utente non esiste più, il login fallisce, e le partite restano come deciso in D6.
- *Dipende da*: P16, P40.

**P18 — Backup e ripristino** · piccolo · decisione: **D10**
- *Cosa e perché*: `backup.py` lancia `mysqldump`, salva un file compresso con la data in `backups/` e cancella quelli più vecchi di D10 giorni. `ripristina.py` ricarica un backup **in un database indicato**, e chiede conferma se non è di test.
- *File* — crea: `scripts/backup.py`, `scripts/ripristina.py`, `tests/db/test_backup.py`. Certezza: **sicuro**.
- *Fatto quando*: sul database di test: backup → modifica dei dati → ripristino → dati identici a prima [T].
- *Dipende da*: P5, P6.

**P45 — Amicizie** · medio · decisione: **D23, D26, D33** (decise il 27 e 28/09/2026)
- *Cosa e perché*: cercare un utente per username e mandargli una **richiesta di amicizia**; accettare, rifiutare, annullare una richiesta; rimuovere un amico; vedere la lista degli amici e delle richieste in arrivo (con il numero per il contatore nella navbar). Sono richieste HTTP in JSON, protette da CSRF. C'è anche "blocca utente" (D23): il blocco toglie l'amicizia.
- *File* — modifica: `app/blueprints/friends/__init__.py`, `app/blueprints/friends/routes.py` (segnaposto di P4). Crea: `app/services/friend_service.py`, `app/repositories/friend_repo.py`, `tests/api/test_amicizie.py`. Certezza: **sicuro**.
- *Fatto quando*: test via HTTP: richiesta → accettazione → i due sono amici; una richiesta doppia o a sé stessi viene rifiutata; rimuovere un amico lo toglie per entrambi; un utente bloccato non può mandare richieste (D23); si rispetta il limite di D26.
- *Dipende da*: P5, P16.

**P26 — Salvataggio delle partite** · piccolo · decisione: no
- *Cosa e perché*: a fine partita si salvano risultato, giocatori ed eventi **in una sola transazione** (o tutto o niente). Prima della fine nel database non si scrive niente: la partita in corso sta solo in memoria (deciso il 28/09/2026).
- *File* — crea: `app/services/match_service.py`, `app/repositories/match_repo.py`, `tests/services/test_match_service.py`. Modifica: `app/realtime/room.py` (P25), **solo** per aggiungere la chiamata al salvataggio a fine partita. Certezza: **sicuro**.
- *Fatto quando*: dopo una partita simulata, nel database di test ci sono partita, giocatori ed eventi in ordine; un errore a metà salvataggio non lascia dati parziali.
- *Dipende da*: P5 per service, repository e test; P25 solo per la modifica a `room.py`, che si fa per ultima.

**P27 — Rating Glicko-2** · medio · decisione: **D9** (decisa il 28/09/2026)
- *File* — crea: `app/services/glicko2.py`, `app/services/rating_service.py`, `app/repositories/rating_repo.py`, `tests/services/test_glicko2.py`, `tests/services/test_rating_service.py`. Modifica: `app/services/match_service.py` (P26). Certezza: **sicuro**.
- *Fatto quando*: test contro l'esempio numerico ufficiale di Glicko-2 (documento di Glickman) [T]; il pareggio conta 0.5; il 1v1 contro un amico non cambia il rating, il 2v2 con un amico come compagno sì; il rating conta allo stesso modo a 150, 300 e 500 punti; 1v1 e 2v2 separati; aggiornamento nella stessa transazione del salvataggio.
- *Dipende da*: P26 (service e repository).

#### Interfaccia (C)

**P19 — Base grafica mobile-first** · medio · decisione: **D18** (solo per il tavolo di gioco)
- *Cosa e perché*: struttura comune delle pagine con lo spazio per la navbar (riempito da P40) e la pagina alta quanto lo schermo, senza scorrimento, variabili CSS (colori, spazi, font), messaggi, finestra di conferma riutilizzabile. Si progetta per **360 px di larghezza** e poi si allarga. **Colori (palette "Carretto siciliano"), font (Fredoka, Nunito) e spazi si prendono dal prototipo di P52** e si riscrivono come variabili CSS nei nostri file, per il **solo tema chiaro**: il tema scuro è rimandato alla fine (P53), ma i colori vanno usati **sempre tramite le variabili**, così P53 dovrà solo aggiungere i valori scuri. Le risorse esterne del prototipo (font, icone, librerie CSS da CDN) si caricano **una volta sola in `base.html`**, così valgono per tutte le pagine.
- *File* — crea: `app/templates/base.html`, `app/templates/partials/flash.html`, `app/static/css/base/reset.css`, `variables.css`, `typography.css`, `layout.css`, `app/static/css/components/button.css`, `form.css`, `modal.css`, `app/static/css/pages/auth.css`, `app/static/js/components/Modal.js`, `app/static/js/utils/dom.js`, `tests/frontend/test_base.py`. Modifica: `app/templates/main/index.html` (P4). Le pagine di errore non le tocca: le crea P7, dopo, già basate su `base.html`. Certezza: **sicuro**.
- *Fatto quando*: a 360 px le pagine sono leggibili senza scorrimento orizzontale; i colori coincidono con quelli del prototipo; nei CSS non ci sono colori scritti a mano fuori da `variables.css`; il test controlla che ogni pagina abbia il `meta viewport`, carichi un solo script di pagina, e che le risorse esterne siano solo quelle elencate in `docs/prototipo/LEGGIMI.md`.
- *Dipende da*: P4, P52.

**P40 — Navbar, pannello statistiche, finestra "Accedi o registrati"** · medio · decisione: no
- *Cosa e perché*: si parte dalla navbar del **prototipo di P52**. Il suo HTML va in `partials/navbar.html`, incluso da `base.html` con `{% include %}`: così compare in ogni pagina senza essere ricopiato. Lo stile va nei CSS dei componenti e il comportamento in `layout.js`. Dove il prototipo e le decisioni non coincidono, valgono le decisioni (`DECISIONI.md`, sezione Interfaccia).
  - **navbar completamente trasparente** (niente fondo, sfocatura né ombra): avatar a sinistra (per ora iniziali su un cerchio colorato con l'anello giallo), logo al centro, pulsante amici a destra con il contatore (il pannello arriva in P46); su computer, accanto all'avatar e all'icona, il nome e la scritta "Amici";
  - **scritte sul panno**: avatar e amici non hanno fondo; le scritte e le icone sono **come il nome "Cinquecento"** del logo (Fredoka color crema, leggero rilievo, contorno scuro sfumato: variabile `--relief-text` del prototipo) con un alone scuro morbido dietro (`::before`), così si leggono anche quando dietro passa una carta. Lo stesso stile serve a P22 per "giocatori online" e titoli, quindi va in una classe comune;
  - **su computer** (da 1024 px) la navbar è larga quanto lo schermo, con avatar e amici vicino ai bordi (`--navbar-side`: 2% della larghezza, tra 16 e 32 px), alta 84 px, avatar da 58 px e icona degli amici da 40 px; passandoci sopra avatar e amici si animano come nel prototipo;
  - **logo** (provvisorio, quello vero in SVG arriva in P42): due carte di dorso a ventaglio che ogni 3 secondi circa si girano e mostrano Cavallo e Re dello stesso seme, un seme alla volta, e accanto il nome in due toni ("Cinque" crema, "cento" giallo) in rilievo; ferme sul dorso con "riduci movimento";
  - **pannello statistiche**: si apre toccando l'avatar, ingrandendosi dall'angolo dell'avatar; mostra partite, vinte, perse, percentuale e rating 1v1 e 2v2 (per ora con i dati finti di `app/static/dev/statistiche_esempio.json`, quelli veri arrivano in P30) e i link **Impostazioni** ed **Esci**; in fondo, piccola, la riga dei crediti delle immagini (D37): "Immagini delle carte: Matsoftware, CC BY-SA 3.0, da Wikimedia Commons" con il collegamento alla licenza;
  - **finestra "Accedi o registrati per giocare"**, riutilizzabile dalle altre pagine;
  - `core/layout.js`: il modulo che **ogni pagina importa** per far funzionare navbar, pannello statistiche e, più avanti, il pannello amici.
- *File* — crea: `app/templates/partials/navbar.html`, `app/static/css/components/navbar.css`, `stats-panel.css`, `app/static/js/core/layout.js`, `app/static/js/components/StatsPanel.js`, `app/static/js/components/LoginPrompt.js`, `app/static/img/cards-bg/` (le immagini del prototipo tranne il seme di denari: le 16 carte, il dorso e i 4 Assi a sagoma, con `LICENZA.md`; il logo usa dorso, Cavalli e Re, P22 usa le altre), `tests/frontend/test_navbar.py`. Modifica: `app/templates/base.html` (P19). Certezza: **sicuro**.
- *Fatto quando*: a 360 px la navbar sta sullo schermo senza sovrapporsi al contenuto e ha l'aspetto del prototipo, anche su computer (1366×657, 1440×900, 1920×1080); il pannello statistiche si apre e si chiude anche con la tastiera e con Esc; ogni pulsante con sola icona ha un'etichetta accessibile; il test controlla che la navbar abbia avatar, nome del gioco e pulsante amici.
- *Dipende da*: P19.

**P20 — Componenti carta e mano** · medio · decisione: no
- *Cosa e perché*: la carta disegnata in CSS come segnaposto, il dorso, la mano che sta in uno schermo di telefono; componenti come funzioni che restituiscono elementi, sempre con `textContent`.
- *File* — crea: `app/static/js/components/Card.js`, `Hand.js`, `app/static/css/components/card.css`, `hand.css`, `app/static/dev/carte.html`, `app/static/dev/carte.js` (pagina di prova con le 40 carte). Certezza: **sicuro**.
- *Fatto quando*: la pagina di prova mostra le 40 carte e una mano da 5 a 360 px; ogni carta ha attributi `data-suit` e `data-rank` stabili.
- *Dipende da*: P19.

**P21 — Tavolo di gioco con dati finti** · medio · decisione: **D15** (decisa il 28/09/2026)
- *Cosa e perché*: il tavolo (la tua mano, gli avversari coperti, la presa in corso, la briscola, i punteggi, il timer, i pulsanti "Canta 40/20"), disegnato da un'**unica funzione `render(vista)`** a partire da `app/static/dev/vista_*.json`. C'è un pulsante "esci" con conferma.
- *File* — crea: `app/templates/game/table.html`, `app/static/js/pages/game.js`, `app/static/js/components/Table.js`, `Trick.js`, `Scoreboard.js`, `Timer.js`, `SingButtons.js`, `app/static/css/components/table.css`, `trick.css`, `scoreboard.css`, `timer.css`, `app/static/css/pages/game.css`, `tests/api/test_pagina_tavolo.py`. Modifica: `app/blueprints/game/routes.py` (P4). Certezza: **sicuro**.
- *Fatto quando*: con `?demo=1v1` e `?demo=2v2` il tavolo si vede correttamente; i pulsanti delle mosse non legali sono disattivati; il test verifica che la pagina risponda e contenga i marcatori `data-*`.
- *Dipende da*: P8, P20, P40.

**P22 — Home con dati finti** · medio · decisione: no (specifiche dal prototipo approvato)
- *Cosa e perché*: la home del **prototipo di P52**, riscritta nei file del progetto:
  - "**giocatori online**" al centro, sotto la navbar (su telefono in fondo alla pagina), e i titoli delle due sezioni, scritti direttamente sul panno con lo stesso stile delle scritte della navbar (P40);
  - sezioni **Partita Veloce** e **Gioca con un amico**, ciascuna con due **carte-pulsante 1v1 e 2v2** (rosso, viola, giallo, blu; icona, modalità e sottotitolo in bianco in rilievo; forma di carta siciliana); su telefono una sotto l'altra, da 900 px affiancate; su telefono in orizzontale le quattro carte su una fila;
  - **carte-pulsante in rilievo**: superficie stampata, cornice doppia, l'**Asso del seme ridotto a sagoma** (solo CSS sull'immagine: filtri e `mix-blend-mode: soft-light`), spessore crema **solo in basso** (`--edge`, 2 px) senza niente sotto; con il mouse la carta si inclina verso il puntatore (non sul telefono né con "riduci movimento");
  - la pagina **non scorre mai**: le carte si rimpiccioliscono sugli schermi bassi (`--tile-h` del prototipo);
  - **modal della modalità a forma di carta**: la carta-pulsante toccata **vola al centro e si gira** (Web Animations, 0,82 s; chiusura al contrario con X, Esc, tocco fuori o "Gioca"; niente doppie aperture durante l'animazione). Sulla faccia bianca con la cornice nel colore della carta: X in alto a destra, titolo, descrizione, punti per vincere (150, 300, 500: Breve, Media, Classica) e "Gioca"; nella Partita Veloce anche "In breve" (con il rating, per ora finto) e un consiglio "Lo sapevi?" dal regolamento; in "Gioca con un amico" la lista degli amici online con "Invita", che prende lo spazio rimasto, e "Gioca" si attiva solo dopo che l'amico ha accettato (dati finti; la coda arriva in P28, gli inviti veri in P47). **Cosa entra dipende dall'altezza della carta** (container query: la faccia è `container: carta / size` e le regole `@container` vanno **dopo** le regole normali); la carta non scorre mai, scorre solo la lista degli amici da invitare (`overscroll-behavior: contain`);
  - **sfondo**: panno verde con luce da lampada e trama di feltro, e sopra una **cascata di carte** che cade senza fermarsi (dorsi, coppie Cavallo + Re, Assi, Tre; le più piccole sono più lontane, più lente e più scure), dietro a tutto; ferma con "riduci movimento". Lo script del prototipo diventa un componente;
  - la **schermata di attesa in coda** a tutto schermo (tempo trascorso, intervallo di rating, "Annulla") e l'avviso "**Hai una partita in corso: rientra**" (solo quando serve);
  - per chi non ha fatto il login, il tocco su una carta-pulsante apre la finestra "Accedi o registrati" (P40).

  Tutto funziona con `app/static/dev/home_esempio.json`. In `index.html` resta **solo il markup della home**, che estende `base.html`; niente blocchi `<style>` né codice JS nella pagina. Le immagini dello sfondo hanno licenza CC BY-SA 3.0: la riga di crediti sta in fondo al pannello statistiche (P40).
- *File* — crea: `app/static/css/pages/home.css`, `app/static/js/components/ModeModal.js`, `app/static/css/components/mode-modal.css`, `app/static/js/components/CardBackground.js`, `app/static/css/components/card-background.css`, `app/static/js/components/QueueOverlay.js`, `app/static/css/components/queue-overlay.css`, `app/static/js/components/ResumeBanner.js`, `tests/api/test_pagina_home.py`. Usa le immagini di `app/static/img/cards-bg/` (P40). Modifica: `app/templates/main/index.html` (P19, P40), `app/static/js/pages/home.js` (P40: per ora avvia solo `layout.js`), `app/blueprints/main/routes.py` (P4). Certezza: **sicuro**.
- *Fatto quando*: la home ha l'aspetto del prototipo a 360 px, su tablet e su computer; la pagina non scorre a nessuna misura (stesse misure controllate in `docs/prototipo/LEGGIMI.md`); il modal si apre da ogni carta-pulsante e in tutte e quattro le modalità ogni parte, "Gioca" compreso, sta dentro la cornice della carta senza sovrapporsi alle altre, alle misure controllate in `LEGGIMI.md` (portatili come 1366×657 e 1536×730, telefoni da 360×560 a 412×915, telefono in orizzontale 844×390 e 667×375); "Gioca" con un amico resta disattivato finché l'invito finto non è accettato; senza login il tocco apre la finestra di accesso; la schermata di coda si apre e si annulla; l'avviso di rientro compare solo se i dati finti lo prevedono; le carte dello sfondo passano sempre dietro a navbar, titoli, "giocatori online" e carte-pulsante, e le scritte restano leggibili anche con una carta chiara dietro; il test controlla che `index.html` non contenga blocchi `<style>` né script scritti nella pagina.
- *Dipende da*: P8, P40, P52.

**P41 — Pagina stanza privata con dati finti** · **tolto il 27/09/2026** per decisione dell'utente (vedi `DECISIONI.md`, Progetto e tempi). Le partite tra amici passano dagli inviti (P47).

**P46 — Pannello amici e finestra chat con dati finti** · medio · decisione: **D25**
- *Cosa e perché*: dal **prototipo di P52**. Al tocco sull'icona amici (in alto a destra) si apre un **pannello laterale** (a tutto schermo su telefono) con: campo per cercare uno username e mandare una richiesta, richieste in arrivo (accetta o rifiuta), lista amici con il pallino online o offline, e per ogni amico i pulsanti **Chatta**, **Invita 1v1** e **Invita 2v2**. "Chatta" apre la **finestra chat**, che su telefono occupa tutto lo schermo. Tutto con `app/static/dev/amici_esempio.json`. Il testo dei messaggi è sempre inserito con `textContent`. Il campo di scrittura accetta **1000 caratteri** (D26), non i 300 del prototipo.
- *File* — crea: `app/static/js/components/FriendsPanel.js`, `ChatWindow.js`, `app/static/css/components/friends-panel.css`, `chat.css`, `tests/frontend/test_pannello_amici.py`. Modifica: `app/static/js/core/layout.js` (P40). Certezza: **sicuro**.
- *Fatto quando*: il pannello si apre da qualsiasi pagina (tranne il tavolo, dove resta chiuso) e si chiude con "indietro" o con Esc; a 360 px la chat è leggibile e il campo di scrittura resta visibile; il test controlla che i componenti non usino `innerHTML` con dati esterni.
- *Dipende da*: P8, P40.

**P51 — Pagina "Regole" con mini-tutorial** · **tolto il 27/09/2026** per decisione dell'utente (vedi `DECISIONI.md`, Progetto e tempi).

#### Tempo reale e integrazione (I)

**P23 — Collegamento in tempo reale** · medio · decisione: **D14** (decisa il 28/09/2026)
- *Cosa e perché*: Flask-SocketIO in modalità threading; si collega solo chi ha fatto il login; `RoomManager` tiene le stanze in memoria con **un lock per stanza**. Lato pagina, `core/socket.js` gestisce connessione e riconnessione automatica.
- *File* — crea: `app/realtime/events.py`, `room.py`, `room_manager.py`, `app/static/js/core/socket.js`, `app/static/js/core/events.js`, `app/static/js/vendor/socket.io.min.js` (versione fissa, annotata in testa al file), `tests/sockets/conftest.py`, `tests/sockets/test_connessione.py`, `tests/sockets/test_lock_stanza.py`. Modifica: `app/sockets/__init__.py`, `app/sockets/connection_events.py` (P4). Certezza: **sicuro**.
- *Fatto quando*: test con client simulati: un utente senza login viene rifiutato; due utenti nella stessa stanza ricevono gli eventi; 50 azioni inviate insieme vengono elaborate una alla volta senza errori.
- *Dipende da*: P16, P8.

**P24 — Stanze e partita completa** · medio · decisione: no
- *Cosa e perché*: il primo momento in cui **si gioca davvero**: il server crea una stanza con i giocatori, la modalità e il punteggio scelto, la partita parte e il server applica il motore. Ognuno riceve **solo la propria vista**. Non esistono più le stanze private con codice: le stanze le crea solo il server. `room_manager.py` **espone** due funzioni che poi usano altri punti senza modificare il file: `create_room(giocatori, modalità, punteggio)`, per la coda (P28, P29) e per gli inviti (P47), e `find_room_of_user(...)`, per il rientro in partita (P44).
- *File* — modifica: `app/realtime/room.py`, `room_manager.py` (P23), `app/sockets/game_events.py` (P4), `app/static/js/pages/game.js` (P21). Crea: `tests/sockets/test_partita.py`. Certezza: **sicuro**.
- *Fatto quando*: test con client simulati: una partita 1v1 e una 2v2 fino al punteggio (a 150 per fare prima), con la stanza creata da `create_room`; una mossa illegale riceve un errore e non cambia niente; le due funzioni esposte hanno un test. La prova a mano con due browser si fa da P28, quando c'è la coda.
- *Dipende da*: P15, P21, P23.

**P25 — Timer, riconnessione, abbandono** · medio · decisione: **D12, D13** (decise il 28/09/2026: regole in `docs/REGOLE-GIOCO.md`, "Tempo per turno")
- *File* — modifica: `app/realtime/room.py` (P24), `app/sockets/game_events.py` (P24), `app/sockets/connection_events.py` (P23), `app/static/js/pages/game.js` (P24). Crea: `tests/sockets/test_timer_riconnessione.py`. Certezza: **sicuro**.
- *Fatto quando*: con i tempi ridotti dalla configurazione di test: a turno scaduto il server gioca la mossa automatica; chi si riconnette in tempo riceve di nuovo la sua vista; oltre il tempo la partita finisce per abbandono.
- *Dipende da*: P24.

**P28 — Matchmaking 1v1** · medio · decisione: **D16** (decisa il 28/09/2026: i valori di `config.py`)
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

**P47 — Amici online e inviti a partita** · medio · decisione: **D27** (decisa il 28/09/2026)
- *Cosa e perché*: il pannello amici mostra **chi è online** in tempo reale e riceve le richieste di amicizia senza ricaricare la pagina. Nel modal di **Gioca con un amico** la lista degli amici online diventa vera: "Invita" manda l'invito, l'amico lo riceve con un conto alla rovescia, e **"Gioca" si attiva solo quando ha accettato**. Poi:
  - **1v1**: il server crea subito la stanza con i due amici (`create_room` di P24);
  - **2v2**: i due amici entrano **insieme** nella coda 2v2 come coppia (P29), e gli avversari arrivano dal matchmaking.

  Il 1v1 contro un amico **non conta per il rating**; il 2v2 con un amico come compagno **conta**. Il pannello passa dai dati finti a quelli veri (API di P45 ed eventi socket).
- *File* — crea: `app/realtime/invites.py`, `tests/sockets/test_inviti.py`. Modifica: `app/sockets/friends_events.py` (P4), `app/static/js/components/FriendsPanel.js` (P46), `app/static/js/components/ModeModal.js` (P28). Certezza: **sicuro**.
- *Fatto quando*: test con client simulati: un amico che si collega appare online agli altri; un invito 1v1 accettato porta i due nella stessa stanza; un invito 2v2 accettato mette la coppia in coda; un invito scaduto o rifiutato avvisa chi l'ha mandato; non si può invitare chi non è amico o chi è già in partita.
- *Dipende da*: P24, P29, P44, P45, P46.

**P48 — Chat tra amici** · medio · decisione: **D24, D25, D26** (decise il 27 e 28/09/2026)
- *Cosa e perché*: messaggi in tempo reale **solo tra amici**, salvati nel database, con la cronologia che si carica all'apertura della chat e un contatore dei messaggi non letti. Protezioni: lunghezza massima e limite di frequenza (D26), testo sempre mostrato come testo, mai nei log. I messaggi **non si cancellano mai** (D24): spariscono solo con l'account di uno dei due (lo fa il database, P5). Se l'amicizia finisce o c'è un blocco, la conversazione resta visibile ma non si può più scrivere.
- *File* — crea: `app/services/chat_service.py`, `app/repositories/chat_repo.py`, `tests/sockets/test_chat.py`. Modifica: `app/sockets/chat_events.py` (P4), `app/static/js/components/ChatWindow.js` (P46). Certezza: **sicuro**.
- *Fatto quando*: test con client simulati: un messaggio arriva solo al destinatario; a chi non è amico il messaggio viene rifiutato; un messaggio troppo lungo o troppo frequente viene rifiutato con un avviso; un messaggio con `<script>` viene mostrato come testo; la cronologia si carica in ordine; dopo la fine dell'amicizia o un blocco la cronologia si legge ma un messaggio nuovo viene rifiutato.
- *Dipende da*: P23, P45, P46.

**P54 — Frasi del tavolo: elenco e salvataggio** · **tolto il 27/09/2026**, lo stesso giorno in cui era stato aggiunto: le frasi del tavolo non si salvano (D24), quindi non c'è niente da fare nel database. L'elenco delle frasi passa a P55.

**P55 — Frasi del tavolo in tempo reale** · piccolo · decisione: no (D24 decisa)
- *Cosa e perché*: al tavolo i giocatori si mandano solo **frasi pronte** (D24), in italiano e in siciliano. Questo punto fissa l'**elenco unico** delle frasi (codice e testo, per esempio `amuni` → "Amunì!"; l'elenco approvato è in `DECISIONI.md`, D24) e l'evento con cui un giocatore ne manda una (nomi e dati da P8). Sotto il lock della stanza il server controlla che chi manda sia seduto a quel tavolo, che il codice sia nell'elenco e che sia passato il tempo minimo (**una frase ogni 3 secondi** per giocatore); poi la manda a **tutti i giocatori della partita**, anche agli avversari nel 2v2, e **non la salva da nessuna parte**. In memoria, nella stanza, resta solo l'ora dell'ultima frase di ogni giocatore, che sparisce con la stanza. All'ingresso nella stanza manda l'elenco delle frasi, così la pagina non ne ha una copia sua. In `config.py` aggiunge `TABLE_PHRASE_MIN_INTERVAL_SECONDS = 3` (`CHAT_RETENTION_DAYS` è già stata tolta il 28/09/2026).
- *File* — crea: `app/realtime/table_phrases.py`, `tests/sockets/test_frasi_tavolo.py`. Modifica: `app/sockets/game_events.py` (P25), `config.py` (P4). Certezza: **sicuro**.
- *Fatto quando*: test con client simulati: la frase arriva a tutti e 2 (1v1) o tutti e 4 (2v2) i giocatori; chi non è al tavolo viene rifiutato; un codice sconosciuto viene rifiutato; una seconda frase prima di 3 secondi viene rifiutata con un avviso (con i tempi ridotti della configurazione di test); nessuna frase finisce nel database né nei log.
- *Dipende da*: P8, P25.

**P56 — Frasi del tavolo nella pagina** · piccolo · decisione: no (D24 decisa)
- *Cosa e perché*: al tavolo un pulsante apre l'elenco delle frasi (quello ricevuto dal server); toccandone una, la frase compare per qualche secondo in un fumetto vicino al posto di chi l'ha mandata, per tutti. Dopo l'invio il pulsante resta disattivato per 3 secondi. Il testo si inserisce sempre con `textContent`; senza connessione non parte niente. Lo stile segue il prototipo (P52).
- *File* — crea: `app/static/js/components/TablePhrases.js`, `app/static/css/components/table-phrases.css`, `tests/frontend/test_frasi_tavolo.py`. Modifica: `app/static/js/pages/game.js` (P25), `app/templates/game/table.html` (P21). Certezza: **sicuro**.
- *Fatto quando*: a 360 px l'elenco delle frasi sta sullo schermo e il fumetto non copre le carte in mano; il pulsante con sola icona ha un'etichetta accessibile; il test controlla che il componente non usi `innerHTML` con dati esterni.
- *Dipende da*: P55.

**P57 — Momenti del tavolo: ultima presa, fine mano, carte del canto** · piccolo · decisione: no (D15 decisa) — aggiunto il 28/09/2026
- *Cosa e perché*: tre momenti della partita che P24 non disegna e P25 non tocca (tempo, riconnessione e abbandono):
  - l'**ultima presa** (`last_trick`): quando una presa si chiude, le carte restano per un momento al centro, con chi l'ha vinta, prima di sparire;
  - il **riepilogo di fine mano** (`last_hand`): a inizio della mano nuova, un riquadro con i punti delle carte prese, dei canti e il totale di ogni squadra (durante la mano i punti delle prese sono nascosti: si vedono solo qui, decisione di P8);
  - le **carte del canto** (`game:sang`, D15): Re e Cavallo cantati si mostrano a tutti per `show_seconds` secondi (3) accanto a chi ha cantato; poi resta l'icona fissa che c'è già (P21). Oggi P24 scrive solo "X ha cantato 40 a coppe".
  Si prova con le viste finte (`?demo=`) e con una partita vera; con "riduci movimento" niente animazioni.
- *File* — crea: `app/static/js/components/HandSummary.js`, `app/static/css/components/hand-summary.css`, `tests/frontend/test_momenti_tavolo.py`. Modifica: `app/static/js/pages/game.js` (P25), `app/static/js/components/Table.js`, `Trick.js`, `app/static/css/components/table.css`, `trick.css` (P21). Certezza: **sicuro**.
- *Fatto quando*: a 360 px ultima presa, riepilogo e carte del canto stanno nello schermo e non coprono le carte in mano; le carte del canto spariscono dopo `show_seconds`; il testo è inserito sempre con `textContent`; il test controlla i marcatori `data-*` dei tre momenti.
- *Dipende da*: P24, P25.

**P58 — Ultima presa della mano nella vista** · piccolo · decisione: no (approvata dai tre il 28/09/2026) — aggiunto il 28/09/2026
- *Cosa e perché*: quando l'ultima presa chiude la mano il motore comincia subito la mano nuova con `last_trick` a `null`, quindi la pagina non riceve mai quelle carte e la carta che chiude la mano non si vede (domanda di Christian in P57). Il risultato della mano (`HandResult`) conserva anche l'ultima presa, e la vista la dà in **`last_hand.last_trick`**, con la stessa forma di `last_trick` (`winner_seat`, `cards`). Cambia il contratto 3.3 (approvato dai tre).
- *File* — modifica: `app/game/engine/state.py`, `game.py`, `views.py` (P13–P15), `docs/CONTRATTO-SOCKET.md` (3.3), `app/static/dev/vista_1v1.json`, `vista_2v2.json` (P8), `tests/engine/test_partita.py`, `test_viste.py`. Certezza: **sicuro**. La pagina (`game.js`) la adatta poi Christian, con un lotto suo, dopo che P58 è in `dev`.
- *Fatto quando*: a fine mano la vista di ogni giocatore ha `last_hand.last_trick` con le carte dell'ultima presa e chi l'ha vinta; gli esempi di `app/static/dev/` hanno le stesse chiavi della vista vera.
- *Dipende da*: P15.

**P59 — 2v2 con più amici invitati** · medio · decisione: no (approvata dai tre il 28/09/2026; cambia D27) — aggiunto il 28/09/2026 — **file non tutti sicuri, vedi sezione 9.2**
- *Cosa e perché*: nel 2v2 "Gioca con un amico" si può invitare più di un amico: con **un solo amico** si è in squadra insieme (come oggi); con **più amici** le squadre si tirano a sorte. Oggi si invita un amico alla volta (D27, contratto 5.3: un secondo `invite:send` risponde `busy`). I dettagli (quanti amici al massimo, cosa succede se non accettano tutti, da dove arrivano i giocatori che mancano) si fissano all'inizio del punto e si scrivono nel contratto 5.3, con l'accordo dei tre.
- *Fatto quando*: test con client simulati: due o tre amici invitati che accettano giocano nella stessa partita 2v2, con le squadre a sorte; con un solo amico il comportamento di oggi non cambia.
- *Dipende da*: P29, P47.

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
- *Cosa e perché*: come deciso, prima si prova un **set con licenza libera**, poi lo si confronta con le vostre immagini. Fino ad allora in gioco si vedono le carte segnaposto di P20; P35 cambia solo la faccia (`Card.js`, `card.css`), non la mano né il tavolo.
- **Proposta per la fonte (28/09/2026, da verificare)**: le carte già nel progetto (`app/static/img/cards-bg/`: Cavallo, Re, Asso e Tre) sono ritagli delle scansioni di **Matsoftware** su Wikimedia Commons, un foglio per seme (`Carte_da_gioco_siciliane_-_<seme>.jpg`), con licenza **CC BY-SA 3.0**. Probabilmente ogni foglio contiene tutte le 10 carte del seme: in quel caso si ritagliano da lì tutte le 40 carte, con la stessa licenza e la riga dei crediti che c'è già (D37, D39). Da controllare all'inizio di P35, aprendo le quattro scansioni.
- *Fatto quando*: le 40 carte si vedono con le immagini scelte, la licenza è annotata, e il peso totale è sotto 1 MB.
- *Dipende da*: P20.

**P42 — Logo vero** · piccolo · decisione: no (logo "Cinquecento" disegnato da Claude in SVG, vedi `DECISIONI.md`) — **file non tutti sicuri, vedi sezione 9.2**
- *Cosa e perché*: il logo **"Cinquecento"** al centro della navbar, leggibile a 40 px di altezza, più l'icona della scheda del browser (favicon). Parte dal logo del prototipo di P52 (due carte a ventaglio che si girano e il nome in due toni in rilievo), già riscritto in CSS da P40.
- *Fatto quando*: il logo si vede nitido a 40 px su telefono e computer (anche in tema scuro, se P53 è già fatto); il tocco porta alla home.
- *Dipende da*: P40.

**P43 — Immagini degli avatar** · piccolo · **decisione: sì** (D29: decisi il 28/09/2026 numero e formato, restano quali figure, autore e licenza) — **file non tutti sicuri, vedi sezione 9.2**
- *Cosa e perché*: le immagini del set di avatar scelto in D29, mostrate nella navbar, nel pannello statistiche, nelle impostazioni e nella lista amici.
- *Fatto quando*: ogni avatar di `avatars.py` ha la sua immagine; chi non ne ha scelto uno vede le iniziali; il peso totale è contenuto (sotto 300 KB).
- *Dipende da*: P17, P40, P46.

**~~P53 — Tema scuro automatico~~** · **tolto il 30/09/2026** (decisione dei tre: resta solo il tema chiaro)
- *Cosa e perché*: rimandato alla fine per scelta dell'utente (27/09/2026). Le pagine passano da sole ai colori scuri quando il telefono o il computer sono in tema scuro (`prefers-color-scheme`). Se P19 e gli altri punti hanno usato sempre le variabili CSS, basta aggiungere in `variables.css` i valori scuri della palette "Carretto siciliano".
- *Fatto quando*: con il dispositivo in tema scuro tutte le pagine (home, pannelli, modal, tavolo, impostazioni, accesso) sono leggibili e hanno contrasto sufficiente; le carte dello sfondo restano visibili ma non abbagliano; con il tema chiaro non cambia niente.
- *Dipende da*: P34 (dopo la rifinitura di tutte le pagine).

**P61 — Regole della password** · piccolo · decisione: sì (D8, chiusa il 29/09/2026) — aggiunto il 29/09/2026 — **file da confermare, vedi sezione 9.2**
- *Cosa e perché*: D8 ha deciso che la password ha **almeno 8 caratteri, almeno una maiuscola, almeno un numero e almeno un simbolo** ("simbolo" = un carattere che non è una lettera, un numero o uno spazio). Oggi la registrazione controlla solo la lunghezza (P16). Vale per le password nuove: gli account che ci sono già entrano con la loro.
- *Fatto quando*: la registrazione rifiuta una password senza maiuscola, numero o simbolo con un messaggio chiaro per ogni regola mancante; la pagina di registrazione dice le regole prima dell'invio; i test di P16 usano password valide.
- *Dipende da*: P16.

**P62 — Font delle icone nel progetto** · piccolo · decisione: sì (D40, opzione b) — aggiunto e fatto il 29/09/2026
- *Cosa e perché*: le icone arrivavano da Google Fonts in un file da 5,4 MB e comparivano dopo qualche secondo (anche 20–45 sul PC di Christian). Il file con solo le icone usate pesa 6 KB e sta nel progetto (`app/static/fonts/`), precaricato da `base.html`.
- *File* — crea: `app/static/fonts/material-symbols-rounded.woff2`, `app/static/fonts/icone.txt`, `tests/frontend/test_icone.py`; modifica: `app/templates/base.html`, `app/static/css/base/typography.css`, `docs/prototipo/LEGGIMI.md`. Certezza: **sicuro**.
- *Fatto quando*: le icone compaiono insieme alla pagina; ogni icona usata nel codice è nel font (lo controlla il test).
- *Dipende da*: P19.

### Correzioni e richieste dalla prova sul telefono (29/09/2026)

Il 29/09/2026 Christian e un amico hanno giocato dal telefono (server sul PC di Christian, stessa rete Wi-Fi) e hanno scritto le cose da sistemare. Sono diventate i punti P63–P73: i primi sei di Giuseppe (server, motore, tempo reale), gli altri cinque di Christian (pagina del tavolo e home). Le decisioni sono in `DECISIONI.md` (29/09/2026), le domande aperte in `DA-DECIDERE.md` (D43, D44).

**P63 — Richiesta di amicizia con spazi prima o dopo il nome** · piccolo · decisione: sì (presa il 29/09/2026) — Giuseppe
- *Cosa e perché*: scrivendo il nome dell'amico con uno spazio prima o dopo (succede spesso con la tastiera del telefono) il server cerca il nome con lo spazio e risponde "Nessun utente con questo username.". Il server toglie gli spazi all'inizio e alla fine prima di cercare: uno username non può contenere spazi (D7), quindi non è una correzione silenziosa di un dato valido.
- *File* — modifica: `app/services/friend_service.py` (`check_username` o `send_request`), `tests/api/test_amicizie.py`. Certezza: **sicuro**.
- *Fatto quando*: " Mario " trova Mario; uno spazio in mezzo al nome si rifiuta ancora con il messaggio di sempre; un test lo prova dalla rotta vera.
- *Dipende da*: P45.

**P64 — Niente canto nella prima presa della mano** · piccolo · decisione: sì (regola nuova del 29/09/2026) — Giuseppe — **file da confermare, vedi sezione 9.2**
- *Cosa e perché*: regola nuova: durante la **prima presa di ogni mano** nessuno può cantare, né 40 né 20; si canta dalla seconda presa in poi, con le regole di sempre (nel proprio turno, prima della carta). La pagina non cambia: usa `legal.sing`, che nella prima presa è vuoto.
- *File* — modifica: `app/game/engine/singing.py`, `docs/REGOLE-GIOCO.md` (sezione Canti), `tests/engine/test_canti.py`; forse `state.py` se serve sapere a che presa si è. Certezza: **da confermare** all'inizio del punto.
- *Fatto quando*: nella prima presa `legal.sing` è vuoto e `sing` rifiuta con un messaggio chiaro; dalla seconda presa si canta come prima; la prova che confronta `singable_suits` e `sing` (3.000 situazioni) passa ancora; il regolamento lo dice.
- *Dipende da*: P12, P13.

**P65 — Amico sbloccato che non compare più online nella carta-pulsante** · piccolo · decisione: no — Giuseppe — **file non sicuri, vedi sezione 9.2**
- *Cosa e perché*: dopo aver bloccato un amico, averlo sbloccato ed essere tornati amici, l'amico non compare più tra gli amici online nella carta-pulsante "Gioca con un amico" (la lista da invitare). Prima si riproduce con un test, poi si trova dove si perde (elenco degli amici online di P47, presenza di P44 o pagina).
- *Fatto quando*: un test fa blocca → sblocca → richiesta → accetta e controlla che l'amico torni online nella lista da invitare, senza ricaricare la pagina.
- *Dipende da*: P44, P45, P47.

**P66 — Mossa automatica dopo il rientro** · piccolo · decisione: no — Giuseppe — **file non sicuri, vedi sezione 9.2**
- *Cosa e perché*: uscendo dal browser e rientrando nella partita, allo scadere dei 30 secondi del turno la carta automatica non parte più (P25). Prima si riproduce con un test (suite `sockets` o `e2e`), poi si corregge.
- *Fatto quando*: dopo uscita e rientro, il turno scaduto gioca la carta automatica come prima; il test lo prova con il turno accorciato (`shorten_turn`).
- *Dipende da*: P25.

**P67 — Punti della mano in corso nella vista** · piccolo · **decisione: sì** (D44) — Giuseppe
- *Cosa e perché*: la pagina deve mostrare i punti della mano in corso, aggiornati a ogni presa e a ogni canto (P72). ~~Solo i punti della propria squadra~~: **superato da D44** (30/09/2026), il server manda i punti di tutte e due le squadre. Oggi la vista ha solo i totali della partita (`scores`) e i punti della mano finita (`last_hand`). Il server aggiunge un campo nella vista (nome da fissare nel punto); è un cambiamento del contratto 3.3, che vale con l'ok di Giuseppe e Christian.
- *File* — modifica: `app/game/engine/views.py`, `docs/CONTRATTO-SOCKET.md` (3.3), `app/static/dev/*.json` (esempi della vista), `tests/engine/test_viste.py`; forse `state.py` o `game.py`. Certezza: **quasi sicuro** (da D44).
- *Fatto quando*: la vista di ogni giocatore ha i punti della mano in corso di tutte e due le squadre (carte prese più canti, D44); gli esempi della vista sono aggiornati e i test che li confrontano passano.
- *Dipende da*: P15, P58; aspetta D44.

**P68 — Partita contro la CPU: mosse e stanza** · grande · **decisione: sì** (D43) — Giuseppe — **file non sicuri, vedi sezione 9.2**
- *Cosa e perché*: richiesta nuova del 29/09/2026: si può giocare contro la CPU. Le mosse **non sono casuali**: la strategia si decide insieme (D43). Il motore resta puro: la scelta della mossa è una funzione come `auto_move` (dalla vista del giocatore CPU e da `legal`), e la stanza la fa giocare quando tocca alla CPU.
- *Fatto quando*: da un evento del tempo reale si avvia una partita contro la CPU, la CPU gioca e canta secondo la strategia di D43 senza vedere le carte altrui, e la partita arriva alla fine; i test la giocano intera.
- *Dipende da*: P15, P24, P25; D43 (decisa il 04/10/2026: `DECISIONI.md`, Gioco).
- *Stato (01/10/2026)*: stanza, evento `cpu:start` e una prima strategia sono in `dev` (commit `a7b1346`); la strategia è stata scartata da Christian (troppo facile da battere): va rifatta dopo un accordo su D43. **04/10/2026**: D43 decisa (strategia "simulazione" con calcolo esatto a mazzo finito, solo 1v1, non salvata, `cpu: true`, icona robot, attesa tra 1 e 2 s: `DECISIONI.md`, Gioco); si può rifare.

**P69 — Tocchi e clic al tavolo** · piccolo · decisione: sì (presa il 29/09/2026) — Christian — **file non sicuri, vedi sezione 9.2**
- *Cosa e perché*: tre difetti trovati giocando dal telefono. (1) Il doppio tocco ingrandisce la pagina e tenendo premuta una carta il telefono la ingrandisce o apre il suo menù: al tavolo non deve succedere (lo zoom con due dita resta, per l'accessibilità). (2) Toccando in fretta le carte a fine mano, mentre si vedono l'ultima presa e il riepilogo, si riesce a giocare una carta: finché ci sono ultima presa e riepilogo le carte in mano non si giocano. (3) Toccando più volte l'icona delle frasi del tavolo, in alto a destra, si mandano frasi a raffica anche se sembra spenta: durante la pausa (P56) il pulsante non manda niente. Se il server accetta frasi più spesso del limite di P55, la correzione del server va a Giuseppe.
- *Fatto quando*: al tavolo, sul telefono, doppio tocco e tocco lungo non ingrandiscono né aprono menù; nei test del browser un clic sulle carte durante l'ultima presa o il riepilogo non manda `game:play`, e i clic ripetuti sulle frasi ne mandano una sola per pausa.
- *Dipende da*: P56, P57, P58 (pagina).

**P70 — Animazioni del tavolo** · medio · decisione: sì (presa il 29/09/2026) — Christian — **file non sicuri, vedi sezione 9.2**
- *Cosa e perché*: (1) la carta giocata **vola sul tavolo con un movimento fluido**, ruotando leggermente su sé stessa, come lanciata; (2) si può giocare una carta solo quando è **finita l'animazione della carta precedente**; (3) a inizio mano un'animazione **mescola il mazzo** e **distribuisce le carte una alla volta** ai giocatori; (4) le carte in mano agli avversari **partono dal bordo dello schermo, nascoste per metà**, e la carta pescata dall'avversario **entra fluida** tra quelle che ha in mano; (5) difetto: ogni tanto le carte diventano **bianche per qualche millisecondo** (da riprodurre: forse le immagini ricreate a ogni vista). Con "riduci movimento" del dispositivo le animazioni si accorciano o si tolgono. Le animazioni non devono mangiare troppo del turno di 30 secondi, che il server conta già.
- *Fatto quando*: le quattro animazioni si vedono su telefono e computer e non bloccano la pagina; le carte non lampeggiano più; i test del tavolo passano anche con le animazioni (marcatori `data-*` per sapere quando un'animazione è finita).
- *Dipende da*: P57, P58 (pagina); meglio dopo P71, che sposta mazzo e carte.

**P71 — Grafica del tavolo** · medio · decisione: sì (presa il 29/09/2026) — Christian — **file non sicuri, vedi sezione 9.2**
- *Cosa e perché*: (1) via la scritta "Carte franche" prima del canto del 40; (2) la **briscola** si mostra con il **seme sopra il mazzo, al centro**, senza il nome del seme; quando il mazzo finisce sparisce anche il seme; (3) un segno **vicino alle carte in mano** fa capire qual è la briscola (forma da proporre nel punto); (4) via la scritta "mazziere"; (5) sul telefono il **mazzo** sta più a destra ed è **più grande**; (6) le **carte giocate sul tavolo** (dopo il lancio) sono più grandi; (7) il pulsante delle **frasi del tavolo** ("chat") va **sopra le carte in mano, a destra**.
- *Fatto quando*: tutto quanto sopra si vede su telefono (360 px) e computer; il tavolo non scorre; i test del tavolo e delle frasi passano, aggiornati ai nuovi marcatori. Un'icona nuova va in `app/static/fonts/icone.txt` (P62).
- *Dipende da*: P57, P58 (pagina).

**P72 — I propri punti sopra le carte in mano** · piccolo · **decisione: sì** (D44) — Christian — **file da confermare, vedi sezione 9.2**
- *Cosa e perché*: i punti della mano in corso si vedono al tavolo, aggiornati in tempo reale a ogni presa e canto. ~~Solo i punti della propria squadra~~: **superato da D44** (30/09/2026): tabellone e riepilogo restano come sono; i tuoi punti sopra la tua mano; nel 1v1 quelli dell'avversario sotto la sua mano, nel 2v2 quelli degli avversari una volta sola accanto alla mano del giocatore a sinistra.
- *Fatto quando*: durante la mano il numero sopra le carte cambia a ogni presa e a ogni canto della propria squadra; i test del tavolo lo provano con gli esempi della vista.
- *Dipende da*: P67; aspetta D44.

**P73 — Partita contro la CPU nella home** · medio · **decisione: sì** (D43) — Christian — **file non sicuri, vedi sezione 9.2**
- *Cosa e perché*: il modo di avviare dalla home la partita contro la CPU (P68), con la grafica delle carte-pulsante e della carta-modal. La home non deve scorrere (va misurata come in P22).
- *Fatto quando*: dalla home si avvia una partita contro la CPU e si arriva al tavolo; `test_pagina_home.py` misura la home senza scorrimento; senza connessione il pulsante è spento (P33).
- *Dipende da*: P68 rifatto, P59 (tocca anche lui `home.js` e `ModeModal.js`); D43 decisa il 04/10/2026 (una scelta nella carta-modal, icona robot).

### Correzioni e richieste dalla prova a mano del 01/10/2026

Il 01/10/2026 Christian e Giuseppe hanno provato il gioco a mano, insieme, e Christian ha scritto le cose da sistemare. Sono diventate i punti P74–P85: quattro di Giuseppe (vista, server e tempo reale: P75, P82, P83, P84), gli altri di Christian (pagina del tavolo e chat). Le decisioni sono in `DECISIONI.md` (01/10/2026), la domanda aperta in `DA-DECIDERE.md` (D45). **Da computer** vuol dire da **1024 px di larghezza in su**, la stessa soglia di P70 e P72; sul telefono il tavolo non cambia, salvo dove il punto dice "su tutti e due".

**P74 — Tavolo da computer: avatar, carte degli avversari, "Esci", tabellone e propri punti** · medio · **decisione: sì** (01/10/2026; le posizioni del tabellone si scelgono nel punto) — Christian — **file non sicuri, vedi sezione 9.2**
- *Cosa e perché*: da computer il tavolo ha troppo spazio vuoto. (1) Gli **avatar di tutti** i giocatori si spostano accanto alle loro carte: il tuo **a sinistra della tua mano**, quelli degli avversari (e del compagno nel 2v2) accanto al loro ventaglio, dalla parte che si propone nel punto; (2) le **carte degli avversari** sono più grandi (oggi circa 56 px da 1024 px in su, P70); (3) **"Esci"** va nell'**angolo in alto a sinistra**; (4) il **tabellone** si sposta dove riempie lo spazio vuoto: all'inizio del punto Claude propone 2–3 posizioni, con una raccomandazione, e Christian sceglie; (5) i **tuoi punti della mano** (P72) stanno **a destra della tua mano**, non più sopra.
- *Fatto quando*: a 1280×720 e 1440×900 tutto quanto sopra si vede, il tavolo non scorre e niente si sovrappone (presa, ventagli, avatar, fumetti delle frasi); sul telefono non cambia niente; `test_grafica_tavolo.py` e `test_punti_mano.py` misurano le posizioni nuove.
- *Dipende da*: P70, P71, P72 (pagina).

**P75 — La carta che sta vincendo la presa nella vista** · piccolo · **decisione: sì** (01/10/2026, cambio del contratto approvato da Giuseppe e Christian) — Giuseppe
- *Cosa e perché*: per evidenziare la carta che sta vincendo la presa in corso (P76) la pagina non deve calcolare le regole (P21): lo dice il server. La vista ha un campo nuovo con la carta che oggi vince la presa (nome e forma da fissare all'inizio del punto con Christian), vuoto quando sul tavolo non c'è nessuna carta. Usa la stessa funzione del motore che decide la presa (`trick_winner`, P11), così le due risposte non possono essere diverse.
- *File* — modifica: `app/game/engine/views.py`, `docs/CONTRATTO-SOCKET.md` (3.3), `app/static/dev/*.json` (esempi della vista), `tests/engine/test_viste.py`. Certezza: **quasi sicuro** (come P67).
- *Fatto quando*: in ogni momento della presa il campo indica la carta che la vincerebbe se finisse lì (anche quando una briscola arriva dopo); gli esempi della vista sono aggiornati e i test che li confrontano passano.
- *Dipende da*: P11, P15.

**P76 — Presa con le carte affiancate e la carta che vince evidenziata** · piccolo · decisione: sì (01/10/2026) — Christian — **file non sicuri, vedi sezione 9.2**
- *Cosa e perché*: oggi le carte giocate al centro sono sovrapposte una sull'altra. (1) Le carte della presa stanno **affiancate**, senza coprirsi (la disposizione si propone nel punto, per 1v1 e 2v2, telefono e computer); (2) la carta che **sta vincendo** la presa (campo di P75) è **evidenziata** rispetto alle altre, e il segno si sposta quando una carta nuova la supera. Vale anche per l'ultima presa mostrata a fine presa (P57).
- *Fatto quando*: su telefono (360 px) e computer le carte della presa non si coprono e il tavolo non scorre; la carta evidenziata è sempre quella del campo di P75 (test con gli esempi della vista); il segno non si affida solo al colore (accessibilità).
- *Dipende da*: **P75**, P70, P71.

**P77 — Briscola solo sul mazzo, anche a mazzo finito** · piccolo · **decisione: sì** (01/10/2026, cambia P71 del 29/09/2026) — Christian — **file non sicuri, vedi sezione 9.2**
- *Cosa e perché*: (1) via il **tondo con il seme** sopra le carte in mano (P71): la briscola si vede **solo sul mazzo**; (2) quando il mazzo **finisce**, al suo posto **resta il seme della briscola** che c'era sopra, fino a fine mano. Prima del canto del 40 non c'è briscola e non si vede niente.
- *Fatto quando*: durante la mano il seme della briscola si vede solo dov'è il mazzo, anche dopo l'ultima pescata; il tondo vicino alla mano non c'è più; i tuoi punti della mano (P72, o il posto nuovo di P74) restano dove devono; i test del tavolo sono aggiornati ai marcatori nuovi.
- *Dipende da*: P71, P72.

**P78 — Animazioni più realistiche** · medio · decisione: sì (01/10/2026) — Christian — **file non sicuri, vedi sezione 9.2**
- *Cosa e perché*: le animazioni di P70 devono sembrare più vere. (1) Dopo ogni presa le carte si **pescano una alla volta**, nell'ordine giusto (prima chi ha vinto la presa, poi gli altri in ordine di turno), non tutte insieme; (2) il **lancio di una carta** parte solo quando è **finito il lancio della carta precedente**: se due viste arrivano vicine (un avversario veloce, la mossa automatica, la CPU) le animazioni si mettono in fila; (3) altri ritocchi dello stesso tipo si propongono nel punto. Con "riduci movimento" restano corte o assenti, e le animazioni non devono mangiare troppo dei 30 secondi del turno.
- *Fatto quando*: nei test del browser (con "riduci movimento" spento) le carte pescate arrivano una dopo l'altra e due lanci vicini non partono insieme; le durate in `game.js` restano uguali a quelle dei CSS (test di P70).
- *Dipende da*: P70; meglio dopo P74 e P76, che spostano le cose sul tavolo.

**P79 — Carte bianche per qualche secondo al tavolo** · piccolo · decisione: no — Christian — **file non sicuri, vedi sezione 9.2**
- *Cosa e perché*: in partita, **da telefono e da computer**, capita spesso che le carte (in mano o sul tavolo) restino **bianche per qualche secondo** prima di comparire. Non è il lampeggio di pochi millisecondi corretto in P70: l'ipotesi [D] è che l'immagine di una carta si scarichi solo la prima volta che serve. Prima si riproduce (per esempio con la rete rallentata nel browser dei test), poi si corregge: per esempio scaricando le 40 carte e il dorso appena si apre il tavolo.
- *Fatto quando*: un test del browser con la rete rallentata non vede mai una carta bianca dopo il caricamento del tavolo; il peso delle immagini resta quello di P35.
- *Dipende da*: P35, P70.

**P80 — Frasi del tavolo aperte di lato, da computer** · piccolo · decisione: sì (01/10/2026) — Christian — **file non sicuri, vedi sezione 9.2**
- *Cosa e perché*: da computer l'elenco delle **frasi del tavolo** (i messaggi veloci, P56), quando è aperto, copre il tavolo. Da computer si apre come **pannello sul lato destro**, senza coprire il tavolo; sul telefono resta com'è.
- *Fatto quando*: a 1280×720 e 1440×900, con l'elenco aperto, la presa, la tua mano e le carte degli avversari restano visibili e cliccabili; sul telefono non cambia niente; i test delle frasi (`test_frasi_pagina.py`) passano.
- *Dipende da*: P56, P71; meglio dopo P74, che sposta le cose a destra della mano.

**P81 — La tastiera del telefono si chiude a ogni messaggio della chat** · piccolo · decisione: no — Christian
- *Cosa e perché*: nella home, dal telefono, mandando un messaggio a un amico la tastiera si chiude e si riapre; deve restare aperta. Causa probabile [L]: mentre aspetta la risposta del server `ChatWindow.js` spegne anche la casella di testo (`input.disabled = true`), e il telefono chiude la tastiera di un campo spento. Si spegne solo il pulsante "Invia" (resta la regola contro il doppio invio) e la casella tiene il fuoco.
- *File* — modifica: `app/static/js/components/ChatWindow.js`, un test in `tests/frontend/` (per esempio `test_pannello_amici.py`). Certezza: **quasi sicuro**.
- *Fatto quando*: dopo "Invia" la casella resta attiva e con il fuoco, anche mentre si aspetta la risposta; un doppio invio manda un solo messaggio; senza connessione resta tutto spento come in P33.
- *Dipende da*: P48.

**P82 — Giocatori online veri nella home anche senza login** · piccolo · decisione: no — Giuseppe — **file non sicuri, vedi sezione 9.2**
- *Cosa e perché*: nella home, senza login, si vede sempre "24 giocatori online": è il numero dei dati finti di sviluppo (`app/static/dev/home_esempio.json`) [L], perché senza login la pagina non si collega al tempo reale e il numero vero non arriva mai; nella demo vera la riga resterebbe vuota [D]. Serve una via senza login per il **solo numero** (per esempio una rotta HTTP pubblica o un evento senza login, con un limite di frequenza), che non dica niente di più.
- *Fatto quando*: senza login la home mostra il numero vero di giocatori online, che si aggiorna quando qualcuno entra o esce (subito o entro pochi secondi, da fissare nel punto); il numero finto non compare mai; un test lo prova senza login.
- *Dipende da*: P44.

**P83 — Invito accettato e poi annullato: chi ha accettato resta ad aspettare** · piccolo · decisione: no — Giuseppe — **file non sicuri, vedi sezione 9.2**
- *Cosa e perché*: un giocatore invita un amico, l'amico accetta e vede "aspettiamo che … avvii la partita"; se chi ha invitato chiude la carta (annulla), l'amico resta ad aspettare. Deve vedere che l'invito è stato annullato ("… ha annullato l'invito.", P47) e tornare libero. Visto nel **2v2**, probabilmente succede anche nel **1v1**: prima si riproduce con un test in tutti e due i casi, poi si corregge.
- *Fatto quando*: nel 1v1 e nel 2v2 (anche con più amici invitati, P59), dopo l'annullamento chi aveva accettato vede l'invito annullato e può essere invitato di nuovo; i test lo provano dal tempo reale e nel browser.
- *Dipende da*: P47, P59.

**P84 — "Cala le carte": regola, motore e stanza** · medio · **decisione: sì** (regola nuova del 01/10/2026), dettagli decisi il 04/10/2026 (**D45**, `DECISIONI.md`, Gioco; regola in `docs/REGOLE-GIOCO.md`) — Giuseppe — **file non sicuri, vedi sezione 9.2**
- *Cosa e perché*: regola nuova. **A mazzo finito**, quando le carte in mano a un giocatore (nel 2v2 a una **squadra**, contando anche quelle del compagno) **vincono tutte le prese rimaste, in qualunque ordine si giochi e chiunque apra**, quel giocatore (o quella squadra) può **calare le carte**: le carte di tutti si scoprono e la sua squadra prende tutte le prese rimaste, con i loro punti. Non si può calare se un **avversario può ancora cantare** (con le regole del canto a mazzo finito). Il server conosce le carte di tutti, quindi il controllo lo fa lui; la pagina vede solo se l'azione è legale (`legal`), mai il perché. È un'azione nuova nel motore e nel contratto, che vale con l'ok di Giuseppe e Christian.
- *Fatto quando*: l'azione è legale esattamente quando valgono le condizioni sopra (una prova su molte situazioni la confronta con un calcolo che prova tutti gli ordini di gioco); calando, la mano finisce con le prese e i punti giusti; la mossa automatica non cala; regolamento (`docs/REGOLE-GIOCO.md`) e contratto lo dicono; la vista non mostra mai le carte altrui prima che si calino.
- *Dipende da*: P13, P15, P24; D45 (decisa il 04/10/2026).

**P85 — "Cala le carte": pulsante e carte calate al tavolo** · piccolo · decisione: sì (01/10/2026) — Christian — **file non sicuri, vedi sezione 9.2**
- *Cosa e perché*: quando il server dice che si può calare (P84), al tavolo compare il pulsante **"Cala le carte"**, solo al giocatore o alla squadra che può farlo. Premendolo, le carte di tutti si scoprono sul tavolo e vanno alla squadra che ha calato; poi il riepilogo di fine mano come sempre (P57). Senza connessione il pulsante è spento (P33).
- *Fatto quando*: il pulsante compare solo quando la vista lo permette e manda l'azione una volta sola (doppio clic); le carte calate si vedono prima del riepilogo; un'icona nuova, se serve, va in `icone.txt` (P62).
- *Dipende da*: **P84**.

**Seconda lista dello stesso giorno** (01/10/2026, sera): Christian ha aggiunto altre cinque richieste, diventate P86–P90 (P88 di Giuseppe, gli altri di Christian).

**P86 — Mazzo più grande, da computer** · piccolo · decisione: sì (01/10/2026) — Christian — **file non sicuri, vedi sezione 9.2**
- *Cosa e perché*: da computer il mazzo da cui si pesca è piccolo rispetto al tavolo: diventa più grande (misura proposta nel punto), con il seme della briscola sopra (P77). Sul telefono resta com'è (lo ha già ingrandito P71).
- *Fatto quando*: a 1280×720 e 1440×900 il mazzo è più grande e non tocca presa, ventagli e avatar; il tavolo non scorre; `test_grafica_tavolo.py` misura la misura nuova.
- *Dipende da*: P71; meglio insieme o subito dopo P74 e P77 (stessa zona del tavolo).

**P87 — "Esci" e punti più moderni e minimal** · piccolo · decisione: sì (01/10/2026; la grafica si sceglie nel punto) — Christian — **file non sicuri, vedi sezione 9.2**
- *Cosa e perché*: il pulsante **"Esci"** e i **punti** al tavolo hanno una grafica vecchia: vanno resi più moderni e minimal, su telefono e computer. "Punti" vuol dire il **tabellone** (dove resta, cioè da computer: P90) e i **punti della mano** di P72; all'inizio del punto Claude propone 2–3 stili, con una raccomandazione, e Christian sceglie. I colori nuovi vanno solo in `variables.css` (P40).
- *Fatto quando*: "Esci", tabellone e punti della mano hanno lo stile scelto, si leggono bene (contrasto) e hanno ancora l'etichetta per i lettori di schermo; i test del tavolo passano.
- *Dipende da*: P72; meglio dopo P74 e P90, che decidono dove stanno.

**P88 — Rating dei giocatori nella vista** · piccolo · decisione: sì (01/10/2026), contratto approvato da Giuseppe e Christian (02/10/2026: `rating` = `{"value", "provisional"}`) — Giuseppe
- *Cosa e perché*: per mostrare il rating dei giocatori al tavolo (P89) la vista deve averlo: oggi non c'è [L]. Ogni giocatore della vista ha il suo rating (il numero di Glicko-2 arrotondato, come nel pannello statistiche, P30; nome del campo e "provvisorio" sì o no da fissare nel punto), letto una volta sola quando si crea la stanza; vuoto per la CPU (P68). Il rating degli altri è un dato di gioco, non personale: è lo stesso numero che decide la coda.
- *File* — modifica: `app/realtime/room.py` o `room_manager.py` (dove si crea la stanza), `app/game/engine/views.py` (solo se il campo passa dal motore), `docs/CONTRATTO-SOCKET.md` (3.3), `app/static/dev/*.json`, test in `tests/sockets/` e `tests/engine/test_viste.py`. Certezza: **quasi sicuro**.
- *Fatto quando*: nella vista di ogni giocatore c'è il rating di tutti i giocatori umani, uguale a quello del pannello statistiche a inizio partita; gli esempi della vista sono aggiornati e i test che li confrontano passano.
- *Dipende da*: P24, P27, P30.

**P89 — Rating dei giocatori al tavolo, da computer** · piccolo · decisione: sì (01/10/2026) — Christian — **file non sicuri, vedi sezione 9.2**
- *Cosa e perché*: da computer, accanto al nome di **ogni giocatore** (tu, avversari, compagno) si vede il suo rating, così si riempie anche lo spazio vuoto. Sul telefono no (c'è poco spazio). Per la CPU niente rating.
- *Fatto quando*: a 1280×720 e 1440×900 ogni giocatore umano ha il suo rating accanto al nome, preso dal campo di P88; sul telefono non si vede; il tavolo non scorre.
- *Dipende da*: **P88**, P74 (posti nuovi degli avatar).

**P90 — Tavolo sul telefono: via il tabellone, "Esci" che non si sovrappone** · piccolo · **decisione: sì** (01/10/2026) — Christian — **file non sicuri, vedi sezione 9.2**
- *Cosa e perché*: sul telefono c'è troppo poco spazio. (1) Il **tabellone** in alto **si toglie**: il punteggio della partita si vede solo nel **riepilogo di fine mano**, che lo mostra già (riga "Punteggio" di `HandSummary.js`) [L]; restano i punti della mano in corso di P72. (2) Il pulsante **"Esci"** in partita oggi si **sovrappone** ad altre cose: prima si riproduce (360×640 e altre misure di `LEGGIMI.md`, 1v1 e 2v2), poi lo si mette dove non copre niente. Da computer il tabellone resta (P74).
- *Fatto quando*: sotto 1024 px il tabellone non c'è e "Esci" non si sovrappone a niente in 1v1 e 2v2 (un test del browser misura i rettangoli); il riepilogo di fine mano mostra ancora il punteggio; per i lettori di schermo il punteggio della partita resta raggiungibile (per esempio nel riepilogo).
- *Dipende da*: P71, P72.

**P91 — Suite `frontend` sotto il limite di tempo** · piccolo · decisione: no — Christian — **file non sicuri, vedi sezione 9.2** — *aggiunto il 02/10/2026 da Christian*
- *Cosa e perché*: la suite `frontend` dura da 187 a 222 s contro i 240 di `SUITE_TIMEOUT` (`tests/esegui_tutti.py`), e il 02/10/2026 due giri si sono fermati al limite (su `test_frasi_pagina.py` e `test_banner_connessione.py`, che da soli passano). Si spostano nella suite `api` i file lunghi del tavolo che non usano MySQL (per esempio `test_momenti_tavolo.py`, `test_lancio_carta.py`, `test_distribuzione.py`), misurando prima la durata di ciascuno, e si capisce perché a volte un test resta fermo fino al limite.
- *Fatto quando*: la suite `frontend` sta sotto i 170 s e la suite `api` sotto i 200 s, per 3 giri di fila.
- *Dipende da*: niente.

**Richiesta del 04/10/2026** (Christian): una regola del 2v2 con cui gioca Christian, diventata P92 (Giuseppe) e P93 (Christian). I dettagli sono decisi il 04/10/2026 (D46, `DECISIONI.md`, Gioco; regola in `docs/REGOLE-GIOCO.md`), con l'ok di Giuseppe.

**P92 — Carte del compagno scoperte a mazzo finito e consiglio: regola, vista ed evento** · medio · **decisione: sì** (D46, 04/10/2026) — Giuseppe — **file non sicuri, vedi sezione 9.2**
- *Cosa e perché*: regola nuova del 2v2. Da quando ci sono **insieme** la briscola fissata e il mazzo finito (in qualunque ordine), ogni giocatore vede le carte del **proprio compagno** fino a fine mano; senza briscola mai. (1) La vista di ogni giocatore ha le carte del compagno **solo** quando la regola lo permette (nome e forma del campo da fissare con Christian): è il punto delicato di P15, una chiave di troppo mostra carte che non si devono vedere; (2) un **evento nuovo per il consiglio**: il giocatore indica una carta del compagno (o toglie il consiglio); il server controlla che la regola sia attiva e che la carta sia davvero in mano al compagno, e lo manda **solo al compagno**; il consiglio sparisce quando il compagno gioca, non si salva, ha un limite di frequenza; (3) la mossa automatica lo ignora (D12); (4) contratto (il regolamento è già scritto: lo ha aggiornato Christian il 04/10, di turno sui documenti). Il contratto cambia: ok di Giuseppe e Christian.
- *Fatto quando*: in ogni momento di molte partite 2v2 le carte del compagno sono nella vista esattamente quando briscola e mazzo finito ci sono insieme, e mai quelle degli avversari; nel 1v1 il campo non c'è mai; un consiglio arriva solo al compagno, uno non valido (regola non attiva, carta che il compagno non ha, 1v1) si rifiuta con un messaggio chiaro; `docs/REGOLE-GIOCO.md`, contratto ed esempi della vista sono aggiornati.
- *Dipende da*: P15, P24, P55 (stessa forma delle frasi: niente salvataggio, limite di frequenza); D46 (decisa il 04/10/2026); meglio dopo P84 (stessi file del motore e della vista).

**P93 — Carte del compagno scoperte e consiglio al tavolo** · medio · **decisione: sì** (D46, 04/10/2026) — Christian — **file non sicuri, vedi sezione 9.2**
- *Cosa e perché*: quando la vista ha le carte del compagno (P92), il suo ventaglio in alto **si gira da solo** con un'animazione e mostra le facce, un po' più grande di quello coperto; per 2–3 s la scritta "Mazzo finito: ora vedi le carte di <nome>" (con "riduci movimento" solo la scritta). Un clic (o un tocco) su una carta del compagno manda il consiglio; un altro clic lo sposta, un clic sulla stessa carta lo toglie. Chi lo riceve vede nella sua mano la carta con un bordo e l'etichetta "consiglio di <nome>". Senza connessione il clic non manda niente (P33).
- *Fatto quando*: su telefono (360 px) e computer il ventaglio scoperto si legge e non copre presa, mazzo e avversari; il tavolo non scorre; il consiglio si vede solo nella mano del compagno e sparisce quando gioca; il segno non si affida solo al colore (accessibilità); le carte del compagno hanno un'etichetta per i lettori di schermo; i test del browser lo provano con gli esempi della vista; un test lungo nuovo del tavolo va nella suite `table` (P91).
- *Dipende da*: **P92**, P70 (animazioni), P74 (tavolo da computer); D46 (decisa il 04/10/2026).

### Correzioni e richieste dalla prova del 04/10/2026

Il 04/10/2026 Christian ha provato la grafica nuova del tavolo dal telefono e dal computer (P74, P76–P78, P80, P86, P87, P89, P90) e ha scritto le cose da sistemare. Sono diventate i punti P94–P103: due di Giuseppe (P94, P96), gli altri di Christian. I dettagli li ha chiariti Christian con Claude prima di scriverli; le decisioni sono in `DECISIONI.md` (04/10/2026).

**P94 — Turno da 15 secondi, che parte dopo le pause del tavolo** · piccolo · **decisione: sì** (04/10/2026, sostituisce i 30 s del 26/09) — Giuseppe — **file non sicuri, vedi sezione 9.2**
- *Cosa e perché*: il turno passa da **30 a 15 secondi**. Perché siano tutti giocabili, il conto alla rovescia parte solo **dopo le pause del tavolo**: dopo una presa (ultima presa e pescata) e a fine mano (ultima presa, riepilogo, mescolata, distribuzione, carte calate di P85). Oggi chi apre la mano dopo parte con circa 20 s su 30 (riepilogo di P84) [L]: con 15 s gliene resterebbero circa 5. Le durate delle pause stanno in `game.js` (Christian): il server deve usare gli stessi numeri, e un test li confronta (come `PHRASE_PAUSE_MS`, P56). I 60 s per rientrare e la mossa automatica (D12) non cambiano. Anche le attese della CPU (`CPU_NEW_HAND_SECONDS`) vanno riviste con questi tempi.
- *Fatto quando*: in partita ogni turno ha 15 s giocabili, anche il primo di una mano e quello dopo una presa (un test misura da quando parte il timer); `turn.seconds_total` è 15; contratto ed esempi della vista aggiornati se cambia qualcosa. Il regolamento è già aggiornato (04/10, Christian di turno).
- *Dipende da*: P25, P66; meglio dopo P85 (durata delle carte calate).

**P95 — Partita interrotta dal riavvio del server** · piccolo · **decisione: sì** (04/10/2026) — Christian — **file non sicuri, vedi sezione 9.2**
- *Cosa e perché*: se il server si spegne e si riaccende durante una partita, al tavolo non si può più né giocare né uscire. Le partite stanno solo in memoria e dopo il riavvio non esistono più. Causa probabile [L]: il server risponde già `not_found` a `game:join`, ma `game.js` (`join`), se il tavolo era già disegnato, mostra solo il messaggio nella riga di stato e lascia il tavolo com'è. Prima si riproduce, poi: con `not_found` la pagina mostra un avviso ("La partita è stata interrotta", testo esatto da fissare nel punto) e torna alla **home**. La partita non si salva e non conta per il rating. Se la causa è anche nel server, Giuseppe va avvisato.
- *Fatto quando*: un test con la partita sparita dal server (server riavviato, o stanza tolta) vede l'avviso e il ritorno alla home; nessun pulsante del tavolo resta attivo.
- *Dipende da*: P24, P33.

**P96 — Login con nome utente o email** · piccolo · **decisione: sì** (04/10/2026) — Giuseppe — **file non sicuri, vedi sezione 9.2**
- *Cosa e perché*: oggi si accede solo con lo username [L] (`LoginForm`, `auth_service.authenticate`). La pagina di accesso ha **un campo solo**, "Nome utente o email", e la password: se il testo contiene `@` è un'email (gli username non possono contenere `@`, D7), altrimenti uno username. Il messaggio d'errore resta sempre lo stesso e non dice se l'account esiste. Il limite dei tentativi (P16) deve valere per l'**account**, non per il testo scritto, altrimenti si aggira scrivendo una volta lo username e una volta l'email.
- *Fatto quando*: si entra con lo username o con l'email (maiuscole dell'email come le tratta il database, da verificare nel punto); un account bloccato dai tentativi resta bloccato con tutte e due le scritture; i test di P16 e P32 passano.
- *Dipende da*: P16, P32.

**P97 — Le carte della propria mano "lampeggiano"** · piccolo · decisione: no — Christian — **file non sicuri, vedi sezione 9.2**
- *Cosa e perché*: soprattutto dal telefono, le carte della **tua mano** a volte si alzano e si abbassano subito, come un'animazione brevissima (non sono bianche: è un'altra cosa rispetto a P79). Quando succede va capito nel punto. Ipotesi [D]: un'animazione o una transizione che riparte a ogni ridisegno del tavolo (P70: il tavolo si ridisegna tutto a ogni vista). Prima si riproduce (anche a 360 px), poi si corregge.
- *Fatto quando*: un test del browser, con "riduci movimento" spento, non vede mai la mano muoversi senza una mossa del giocatore; le animazioni volute (P70, P78) restano.
- *Dipende da*: P70, P78.

**P98 — Zoom con il doppio tocco al tavolo su iPhone** · piccolo · decisione: no — Christian — **file non sicuri, vedi sezione 9.2**
- *Cosa e perché*: su **iPhone con Safari** si può ancora ingrandire la pagina con il doppio tocco mentre si gioca. Le regole contro lo zoom di P69 (`:root:has(.page--game)`) non bastano per Safari, che ignora alcune di queste regole: serve una soluzione che funzioni lì, senza cambiare niente su Android e da computer.
- *Fatto quando*: una prova a mano su un iPhone vero non riesce a ingrandire il tavolo con il doppio tocco (Chrome dei test non può simulare Safari); i test di P69 passano.
- *Dipende da*: P69.

**P99 — Lancio della propria carta più realistico** · piccolo · **decisione: sì** (04/10/2026; l'animazione si sceglie nel punto) — Christian — **file non sicuri, vedi sezione 9.2**
- *Cosa e perché*: il lancio della **tua** carta è ancora troppo finto e veloce. All'inizio del punto Claude propone 2–3 animazioni (durata, traiettoria, rotazione, ombra), con una raccomandazione, e Christian sceglie. Con "riduci movimento" resta corto o assente; con il turno da 15 s (P94) non deve rallentare il gioco.
- *Fatto quando*: il lancio ha l'animazione scelta; le durate in `game.js` restano uguali a quelle dei CSS (test di P70); i lanci in fila (P78) funzionano ancora.
- *Dipende da*: P70, P78.

**P100 — Mazzo del 1v1: posizione da computer e misura sul telefono** · piccolo · **decisione: sì** (04/10/2026) — Christian — **file non sicuri, vedi sezione 9.2**
- *Cosa e perché*: nel **1v1**: (1) da computer il mazzo va **un po' più a destra**, con il centro quasi sulla stessa verticale della pillola "Frasi"; (2) sul telefono il mazzo è **un po' più grande** (oggi 56 px, P86). Nel 2v2 non cambia niente.
- *Fatto quando*: a 1280×720 e 1440×900 nel 1v1 il centro del mazzo è vicino a quello della pillola "Frasi" e non tocca presa, ventagli e avatar; a 360 px il mazzo del 1v1 è più grande e il tavolo non scorre; `test_grafica_tavolo.py` misura le posizioni nuove.
- *Dipende da*: P74, P86; meglio insieme a P102 (stessa zona del mazzo).

**P101 — Frasi del tavolo sul telefono aperte sopra le proprie carte** · piccolo · **decisione: sì** (04/10/2026) — Christian — **file non sicuri, vedi sezione 9.2**
- *Cosa e perché*: sul telefono l'elenco delle **frasi pronte** ("Frasi"), quando è aperto, copre tutto il tavolo. Deve coprire **solo la zona delle tue carte**, in basso, così presa, mazzo e avversari restano visibili. Da computer resta il pannello di lato (P80).
- *Fatto quando*: a 360×640 e 390×844, con l'elenco aperto, presa, mazzo e avversari si vedono; le frasi si scelgono come prima; i test delle frasi (`test_frasi_pagina.py`, `test_frasi_di_lato.py`) passano.
- *Dipende da*: P56, P80.

**P102 — Indicatore della briscola** · piccolo · **decisione: sì** (04/10/2026; cambia P77 a mazzo finito) — Christian — **file non sicuri, vedi sezione 9.2**
- *Cosa e perché*: la briscola deve vedersi bene. Oltre che sopra il mazzo, compare in un **tondo** in vetro scuro (lo stile di "Esci", P87) con il seme dentro: **sul telefono** nell'angolo **in alto a destra**, simmetrico al tondo di "Esci" (P90), un po' più grande di "Esci" (oggi 44 px); **da computer** a **sinistra del tabellone**, rotondo e un po' più grande di "Esci". Compare **solo quando c'è la briscola** (prima del 40 non c'è niente). **A mazzo finito** il seme sopra il mazzo sparisce (cambia P77) e resta solo il tondo; al posto del mazzo resta **uno spazio vuoto** della stessa misura, così il tavolo non si sposta. Per i lettori di schermo il tondo dice la briscola (per esempio "Briscola: coppe").
- *Fatto quando*: a 360 px e da computer il tondo si vede appena c'è la briscola e non tocca "Esci", tabellone, ventagli e punti dell'avversario (a 1024×768 nel 1v1 lo spazio in alto è già stretto: punto delicato di P74); a mazzo finito il seme sul mazzo non c'è più e la presa non si sposta; i test di P77 sono aggiornati.
- *Dipende da*: P77, P87, P90; meglio insieme a P100.

**P103 — Suoni al tavolo** · medio · **decisione: sì** (04/10/2026) — Christian — **file non sicuri, vedi sezione 9.2**
- *Cosa e perché*: suoni per quello che succede in partita: **mescolata**, **lancio** di una carta, **pescata**, **presa** (carte raccolte), **canto** (40 o 20) e **calata**, **tocca a te**, **tempo che scade** (ticchettio negli ultimi 5 s del tuo turno), **fine mano** e **fine partita** (uno per vittoria, sconfitta, pareggio). Si spengono con un **interruttore nella pagina delle impostazioni**; la scelta si ricorda **nel browser** (niente database); all'inizio sono **accesi**. I file audio sono locali, piccoli e con una licenza che ne permetta l'uso (scritta accanto ai file, come per le carte: P35). Un'animazione e il suo suono partono insieme (stessi momenti di `game.js`).
- *Fatto quando*: ogni momento dell'elenco ha il suo suono; con l'interruttore spento non suona niente, anche dopo aver ricaricato la pagina; la pagina funziona anche se il browser blocca l'audio; `test_csp.py` non segnala niente; il peso dei file audio è misurato e scritto nel punto.
- *Dipende da*: P17 (pagina delle impostazioni), P70, P78; meglio dopo P85 e P99 (momenti nuovi del tavolo).

### Correzioni e richieste del 05/10/2026

Il 05/10/2026, durante e dopo i punti della prova del 04/10, Christian ha provato il tavolo dal telefono (anche iPhone) e dal computer e ha scritto altre cose da sistemare (`cose-da-sistemare.txt`, fuori dal repository). Sono diventate i punti P104–P113, tutti di Christian (P111 tocca file di Giuseppe, con il suo ok). P104–P112 sono stati fatti lo stesso giorno da Claude, con il permesso di Christian per commit, merge e push: le note sono nel tracker e nei riepiloghi di `christian.md`; le decisioni in `DECISIONI.md` (05/10/2026).

**P104 — Zoom con il doppio tocco su iPhone, in JavaScript** · piccolo · **fatto il 05/10/2026** — Christian
- *Cosa e perché*: dopo P98, su iPhone con Safari il doppio tocco ingrandiva ancora il tavolo. La pagina blocca lo zoom quando un tocco arriva entro 0,3 s dal precedente e manda da sé il clic, così non si perde nessun tocco.
- *Fatto quando*: su un iPhone vero il doppio tocco non ingrandisce e due tocchi veloci su due carte o su "Frasi" funzionano (provato da Christian il 05/10).

**P105 — Coda: l'intervallo di rating cambia senza lampo** · piccolo · **fatto il 05/10/2026** — Christian
- *Cosa e perché*: quando l'intervallo si allargava la schermata della coda si richiudeva e riapriva (un lampo). Restano aperta e i numeri scorrono.
- *Fatto quando*: un test vede la stessa schermata aperta e i numeri passare per valori intermedi.

**P106 — La mano non cambia misura quando restano meno carte** · piccolo · **fatto il 05/10/2026** — Christian
- *Cosa e perché*: sul telefono, da 5 a 4 carte, le carte si ingrandivano e tutto il tavolo saliva. Ogni carta resta larga come in una mano piena.
- *Fatto quando*: con 4, 3 e 1 carta mano, presa, mazzo e giocatori non si spostano (test a 4 misure).

**P107 — Lancio della carta degli avversari più realistico** · piccolo · **fatto il 05/10/2026** — Christian
- *Cosa e perché*: la carta di un avversario arrivava dal suo lato senza un movimento credibile. Parte dal suo ventaglio e fa lo stesso volo della tua (P99), in 0,4 s.
- *Fatto quando*: un test vede la carta partire dal centro del ventaglio con la sua misura e finire al suo posto, nel 1v1 e nel 2v2.

**P108 — Briscola solo nell'angolo, con Cavallo e Re** · piccolo · **fatto il 05/10/2026** (cambia P102) — Christian
- *Cosa e perché*: la briscola si vede con le due carte che si cantano (Cavallo e Re del seme), come nel logo, nell'angolo in alto a destra; niente più seme sul mazzo.
- *Fatto quando*: le due carte del seme giusto, alte come "Esci" sul telefono e 56 px da computer, non toccano niente (test a 4 misure).

**P109 — Suoni registrati dal vero, e un suono per le frasi** · medio · **fatto il 05/10/2026**, da approvare dai tre (D47, P113) — Christian
- *Cosa e perché*: i suoni sintetizzati di P103 erano poco realistici. Al loro posto file MP3 registrati (Kenney, CC0); anche le frasi del tavolo hanno un suono. Dopo la prova di Christian: tolto il "ding" di "tocca a te" e cambiato il suono della presa, che aveva molto rumore di fondo.
- *Fatto quando*: ogni momento ha il suo file, con la licenza scritta; nessun contesto audio prima di un gesto; `tests/table/test_suoni.py` passa.

**P110 — L'elenco delle frasi non lampeggia durante i lanci** · piccolo · **fatto il 05/10/2026** — Christian
- *Cosa e perché*: con l'elenco aperto, quando un avversario lanciava una carta l'elenco lampeggiava (la sua entrata ripartiva a ogni ridisegno).
- *Fatto quando*: un test con l'elenco aperto durante un lancio non vede nessuna entrata ripartire e l'opacità resta piena; l'elenco fatto scorrere resta dov'era.

**P111 — Matchmaking più veloce** · piccolo · **fatto il 05/10/2026** (cambia i numeri di D16) — Christian, con l'ok di Giuseppe
- *Cosa e perché*: la Partita Veloce ci metteva circa 20 s a trovare un avversario, perché l'intervallo di rating di tutti e due cresceva lentamente. Opzione A, scelta da Christian e Giuseppe: ±150, +100 ogni 5 s fino a ±400, chiunque dopo 30 s.
- *Fatto quando*: i test della coda passano con i numeri nuovi; `matchmaking.py` non cambia.

**P112 — Sul telefono l'elenco delle frasi si apre al suo posto** · piccolo · **fatto il 05/10/2026** — Christian
- *Cosa e perché*: su iPhone l'elenco compariva più in alto, sopra il tuo nome e il pulsante "Frasi", e poi scendeva. Correzione difensiva (la causa non si è riprodotta): la posizione la misura la pagina e l'entrata è solo una dissolvenza.
- *Fatto quando*: un test vede l'elenco, dal primo fotogramma, sempre alla stessa altezza subito sotto la tua riga; provato da Christian su iPhone.

**P113 — Pagina per ascoltare e confrontare i suoni** · piccolo · **decisione: sì** (05/10/2026; i suoni da scegliere sono D47) — Christian — **file non sicuri, vedi sezione 9.2**
- *Cosa e perché*: il 06/10 Christian, Giuseppe e Antonio (se c'è) vogliono **sentire suoni diversi** da quelli di P109 e scegliere quelli che piacciono di più. Serve una **pagina a parte** dove, per ogni momento del tavolo (carta che si posa, pescata, mescolata, distribuzione, presa raccolta, calata, canto, frase, ticchettio, vittoria, sconfitta, pareggio), si ascoltano il suono di oggi e 3–4 alternative, con un pulsante "ascolta" per ciascuna. I candidati vengono da pacchetti con una licenza che ne permette l'uso (per esempio i pacchetti Kenney, CC0), convertiti come in `app/static/sounds/LICENZA.md`. All'inizio del punto si decide con Christian **dove sta la pagina**: nel sito solo in sviluppo (come le prove `?demo=`), oppure un file HTML fuori dal repository da aprire nel browser; in tutti e due i casi non va in `main`. Dopo la scelta dei tre, i file scelti prendono il posto di quelli di oggi.
- *Fatto quando*: i tre hanno ascoltato e scelto (D47 chiusa); i file scelti sono in `app/static/sounds/` con `LICENZA.md` aggiornato e i file non usati tolti; `tests/table/test_suoni.py` passa; il peso dei suoni resta sotto i 250 kB.
- *Dipende da*: P109.

**P114 — Suite `table` sotto il limite di tempo** · piccolo · decisione: no — Christian
- *Cosa e perché*: il 05/10, dopo P112, la suite `table` dura **294 s** (131 PASS) e il runner la ferma a 240 s (`SUITE_TIMEOUT`): non è un test bloccato, è cresciuta con i test del 04–05/10 (calata, carte del compagno, suoni, lanci, mano ferma, frasi, partita interrotta). Proposta di Claude, come P91: dividerla in due, con una suite nuova (per esempio `tests/table2/`) che il runner trova da solo, circa 150 s ciascuna. Scartato per ora, salvo decisione diversa: alzare `SUITE_TIMEOUT` (il runner è di tutti, serve l'ok di Giuseppe). Scelta di Christian del 05/10: solo annotarlo, si fa un altro giorno.
- *Fatto quando*: nel giro completo nessuna suite supera i 240 s, con margine (sotto i 200 s); `tests/esegui_tutti.py` non cambia.
- *Dipende da*: P91.

**~~P60 — Togliere le viste finte dalla versione consegnata~~** · **tolto il 29/09/2026** (vedi il tracker) · aggiunto il 28/09/2026 (proposta di Christian in P57)
- *Cosa e perché*: le prove nell'indirizzo (`?demo=1v1`, `?demo=2v2` del tavolo, `?demo=rientro` della home) e gli eventi `demo:` del browser non devono restare nella versione consegnata: si tolgono o si spostano in una pagina solo di sviluppo, e si adattano le suite che le usano.
- *Fatto quando*: nella demo vera nessun indirizzo con `?demo=` mostra dati finti; le suite passano.
- *Dipende da*: P21, P22, P56, P57 (le pagine con le prove); va fatto prima di P36.

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
- *Da quale branch* (deciso il 29/09/2026, D20): la demo si installa da **`main`**, il branch di produzione, aggiornato con i soli file che servono al sito (regola in `CLAUDE.md`, "Regole git").
- *Fatto quando*: nella cartella demo il runner si rifiuta di partire [T]; il backup pianificato produce un file; un ripristino di prova su `cinquecento_test` funziona.
- *Dipende da*: P18, P37.

**P39 — Accesso dagli altri dispositivi e prova generale** · piccolo · decisione: **D20**
- *Cosa e perché*: avviare il server in ascolto sulla rete locale (con `HOST` nel `.env` della demo, già previsto in P4), aprire la porta nel firewall di Windows (solo per le reti private), completare la lista di controllo del giorno della demo. **Deciso il 29/09/2026 (D20)**: la demo gira sul **PC di Giuseppe**; per il collegamento si prova un **tunnel ngrok** con un **QR code** da inquadrare con il telefono, così possono provare anche i colleghi; se ngrok si rivela troppo complesso o lento da preparare, si usa la stessa rete Wi-Fi.
- *File* — modifica: `docs/DEMO.md` (P38). Certezza: **sicuro** per il repository. Firewall e `.env` della demo sono fuori dal repository.
- *Fatto quando*: tre telefoni sulla stessa rete Wi-Fi e un PC diventano amici, si invitano e giocano una partita 2v2 completa; la lista di controllo è stata seguita almeno una volta dall'inizio alla fine.
- *Dipende da*: P38.

## 5. Calendario indicativo (3 persone)

Segue la divisione della sezione 9. **Attenzione**: con amici, chat e prototipo i punti sono passati da 39 a 52; il 27/09/2026 ne sono stati tolti 4 (P41, P49, P50, P51) e aggiunti 2 (P55, P56: frasi del tavolo; P54 è stato aggiunto e tolto lo stesso giorno), quindi ne restano 50. Una settimana resta **stretta** (vedi rischi e ordine di taglio).

| Giorno | Giuseppe: motore e tempo reale | Antonio: account, dati, amici, pagine dati | Christian: interfaccia e documenti |
|---|---|---|---|
| 1 — 27/09 | fatti: P1, P2, P4 | — (tabelle approvate: D38) | fatti: P52, P3 |
| 2 — 28/09 | P10, P11, P12, P6 (appena P5 è in `dev`) | **P5**, P7 (dopo P6 e P19), P18 | **P8** (il contratto si approva insieme), P19, P40 |
| 3 — 29/09 | P13, P14, P15 | P16, P17 (dopo P40) | P20, P22, P9 |
| 4 — 30/09 | P23 | P45, P26 (service, repository e test), P27 | P21, P46 |
| 5 — 01/10 | P24, P25 | P28 (dopo P24), chiamata di P26 in `room.py` (dopo P25) | P30 |
| 6 — 02/10 | P44 (dopo P29), P47, P55 | P29, P48 | P56 (dopo P55), P33, P34, P35 |
| 7 — 03/10 | P31, P32 | P38, P39 | P42, P43, P53 (se c'è tempo), P36, P37 |

I giorni sono indicativi (aggiornati il 28/09/2026: P5 e P8, previsti il 27/09, passano al 28/09, e la settimana resta la stessa). La regola che conta è quella delle dipendenze: un punto inizia solo quando i punti da cui dipende sono già in `dev`.

**Se il tempo stringe**, ordine di taglio proposto (da confermare, D31): ~~P53~~ (tolto il 30/09/2026: resta solo il tema chiaro) → P56 e P55 (niente frasi al tavolo) → P43 e P42 (restano iniziali e nome testuale) → P35 (restano le carte CSS) → P48 (chat) → P29 (niente 2v2: senza la coda 2v2 non si può giocare nemmeno in coppia con un amico) → P34. **Non si tagliano mai** P6, P15, P24, P31 e P32.

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
| `partials/navbar.html`, `navbar.css`, `stats-panel.css`, `core/layout.js`, `StatsPanel.js`, `LoginPrompt.js`, `img/cards-bg/*`, `pages/home.js` (poi P22) | P40 |
| `Card.js`, `Hand.js`, `card.css`, `hand.css`, `static/dev/carte.*` | P20 |
| `game/table.html`, `pages/game.js`, `Table/Trick/Scoreboard/Timer/SingButtons.js` e relativi CSS | P21 |
| `HandSummary.js`, `hand-summary.css`, `tests/frontend/test_momenti_tavolo.py` | P57 |
| `pages/home.css`, `ModeModal.js`, `mode-modal.css`, `CardBackground.js`, `card-background.css`, `QueueOverlay.js`, `queue-overlay.css`, `ResumeBanner.js` | P22 |
| `friend_service.py`, `friend_repo.py` | P45 |
| `FriendsPanel.js`, `ChatWindow.js`, `friends-panel.css`, `chat.css` | P46 |
| `app/realtime/events.py`, `room.py`, `room_manager.py`, `js/core/socket.js`, `js/core/events.js`, `js/vendor/*` | P23 |
| `match_service.py`, `match_repo.py` | P26 |
| `glicko2.py`, `rating_service.py`, `rating_repo.py` | P27 |
| `app/realtime/matchmaking.py` | P28 |
| `app/realtime/presence.py`, `app/sockets/home_events.py` | P44 |
| `app/realtime/invites.py` | P47 |
| `chat_service.py`, `chat_repo.py` | P48 |
| `app/realtime/table_phrases.py` | P55 |
| `TablePhrases.js`, `table-phrases.css` | P56 |
| `stats_service.py`, `stats_repo.py` | P30 |
| `tests/e2e/*` | P31 |
| `Banner.js`, `banner.css` | P33 |
| `app/static/img/cards/*` | P35 |
| `app/static/img/logo.*` | P42 |
| `app/static/img/avatars/*` | P43 |
| `app/static/fonts/*` | P62 |
| `REVIEW.md` | P36 |
| `docs/archivio/*` | P37 |
| `docs/DEMO.md` | P38 |

## 7. Rischi e come la scaletta li affronta

| Rischio | Come lo affrontiamo |
|---|---|
| **Tempo**: 50 punti in una settimana per tre persone sono molti, e amici e chat sono il blocco più grosso aggiunto | Filoni paralleli grazie al contratto P8 e ai dati finti (P21, P22, P46); tolti classifica, stanza privata, storico e regole (27/09); ordine di taglio proposto (D31); punti piccoli |
| **Conflitti git tra i tre** | Ogni punto elenca i suoi file; P4 prepara i segnaposto; file condivisi in sequenza (sezione 3 e colonna "Attende" della sezione 9); documenti condivisi aggiornati da una persona sola, scelta dal gruppo a fine giornata |
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
| Chat di gruppo e chat a testo libero durante la partita | La chat a testo libero è solo tra due amici; al tavolo ci sono solo le frasi pronte (D24, D25; P55, P56) |
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

Chi fa cosa (D3, deciso il 27/09/2026): **Studente 1 = Giuseppe**, **Studente 2 = Antonio**, **Studente 3 = Christian**. Nel resto della scaletta si usano i nomi.

### 9.1 Punti con file sicuri

Qui ci sono solo i punti di cui conosco **con certezza** tutti i file. Sono divisi in modo che:
- i punti che toccano **gli stessi file nello stesso periodo** vadano allo **stesso studente**;
- quando due studenti toccano lo stesso file, lo fanno **uno dopo l'altro**: nella colonna "Attende" c'è il punto che deve essere **già in `dev`** prima di iniziare. Rispettando quella colonna non nascono conflitti.

Due studenti che lavorano in parallelo non toccano mai gli stessi file. Vale anche per i documenti condivisi (`SCALETTA.md`, riga Stato di `CLAUDE.md`, `DECISIONI.md`, `DA-DECIDERE.md`): li aggiorna solo chi il gruppo sceglie a fine giornata, su un branch `docs/…` (28/09/2026, sostituisce D22).

**Giuseppe (Studente 1) — motore di gioco e tempo reale:** P1, P2, P4, P6, P10, P11, P12, P13, P14, P15, P23, P24, P44, P47, P55, P58, P59, P31, P63, P67, P75, P88 (più P32, P61, P64, P65, P66, P68, P82, P83, P84, P92, P94 e P96 in 9.2); dal 28/09/2026 anche i punti di Antonio ancora aperti: P38 (in 9.2) e P39. Al posto di Antonio, con il suo permesso, ha già fatto P16, P28, P29, P48 e metà di P38

**Antonio (Studente 2) — account, dati, amici:** P5, P7, P17, P18, P45, P26, P27, più P25 al posto di Giuseppe. **Dal 28/09/2026 non può lavorare al progetto per un bel po'** (detto da Christian, riepilogo di P30): i suoi punti aperti sono passati a Giuseppe (P16, P28, P29 e P48 li aveva già fatti lui; P38 e P39 riassegnati il 28/09/2026)

**Christian (Studente 3) — interfaccia e documenti:** P3, P52, P8, P9, P19, P40, P20, P21, P22, P46, P56, P57, P30, P62, P81, P36, P37 (più P33, P34, P35, P42, P43, P69, P70, P71, P72, P73, P74, P76, P77, P78, P79, P80, P85, P86, P87, P89, P90, P93, P95 e P97–P113 in 9.2; P111 con file di Giuseppe, con il suo ok; P60 tolto il 29/09/2026, P53 il 30/09/2026)

**Da dove si parte** (aggiornato il 05/10/2026 da Christian, di turno sui documenti: registrati **P68** rifatto, **P92**, **P94** e **P96** di Giuseppe e **P85**, **P93**, **P95**, **P97–P103** di Christian, del 04–05/10; aggiunti e fatti il 05/10 **P104–P112**, aggiunto **P113**; in `dev` ci sono P1–P8, P10–P35, P40, P42–P48, P52, P55–P59, P61–P72, P74–P81, P83–P112, P62; metà di P38; P53 e P60 tolti; P9 fatto in parte e annullato il 03/10 su richiesta di Christian; giro completo **1758 PASS** in 9 suite, nessun test fallito, ma la suite **`table` supera il limite**: il runner la ferma a 240 s (le altre otto 1627 PASS), e lanciata da sola fa 131 PASS in 294 s (05/10, dopo P112; da sistemare con **P114**)) [L]:
- **Giuseppe**: (0) resta il difetto **P82** (online senza login); (1) il 06/10, con Christian, la scelta dei suoni (**D47**, con la pagina di P113); (2) **P38** (installazione sul PC della demo, da `main`) e **P39** (con ngrok e QR code, D20), prima della consegna; (3) `js/pages/auth.js` se il gruppo lo conferma (sotto). Da sapere: in P111 Christian ha cambiato con il tuo ok i numeri della coda in `config.py` e i test della coda (`test_matchmaking_1v1.py`, `test_matchmaking_2v2.py`): fai il pull prima di toccarli.
- **Antonio**: nessun punto aperto.
- **Christian**: (0) **P113** (pagina per ascoltare i suoni, per la scelta dei tre del 06/10, D47), poi i suoni scelti al posto di quelli di oggi; (0b) **P114** (suite `table` oltre i 240 s: dividerla); (1) **P73** (CPU nella home: P68 rifatto è in `dev` dal 04/10, contratto approvato); (2) **P9** (guida di installazione verificata nel `README.md`), quando lo decide; (3) la review **P36**, poi P37; (4) a fine progetto la **relazione** (D1) e l'aggiornamento di `main` con i soli file del sito. Con P32 vale la **CSP**: niente script, stili o `onclick=` scritti nell'HTML, e ogni risorsa esterna nuova va anche in `CSP_DIRECTIVES` di `app/__init__.py`. Un'icona nuova va in `app/static/fonts/icone.txt` e il font va riscaricato (P62). Un test lungo nuovo del tavolo nel browser va nella suite **`table`** (`tests/table/`); quella che si avvicina al limite di 240 s va divisa di nuovo.
- **Da concordare**: le pagine di accesso e registrazione (P16) non hanno ancora uno script di pagina, quindi lì la navbar non si apre. Serve un `js/pages/auth.js` che importa `core/layout.js` e chiama `initLayout()`: non è nell'elenco di nessun punto; proposta: lo aggiunge Giuseppe con la grafica delle due pagine.

| Punto | Chi | File condivisi con punti di altri studenti | Attende (già in `dev`) |
|---|---|---|---|
| P1, P2 | Giuseppe | nessuno | — |
| P3 | Christian | `CLAUDE.md` (poi P37, sempre Christian) | — |
| P4 | Giuseppe | crea i segnaposto che altri riempiranno | P1, P2 |
| P5 | Antonio | nessuno | P4 (solo per `migrate.py` e i modelli) |
| P6 | Giuseppe | nessuno | P4, P5 |
| P7 | Antonio | `logging_config.py`, `errors.py` (segnaposto di P4); crea `templates/errors/*` basati su `base.html` (P19) | P4, P6, P19 |
| P8 | Christian | nessuno | — |
| P9 | Christian | `README.md` (poi P37, sempre Christian) | P4, P5, P6 |
| P52 | Christian | nessuno (crea solo `docs/prototipo/*`) | P1 |
| P10–P15 | Giuseppe | nessuno (tutto in `app/game/engine/`) | P4; P15 attende anche P8 |
| P16 | Antonio | `blueprints/auth/*` (segnaposto di P4) | P5, P7, P19 |
| P17 | Antonio | `blueprints/profile/routes.py` (segnaposto di P4); crea `profile/settings.html` che poi modifica P43 | P16, P40 |
| P18 | Antonio | nessuno | P5, P6 |
| P19 | Christian | `templates/main/index.html` (P4) | P4, P52 |
| P40 | Christian | nessuno di altri studenti (`base.html` è di Christian) | P19 |
| P20 | Christian | nessuno | P19 |
| P21 | Christian | `blueprints/game/routes.py` (P4); crea `pages/game.js` che poi modifica P24 | P8, P20, P40 |
| P22 | Christian | `blueprints/main/routes.py` (P4); modifica `pages/home.js` (creato da P40; poi P28, P29, P44), crea `ModeModal.js` (poi P28, P47) | P8, P40, P52 |
| P45 | Antonio | `blueprints/friends/*` (segnaposto di P4) | P5, P16 |
| P46 | Christian | crea `FriendsPanel.js` (poi P47) e `ChatWindow.js` (poi P48) | P8, P40 |
| P23 | Giuseppe | `sockets/__init__.py`, `connection_events.py` (P4) | P8, P16 |
| P24 | Giuseppe | `pages/game.js` (P21), `game_events.py` (P4) | P15, P21, P23 |
| P25 | Giuseppe | nessuno di altri studenti in parallelo | P24 |
| P26 | Antonio | `realtime/room.py` (solo la chiamata al salvataggio) | P5; **P25** per la modifica a `room.py` |
| P27 | Antonio | nessuno | P26 (service e repository) |
| P28 | Giuseppe (per Antonio) | `lobby_events.py`, `sockets/__init__.py` (dopo Giuseppe), `pages/home.js` e `ModeModal.js` (dopo Christian) | P22, P24, P27 |
| P29 | Giuseppe (per Antonio) | nessuno di altri studenti in parallelo | P28 |
| P44 | Giuseppe | `sockets/__init__.py` e `pages/home.js` (dopo Antonio) | P25, P29 |
| P47 | Giuseppe | `FriendsPanel.js` (dopo Christian), `ModeModal.js` (dopo Antonio), `friends_events.py` (P4) | P24, P29, P44, P45, P46 |
| P48 | Giuseppe (per Antonio) | `ChatWindow.js` (dopo Christian), `chat_events.py` (P4) | P23, P45, P46 |
| P30 | Christian | `blueprints/stats/routes.py` (segnaposto di P4), `StatsPanel.js` (P40, sempre Christian) | P26, P27, P40 |
| P55 | Giuseppe | `config.py` (P4: una chiave nuova, concordata nel punto); `game_events.py` è di Giuseppe | P8, P25 |
| P56 | Christian | `pages/game.js` (dopo Giuseppe, P25) | P55 |
| P57 | Christian | `pages/game.js` (dopo Giuseppe, P25); `Table.js`, `Trick.js` sono suoi (P21) | P24, P25 |
| P58 | Giuseppe | nessuno (motore, vista, contratto 3.3 ed esempi; `game.js` lo adatta poi Christian) | P15 |
| P59 | Giuseppe | vedi 9.2 (forse `ModeModal.js` di Christian) | P29, P47 |
| P31 | Giuseppe | nessuno (crea solo `tests/e2e/*`) | P25, P29, P47, P48 |
| ~~P60~~ | — | tolto il 29/09/2026 | — |
| P61 | Giuseppe | vedi 9.2 (`auth/forms.py`, template di registrazione) | P16 |
| P62 | Christian | nessuno (`base.html`, `typography.css` sono suoi) | P19 |
| P36 | Christian | nessuno (crea solo `REVIEW.md`) | P31, P32, P33 |
| P37 | Christian | `CLAUDE.md`, `README.md` (P3 e P9, sempre Christian) | P36 |
| P39 | Giuseppe (riassegnato) | `docs/DEMO.md` (creato da P38, sempre Giuseppe) | P38 |
| P63 | Giuseppe | `friend_service.py` (P45, P47: ora di Giuseppe) | P45 |
| P64 | Giuseppe | nessuno (motore, `docs/REGOLE-GIOCO.md`) | P12, P13 |
| P65 | Giuseppe | vedi 9.2 (forse `ModeModal.js` o `home.js` di Christian) | P44, P45, P47 |
| P66 | Giuseppe | nessuno di altri studenti (`room.py` è di Giuseppe) | P25 |
| P67 | Giuseppe | `app/static/dev/*.json` (li leggono i test del tavolo di Christian), contratto 3.3 (ok di Giuseppe e Christian) | P58; aspetta D44 |
| P68 | Giuseppe | vedi 9.2 | P25; D43 decisa (strategia da rifare) |
| P69 | Christian | nessuno di altri studenti (`game.js`, `Table.js`, `TablePhrases.js` sono suoi dopo P33) | P58 |
| P70 | Christian | nessuno di altri studenti | P58; meglio dopo P71 |
| P71 | Christian | nessuno di altri studenti | P58 |
| P72 | Christian | nessuno di altri studenti | **P67** |
| P73 | Christian | `home.js`, `ModeModal.js` (dopo Giuseppe, P59); `core/events.js` (il nome `cpu:start`) | **P68** rifatto, **P59** |
| P74 | Christian | nessuno di altri studenti (file del tavolo) | P72 |
| P75 | Giuseppe | `app/static/dev/*.json` (li leggono i test del tavolo di Christian), contratto 3.3 (ok di Giuseppe e Christian, già dato il 01/10/2026) | P15 |
| P76 | Christian | nessuno di altri studenti | P75 (in `dev` dal 01/10) |
| P77 | Christian | nessuno di altri studenti | P72 |
| P78 | Christian | nessuno di altri studenti | P70; meglio dopo P74 e P76 |
| P79 | Christian | nessuno di altri studenti | P70 |
| P80 | Christian | nessuno di altri studenti | P71; meglio dopo P74 |
| P81 | Christian | `ChatWindow.js` (suo; l'ultimo a toccarlo è stato Giuseppe in P48) | P48 |
| P82 | Giuseppe | vedi 9.2 (forse `home.js` di Christian) | P44 |
| P83 | Giuseppe | vedi 9.2 (forse `home.js`, `InviteDialog.js`, `ModeModal.js` di Christian) | P47, P59 |
| P84 | Giuseppe | vedi 9.2; `docs/REGOLE-GIOCO.md`, contratto (ok di Giuseppe e Christian), `app/static/dev/*.json` | P24; meglio dopo P75 (stessi file) |
| P85 | Christian | nessuno di altri studenti | **P84** |
| P86 | Christian | nessuno di altri studenti | P71; meglio con P74 e P77 |
| P87 | Christian | nessuno di altri studenti (`variables.css` è suo) | P72; meglio dopo P74 e P90 |
| P88 | Giuseppe | `app/static/dev/*.json` (li leggono i test del tavolo di Christian), contratto 3.3 (ok di Giuseppe e Christian) | P27, P30; meglio dopo P75 (stessi esempi della vista) |
| P89 | Christian | nessuno di altri studenti | P88, P74 (in `dev`) |
| P90 | Christian | nessuno di altri studenti | P72 |
| P91 | Christian | i test spostati (del tavolo, di Christian) e forse `tests/esegui_tutti.py` (di tutti: avvisare prima) | — |
| P92 | Giuseppe | vedi 9.2; `docs/REGOLE-GIOCO.md`, contratto (ok di Giuseppe e Christian), `app/static/dev/*.json` | P24, P55; meglio dopo P84 (stessi file) |
| P93 | Christian | nessuno di altri studenti (`core/events.js`, il nome dell'evento nuovo, è di Christian) | **P92** |
| P94 | Giuseppe | `game.js` di Christian solo da leggere (durate delle pause, confrontate da un test); contratto ed esempi se cambiano | P85 (meglio) |
| P95 | Christian | nessuno di altri studenti (`game.js` è suo); se la causa è nel server, avvisare Giuseppe | — |
| P96 | Giuseppe | nessuno di altri studenti (P16 l'ha fatto Giuseppe) | — |
| P97 | Christian | nessuno di altri studenti | — |
| P98 | Christian | nessuno di altri studenti | — |
| P99 | Christian | nessuno di altri studenti | — |
| P100 | Christian | nessuno di altri studenti | meglio con P102 |
| P101 | Christian | nessuno di altri studenti | — |
| P102 | Christian | nessuno di altri studenti | meglio con P100 |
| P103 | Christian | la pagina delle impostazioni (creata da Antonio in P17, poi P43 di Christian) | meglio dopo P85, P99 |
| P104 | Christian | nessuno di altri studenti | P98 |
| P105 | Christian | `pages/home.js` (solo `renderQueue`; toccato anche da Giuseppe in P28, P47, P59, P65, P83) | — |
| P106, P107, P108 | Christian | nessuno di altri studenti | P99 (P107), P102 (P108) |
| P109 | Christian | nessuno di altri studenti (CSP invariata) | P103 |
| P110, P112 | Christian | nessuno di altri studenti | P101 |
| P111 | Christian (con l'ok di Giuseppe) | `config.py` e i test della coda (di Giuseppe) | — |
| P113 | Christian | nessuno di altri studenti | P109 |
| P114 | Christian | i test spostati (del tavolo, di Christian); `tests/esegui_tutti.py` (di tutti) solo se si sceglie di alzare il limite: avvisare Giuseppe | — |

**Controlli di parallelismo** [D]: questi punti avvengono negli stessi giorni ma toccano file diversi. La verifica vale finché ognuno resta nei file elencati nel suo punto.
- P25 (Giuseppe) ∥ P28 (Antonio): `room.py`, `game_events.py`, `connection_events.py`, `game.js` contro `matchmaking.py`, `lobby_events.py`, `sockets/__init__.py`, `home.js`.
- P47 (Giuseppe) ∥ P48 (Antonio): `invites.py`, `friends_events.py`, `FriendsPanel.js` contro `chat_service.py`, `chat_repo.py`, `chat_events.py`, `ChatWindow.js`.
- P44 (Giuseppe) ∥ P33 (Christian): P33 può toccare `home.js` (vedi 9.2), quindi **P33 attende che P44 sia in `dev`**.
- P31 e P32 (Giuseppe) ∥ P33 (Christian): P32 può toccare gli stessi file di P33 (gestori degli eventi e pagine): chi comincia per secondo controlla la lista dei file di 9.2 dell'altro.
- P59 (Giuseppe) ∥ P33 (Christian): P59 può toccare `home.js` e `ModeModal.js`; P33 è andato prima (in `dev` dal 29/09/2026): P59 parte dopo il pull.
- P63–P67 (Giuseppe) ∥ P69–P71 (Christian): server, motore e tempo reale contro pagina del tavolo; nessun file in comune. **P65** può scoprire che la causa è nella pagina (`ModeModal.js`, `home.js`): in quel caso Giuseppe avvisa Christian prima di toccarli. **P72** parte solo quando P67 è in `dev` (esempi della vista e contratto).
- P75, P82, P83, P84, P88 (Giuseppe) ∥ P74, P76–P81, P85, P86, P87, P89, P90 (Christian): vista, server e tempo reale contro pagina del tavolo e chat. In comune possono esserci solo `home.js`, `InviteDialog.js`, `ModeModal.js` (P82, P83: Giuseppe avvisa Christian prima di toccarli) e gli esempi della vista (P75, P84, P88: P76, P85 e P89 partono dopo il loro merge). P75, P84 e P88 toccano gli stessi file (vista ed esempi): li fa Giuseppe uno dopo l'altro. I punti del tavolo di Christian toccano tutti `game.js` e `Table.js`: uno alla volta.
- P92 (Giuseppe) ∥ P85, P93 (Christian): vista, stanza ed evento contro pagina del tavolo; in comune solo gli esempi della vista (`app/static/dev/*.json`): **P93 parte dopo il merge di P92**. P84 e P92 toccano gli stessi file del motore e della vista: li fa Giuseppe uno dopo l'altro.
- P94, P96 (Giuseppe) ∥ P95, P97–P103 (Christian): stanza, timer e accesso contro pagina del tavolo e impostazioni; nessun file in comune, ma P94 deve usare le stesse durate delle pause di `game.js`: se Christian cambia una pausa (P99, P85), lo dice a Giuseppe. P103 può toccare `CSP_DIRECTIVES` in `app/__init__.py` (di Giuseppe): avvisarlo prima.
- P113 (Christian) ∥ P82, P38, P39 (Giuseppe): pagina dei suoni contro presenza e installazione della demo; nessun file in comune. P111 (Christian, 05/10) ha toccato `config.py` e i test della coda di Giuseppe, con il suo ok: già in `dev`.

### 9.2 Punti con file NON sicuri

Per questi punti non posso dire adesso con certezza quali file verranno toccati. Per ognuno indico i file che penso tocchi, perché non sono sicuro, e a chi lo assegnerei. **Regola:** all'inizio del punto chi lo fa scrive qui la lista definitiva dei file e la comunica agli altri. Se uno di quei file è in uso da un altro studente, aspetta che l'altro abbia finito e fatto il merge in `dev`.

**P32 — Sicurezza di base** · proposto: Giuseppe (giorno 7) — **fatto il 29/09/2026**
- *Lista definitiva* (confermata da Giuseppe prima di cominciare): modificati `config.py`, `app/__init__.py`, `app/realtime/events.py`, `app/realtime/presence.py`, `app/blueprints/auth/routes.py`, `app/services/auth_service.py`; creati `tests/api/test_sicurezza.py`, `tests/sockets/test_validazione_eventi.py`, `tests/frontend/test_csp.py`; modificati `tests/sockets/conftest.py`, `tests/sockets/test_connessione.py`, `tests/e2e/helpers.py`. Non toccati i gestori degli eventi, `auth/forms.py`, `friends/routes.py` e i template: validavano già tutto.
- *Sicuri* (previsti all'inizio): `config.py`, `app/__init__.py` (creati da P4), `tests/api/test_sicurezza.py`, `tests/sockets/test_validazione_eventi.py`.
- *Probabili*: `app/sockets/connection_events.py`, `lobby_events.py`, `game_events.py`, `friends_events.py`, `chat_events.py`, `home_events.py`; `app/blueprints/auth/forms.py`; `app/blueprints/friends/routes.py`; forse `app/templates/auth/*.html`; `app/services/auth_service.py` (la cancellazione dell'account controlla solo la partita in corso, non la coda né un invito aperto [L], punto delicato di P17).
- *Perché non sono sicuro*: il punto corregge **quello che manca** nel codice scritto da P16–P56. Se i gestori validano già bene i dati, non vanno toccati; se no, sì. Lo si sa solo leggendo il codice quando esiste. I punti di Antonio che toccavano quei file sono tutti in `dev` (P28, P29 e P48 li ha fatti Giuseppe).

**P33 — Errori e connessione nell'interfaccia** · proposto: Christian (giorno 6) — **fatto il 29/09/2026**
- *Sicuri*: crea `app/static/js/components/Banner.js`, `app/static/css/components/banner.css`, `tests/frontend/test_niente_alert.py`; modifica `app/static/js/core/socket.js` (P23), `app/templates/base.html` (P40).
- *Probabili*: `app/static/js/pages/game.js`, `home.js`, `app/static/js/components/ModeModal.js`, `FriendsPanel.js`, `ChatWindow.js`.
- **Lista definitiva** (29/09/2026, fatto): i sicuri, i cinque probabili, più `app/static/js/components/InviteDialog.js` (pulsanti dell'invito ricevuto), `tests/frontend/test_banner_connessione.py` e `tests/frontend/test_base.py` (12 CSS in `base.html`).
- *Perché non sono sicuro*: bisogna disattivare i pulsanti quando la connessione cade. Se le pagine usano già un'unica funzione `render(vista)` che legge lo stato della connessione, basta toccare `socket.js`; altrimenti vanno modificate anche le pagine e i componenti. Quei file sono stati modificati da Giuseppe e Antonio: si inizia solo dopo che P25, P44, P47 e P48 sono in `dev`.

**P34 — Rifinitura mobile e accessibilità** · proposto: Christian (giorno 6–7)
- *Probabili*: qualunque file in `app/static/css/` e `app/templates/`.
- **Lista definitiva** (29/09/2026, la parte nel codice): creato `tests/frontend/test_rifinitura.py`; modificati `app/static/js/components/Table.js`, `FriendsPanel.js`, `TablePhrases.js` (solo il commento), `app/templates/main/index.html`, `app/templates/game/table.html`. Resta la prova su un telefono vero.
- *Perché non sono sicuro*: i problemi si scoprono solo provando le pagine su un telefono vero. **Regola:** mentre P34 è aperto, nessun altro modifica file dell'interfaccia.

**P35 — Carte vere** · proposto: Christian
- *Sicuri*: modifica `app/static/js/components/Card.js`, `app/static/css/components/card.css` (P20, sempre Christian); crea `app/static/img/cards/LICENZA.md`.
- *Probabili*: 40 immagini (più il dorso) in `app/static/img/cards/`.
- *Perché non sono sicuro*: nomi e formato dei file (`.webp`, `.png`, `.svg`) dipendono dal set che sceglierete (D19). Nessun conflitto con gli altri studenti: sono tutti file di Christian.

**P42 — Logo vero** · proposto: Christian
- *Sicuri*: modifica `app/templates/partials/navbar.html`, `app/static/css/components/navbar.css` (P40, sempre Christian).
- *Probabili*: `app/static/img/logo.svg` (oppure `.png`), `app/static/img/favicon.ico`; forse `app/templates/base.html` per la favicon.
- *Perché non sono sicuro*: il logo è un SVG disegnato da Claude, ma la favicon può servire in più formati o no, in base a come la inserite.

**P43 — Immagini degli avatar** · proposto: Christian
- *Sicuri*: crea la cartella `app/static/img/avatars/`.
- *Probabili*: un file per avatar (nomi e formato da D29); modifica `app/templates/partials/navbar.html`, `app/static/js/components/StatsPanel.js` (P30), `FriendsPanel.js` (P47), `app/templates/profile/settings.html` (P17).
- **Lista definitiva** (30/09/2026): creati `app/static/img/avatars/*.svg` (12), `app/static/js/components/Avatar.js`, `app/templates/partials/avatar.html`, `tests/frontend/test_avatar.py`; modificati `partials/navbar.html`, `profile/settings.html`, `FriendsPanel.js`, `ModeModal.js`, `QueueOverlay.js`, `Table.js`, `navbar.css`, `friends-panel.css` (commento), `pages/profile.css`, `app/services/avatars.py` (commento).
- *Perché non sono sicuro*: dipende da **quanti** avatar e **che formato** (D29), e da come le altre pagine hanno già previsto lo spazio per l'avatar: se usano un unico componente o una macro del template, basta modificare quello. `settings.html` e `FriendsPanel.js` sono di altri studenti: si inizia solo dopo che P17 e P47 sono in `dev`.

**~~P53 — Tema scuro automatico~~** · tolto il 30/09/2026
- *Sicuri*: modifica `app/static/css/base/variables.css` (P19).
- *Probabili*: i CSS dei componenti e delle pagine che hanno ombre, trasparenze o immagini da regolare al buio (per esempio `navbar.css`, `card-background.css`, `table.css`).
- *Perché non sono sicuro*: dipende da quanto i punti precedenti hanno usato solo le variabili. **Regola:** come per P34, mentre P53 è aperto nessun altro modifica file dell'interfaccia.

**P59 — 2v2 con più amici invitati** · proposto: Giuseppe
- *Sicuri*: `app/realtime/invites.py`, `app/sockets/friends_events.py` (P47), `docs/CONTRATTO-SOCKET.md` (5.3, con l'accordo dei tre), `tests/sockets/test_inviti.py`.
- *Probabili*: `app/realtime/matchmaking.py` (se mancano giocatori, arrivano dalla coda), `app/static/js/pages/home.js`, `InviteDialog.js`, `ModeModal.js` (di Christian: la lista degli amici da invitare con più scelte).
- **Lista definitiva** (29/09/2026, fatto): `app/realtime/invites.py`, `app/sockets/friends_events.py`, `app/realtime/matchmaking.py`, `docs/CONTRATTO-SOCKET.md` (4 e 5.3), `app/static/dev/home_esempio.json`, `app/static/js/pages/home.js`, `InviteDialog.js`, `ModeModal.js` e `QueueOverlay.js` (di Christian, con il suo ok), `tests/sockets/test_inviti.py`, `test_matchmaking_2v2.py`, `test_matchmaking_1v1.py`, `tests/frontend/test_invito_ricevuto.py`, `tests/api/test_pagina_home.py` (una riga); creato `tests/frontend/test_inviti_2v2.py`.
- *Perché non sono sicuro*: dipende da come si fissano i dettagli all'inizio del punto (quanti amici, chi manca, grafica del modal).

**P61 — Regole della password** · proposto: Giuseppe (da confermare)
- *Probabili*: `app/blueprints/auth/forms.py` (P16), `config.py` (una chiave se le regole vanno in configurazione), `app/templates/auth/register.html`, `tests/api/test_auth.py` e le password dei test che non rispettano le regole nuove.
- **Lista definitiva** (29/09/2026, fatto): `app/blueprints/auth/forms.py`, `app/templates/auth/register.html`, `tests/api/test_auth.py`. Niente `config.py` (`PASSWORD_MIN = 8` c'era già) né `auth/routes.py`.
- *Perché non sono sicuro*: dipende da dove si mettono le regole (solo nel modulo o anche in `config.py`) e da quanti test usano password troppo semplici.

**P64 — Niente canto nella prima presa della mano** · proposto: Giuseppe
- *Sicuri*: `app/game/engine/singing.py`, `docs/REGOLE-GIOCO.md`, `tests/engine/test_canti.py`.
- *Probabili*: `app/game/engine/state.py` (se serve sapere a che presa si è), `tests/engine/test_mano.py` e le partite simulate delle suite `sockets` ed `e2e` che cantano nella prima presa.
- **Lista definitiva** (29/09/2026, fatto): `app/game/engine/singing.py`, `game.py`, `docs/REGOLE-GIOCO.md`, `tests/engine/test_canti.py`, `test_mano.py`, `test_partita.py`, `test_mossa_automatica.py`, `tests/sockets/test_partita.py`. `state.py` non cambia.
- *Perché non sono sicuro*: dipende da come il motore sa a che presa della mano si è, e da quanti test cantano subito.

**P65 — Amico sbloccato non online** · proposto: Giuseppe
- *Probabili*: `app/services/friend_service.py`, `app/realtime/presence.py`, `app/sockets/friends_events.py`, `app/sockets/home_events.py`; forse `app/static/js/pages/home.js` o `ModeModal.js` (di Christian); un test nuovo in `tests/sockets/`.
- **Lista definitiva** (29/09/2026, fatto): `app/services/friend_service.py`, `app/static/js/pages/home.js`, `docs/CONTRATTO-SOCKET.md` (5.2, una frase), `tests/sockets/test_inviti.py`, `tests/frontend/test_inviti_2v2.py`. Non toccati `presence.py`, `friends_events.py`, `home_events.py`, `ModeModal.js`.
- *Perché non sono sicuro*: prima va trovata la causa. Se è nella pagina, i file sono di Christian: si concorda prima.

**P66 — Mossa automatica dopo il rientro** · proposto: Giuseppe
- *Probabili*: `app/realtime/room.py`, `app/sockets/game_events.py`, `app/sockets/connection_events.py`; un test in `tests/sockets/` o `tests/e2e/`.
- **Lista definitiva** (29/09/2026, fatto): `app/realtime/room.py` (`_apply`, una condizione), `tests/sockets/test_timer_riconnessione.py`.
- *Perché non sono sicuro*: prima va riprodotto; il difetto può stare nel timer (`_turn_token`) o nel rientro.

**P68 — Partita contro la CPU: mosse e stanza** · proposto: Giuseppe
- *Probabili*: un file nuovo nel motore per la scelta della mossa (per esempio `app/game/engine/cpu.py`), `app/realtime/room.py`, `room_manager.py`, `app/sockets/lobby_events.py` (o un evento nuovo), `docs/CONTRATTO-SOCKET.md`, forse `match_service.py` e il database (una partita con la CPU si salva? conta per le statistiche?), test nuovi in `tests/engine/` e `tests/sockets/`.
- **Lista definitiva** (30/09/2026, prima versione): creati `app/game/engine/cpu.py`, `tests/engine/test_cpu.py`, `tests/sockets/test_cpu.py`; modificati `app/realtime/room.py`, `room_manager.py`, `app/sockets/lobby_events.py`. Niente database né `match_service.py`; contratto ancora da scrivere. La strategia va rifatta (D43).
- **Lista definitiva** (04/10/2026, seconda parte, Giuseppe): modificati `app/game/engine/cpu.py`, `views.py` (solo `ROOM_PLAYER_FIELDS`), `app/realtime/room.py`, `docs/CONTRATTO-SOCKET.md` (4.1 nuovo, `cpu` in 3.3), `app/static/dev/vista_1v1.json`, `vista_2v2.json`, `tests/engine/test_cpu.py`, `tests/sockets/test_cpu.py`. Non toccati `lobby_events.py`, il database e `match_service.py`.
- *Perché non sono sicuro*: dipendeva da D43 (strategia, 1v1 o anche 2v2, salvataggio e rating), decisa il 04/10/2026: solo 1v1, niente salvataggio, quindi niente database; `cpu: true` tocca anche `views.py` o `room.py`, il contratto e gli esempi della vista. Una colonna o tabella nuova va discussa prima (convenzioni del progetto).

**P69, P70, P71 — Tocchi, animazioni e grafica del tavolo** · proposto: Christian
- *Probabili*: `app/static/js/pages/game.js`, `components/Table.js`, `Trick.js`, `Hand.js`, `Card.js`, `TablePhrases.js`, `Scoreboard.js`; `app/static/css/components/table.css`, `trick.css`, `hand.css`, `card.css`, `table-phrases.css`, `app/static/css/pages/game.css`; forse `app/templates/game/table.html`, `app/static/fonts/icone.txt` e il font delle icone (P62); i test `tests/api/test_pagina_tavolo.py`, `tests/frontend/test_momenti_tavolo.py`, `test_frasi_pagina.py`.
- **Liste definitive** (29/09/2026, fatto): **P69**: `app/static/css/pages/game.css`, `pages/game.js`, `tests/frontend/test_tocchi_tavolo.py` (nuovo), `test_momenti_tavolo.py`, `test_frasi_pagina.py`. **P71**: `Trick.js`, `Table.js`, `trick.css`, `table.css`, `table-phrases.css`, `tests/api/test_grafica_tavolo.py` (nuovo), `test_pagina_tavolo.py`. **P70**: `pages/game.js`, `Card.js`, `Hand.js`, `Trick.js`, `Table.js`, `trick.css`, `hand.css`, `table.css`, `tests/api/test_grafica_tavolo.py`, `tests/frontend/test_lancio_carta.py`, `test_carte_avversari.py`, `test_distribuzione.py` (nuovi).
- *Perché non sono sicuro*: le animazioni e le misure sul telefono si scoprono provando. **Regola:** come per P34, mentre uno di questi punti è aperto nessun altro modifica i file del tavolo.

**P72 — I propri punti sopra le carte in mano** · proposto: Christian
- *Probabili*: `app/static/js/components/Hand.js`, `Scoreboard.js`, `HandSummary.js`, `pages/game.js`, `hand.css`, `scoreboard.css`; i test del tavolo.
- **Lista definitiva** (01/10/2026, fatto): `app/static/js/components/Table.js`, `pages/game.js`, `app/static/css/components/table.css`, `tests/api/test_punti_mano.py` (nuovo). Per D44 tabellone e riepilogo non cambiano: non toccati `Hand.js`, `Scoreboard.js`, `HandSummary.js`, `hand.css`, `scoreboard.css`.
- *Perché non sono sicuro*: dipende da D44 (cosa resta del tabellone e del riepilogo di fine mano) e dal nome del campo di P67.

**P73 — Partita contro la CPU nella home** · proposto: Christian
- *Probabili*: `app/templates/main/index.html`, `app/static/js/pages/home.js`, `components/ModeModal.js`, `app/static/css/pages/home.css`, `mode-modal.css`, `app/static/js/core/events.js` (il nome `cpu:start`, nota di Giuseppe in P68), `tests/api/test_pagina_home.py`.
- *Perché non sono sicuro*: dipendeva da D43, decisa il 04/10/2026: una scelta nella carta-modal (niente carta-pulsante nuova, quindi forse niente `index.html` e `home.css`); l'icona robot va in `app/static/fonts/icone.txt` e nel font (P62), e `Avatar.js` o `Table.js` la mostrano al posto dell'avatar.

**P74, P76, P77, P78, P79, P80, P85, P86, P87, P89, P90 — Tavolo (prova a mano del 01/10/2026)** · proposto: Christian
- *Probabili*: `app/static/js/pages/game.js`, `components/Table.js`, `Trick.js`, `Hand.js`, `Card.js`, `TablePhrases.js`, `Scoreboard.js`; `app/static/css/components/table.css`, `trick.css`, `hand.css`, `card.css`, `table-phrases.css`, `scoreboard.css`, `app/static/css/pages/game.css`; forse `app/templates/game/table.html` (P79, se le carte si scaricano dalla pagina), `app/static/fonts/icone.txt` e il font delle icone (P85); i test `tests/api/test_grafica_tavolo.py`, `test_punti_mano.py`, `test_pagina_tavolo.py`, `tests/frontend/test_momenti_tavolo.py`, `test_frasi_pagina.py`, `test_lancio_carta.py`, `test_distribuzione.py`, `test_carte_avversari.py`, più un test nuovo per punto.
- **P85** (04/10/2026, lista definitiva): modificati `app/static/js/core/events.js` (`GAME_LAY_DOWN`), `components/SingButtons.js`, `Hand.js` (`RevealedHand`), `Table.js`, `pages/game.js`, `app/static/css/components/table.css`; creato `tests/table/test_calata.py`.
- *Perché non sono sicuro*: posizioni e animazioni si scoprono provando. **Regola:** sono tutti file di Christian; i punti si fanno uno dopo l'altro, con il pull di `dev` in mezzo. P76 attende P75, P85 attende P84 e P89 attende P88 (esempi della vista e contratto di Giuseppe). P90 può toccare anche `app/static/css/components/scoreboard.css` e `Scoreboard.js`; P87 anche `app/static/css/base/variables.css`.
- *Liste definitive* (02/10/2026, Christian):
  - **P79**: `app/static/js/components/Card.js`, `app/static/js/pages/game.js`; creato `tests/api/test_carte_pronte.py`.
  - **P90**: `app/static/css/components/scoreboard.css`, `table.css`, `app/static/js/components/Table.js`, `tests/frontend/test_carte_avversari.py` (con l'ok di Christian); creato `tests/api/test_tavolo_telefono.py`.
  - **P77**: `app/static/js/components/Trick.js`, `Table.js`, `app/static/css/components/trick.css`, `table.css`, `tests/api/test_grafica_tavolo.py`, `test_punti_mano.py`, `test_pagina_tavolo.py`.
  - **P74**: `app/static/css/components/table.css`, `scoreboard.css`, `table-phrases.css`, `tests/api/test_grafica_tavolo.py`, `test_punti_mano.py` (non serviti `Table.js` e `test_carte_avversari.py`, che erano nella lista approvata). Correzione del 03/10: `table.css`, `tests/api/test_grafica_tavolo.py`.
  - *Liste definitive* (03/10/2026, Christian):
  - **P86**: `app/static/css/components/trick.css`, `tests/api/test_grafica_tavolo.py`.
  - **P76**: `app/static/js/components/Trick.js`, `app/static/css/components/trick.css`; creato `tests/api/test_presa_affiancata.py` (non servito `Table.js`).
  - **P89**: `app/static/js/components/Table.js`, `app/static/css/components/table.css`; creato `tests/api/test_rating_tavolo.py`.
  - **P80**: `app/static/css/components/table-phrases.css`; creato `tests/api/test_frasi_di_lato.py` (non serviti `TablePhrases.js`, `Table.js`, `game.js`).
  - **P87**: `app/static/css/base/variables.css`, `app/static/css/components/table.css`, `scoreboard.css`; creato `tests/api/test_stile_tavolo.py`.
  - **P78**: `app/static/js/pages/game.js`, `app/static/css/components/trick.css`, `tests/frontend/test_carte_avversari.py`; creato `tests/api/test_animazioni_in_fila.py` (non serviti `Trick.js`, `Hand.js`, `hand.css`).

**P91 — Suite `frontend` sotto il limite di tempo** · proposto: Christian — **fatto il 03/10/2026**
- **Lista definitiva** (03/10/2026): creata la suite `tests/table/` con il test nuovo `test_timer_in_anticipo.py`; spostati in `tests/table/` da `tests/frontend/` `test_momenti_tavolo.py`, `test_frasi_pagina.py`, `test_distribuzione.py`, `test_carte_avversari.py`, `test_lancio_carta.py`, `test_tocchi_tavolo.py` e da `tests/api/` `test_carte_pronte.py`, `test_animazioni_in_fila.py`, `test_punti_mano.py`; modificati `app/static/js/pages/game.js` (`redrawAfter`), `test_frasi_pagina.py`, `test_carte_pronte.py`, `test_punti_mano.py` (nota). **Non toccato** `tests/esegui_tutti.py`.
- *Probabili*: i file dei test del tavolo che non usano MySQL (`tests/frontend/test_momenti_tavolo.py`, `test_lancio_carta.py`, `test_distribuzione.py`, …) spostati in `tests/api/`; forse `tests/esegui_tutti.py` (`SUITE_TIMEOUT`, di tutti: avvisare Giuseppe prima).
- *Perché non sono sicuro*: quali file spostare si decide misurando la durata di ciascuno; la causa dei blocchi fino al limite va ancora trovata.

**P82 — Giocatori online veri senza login** · proposto: Giuseppe
- *Probabili*: `app/realtime/presence.py`, `app/sockets/home_events.py` o `connection_events.py` (se è un evento senza login) oppure `app/blueprints/main/routes.py` (se è una rotta), `app/realtime/events.py` (limite di frequenza), `docs/CONTRATTO-SOCKET.md`; `app/static/js/pages/home.js` (di Christian: chiedere prima); test in `tests/sockets/` o `tests/api/`.
- *Perché non sono sicuro*: dipende dalla via scelta (rotta o evento) e da come si aggiorna il numero.

**P83 — Invito accettato e poi annullato** · proposto: Giuseppe — **fatto il 01/10/2026**
- *Lista definitiva* (Giuseppe): modificati `app/static/js/pages/home.js` (di Christian: 4 righe in `onConnection`, con il suo ok), `app/static/js/components/InviteDialog.js`, `tests/frontend/test_inviti_2v2.py`. Non toccati `invites.py` e `friends_events.py`: il server era già giusto.
- *Probabili*: `app/realtime/invites.py`, `app/sockets/friends_events.py`; forse `app/static/js/pages/home.js`, `InviteDialog.js`, `ModeModal.js` (di Christian: chiedere prima); `tests/sockets/test_inviti.py`, `tests/frontend/test_invito_ricevuto.py`, `test_inviti_2v2.py`.
- *Perché non sono sicuro*: prima va trovata la causa (server o pagina).

**P84 — "Cala le carte": regola, motore e stanza** · proposto: Giuseppe — **fatto il 04/10/2026**
- **Lista definitiva** (04/10/2026, Giuseppe): creati `app/game/engine/lay_down.py`, `tests/engine/test_cala.py`, `tests/sockets/test_cala.py`; modificati `app/game/engine/actions.py`, `state.py`, `rules.py`, `game.py`, `views.py`, `cpu.py`, `app/realtime/room.py`, `app/sockets/game_events.py`, `app/services/match_service.py`, `docs/CONTRATTO-SOCKET.md` (3.2, 3.3), `app/static/dev/vista_1v1.json`, `vista_2v2.json`, `tests/engine/test_viste.py`, `test_cpu.py`, `tests/sockets/test_partita.py`, `test_timer_riconnessione.py`, `tests/e2e/helpers.py`. Non toccati `auto_move.py`, il database (`mosse_partita.tipo` è un `VARCHAR(20)` senza `CHECK`) né il regolamento (già scritto il 04/10).
- *Probabili*: `app/game/engine/actions.py`, `game.py`, `views.py`, forse un file nuovo nel motore per il controllo "imbattibile"; `app/game/engine/auto_move.py` (solo se serve dire che non cala) e `cpu.py`; `app/realtime/room.py`, `app/sockets/game_events.py`; `docs/CONTRATTO-SOCKET.md`, `docs/REGOLE-GIOCO.md`, `app/static/dev/*.json`; test in `tests/engine/` e `tests/sockets/`.
- *Perché non sono sicuro*: D45 è decisa (04/10/2026); dipende da come il motore rappresenta la fine anticipata della mano. Se cambia il salvataggio delle mosse (`mosse_partita`), va discusso prima (convenzioni del progetto).

**P92 — Carte del compagno scoperte e consiglio: regola, vista ed evento** · proposto: Giuseppe
- *Probabili*: `app/game/engine/views.py` (carte del compagno nella vista), forse `game.py` o `rules.py` (la condizione "briscola e mazzo finito"); `app/realtime/room.py` (il consiglio in memoria, tolto quando il compagno gioca), `app/sockets/game_events.py` (l'evento nuovo); `docs/CONTRATTO-SOCKET.md`, `docs/REGOLE-GIOCO.md`, `app/static/dev/*.json`; test in `tests/engine/` (per esempio `test_viste.py`) e `tests/sockets/`.
- **Lista definitiva** (04/10/2026, Giuseppe): modificati `app/game/engine/game.py` (`partner_cards_visible`), `views.py`, `cpu.py`, `app/realtime/room.py`, `app/sockets/game_events.py` (`game:advise`), `docs/CONTRATTO-SOCKET.md` (3.2, 3.3), `app/static/dev/vista_2v2.json`, `tests/engine/test_viste.py`, `tests/e2e/helpers.py`; creato `tests/sockets/test_consiglio.py`. Non toccati `rules.py`, `auto_move.py` e il regolamento.
- *Perché non sono sicuro*: D46 è decisa (04/10/2026); dipende da dove sta il consiglio (stanza o motore: proposta stanza, come le frasi del tavolo di P55, perché non cambia il gioco); `auto_move.py` e `cpu.py` non dovrebbero cambiare.

**P93 — Carte del compagno scoperte e consiglio al tavolo** · proposto: Christian
- *Probabili*: `app/static/js/pages/game.js` (momento "carte scoperte", invio del consiglio), `components/Table.js`, `Hand.js`, `Card.js`; `app/static/js/core/events.js` (il nome dell'evento); `app/static/css/components/table.css`, `hand.css`; forse `app/static/fonts/icone.txt` e il font (P62); test nuovi in `tests/api/` (grafica) e `tests/table/` (animazione e consiglio).
- **Lista definitiva** (04/10/2026): modificati `app/static/js/core/events.js` (`GAME_ADVISE`, `GAME_ADVICE`), `components/Hand.js`, `Table.js`, `pages/game.js`, `app/static/css/components/table.css`; creato `tests/table/test_carte_compagno.py`.
- *Perché non sono sicuro*: dipende dal campo e dall'evento di P92 e dalle misure del ventaglio scoperto sul telefono, che si scoprono provando.

**P94 — Turno da 15 secondi, dopo le pause** · proposto: Giuseppe
- *Probabili*: `app/realtime/room.py` (`TURN_SECONDS`, partenza del timer dopo le pause, attese della CPU), forse `config.py`; `docs/CONTRATTO-SOCKET.md` e `app/static/dev/*.json` se cambia `seconds_total` negli esempi; test in `tests/sockets/` e un test che confronta le pause con quelle di `game.js`.
- **Lista definitiva** (04/10/2026, Giuseppe): modificati `config.py` (`TURN_SECONDS` 15), `app/realtime/room.py`, `docs/CONTRATTO-SOCKET.md` (3.3, riga `turn`), `app/static/dev/vista_1v1.json`, `vista_2v2.json`, `tests/sockets/conftest.py`, `test_partita.py`, `test_cpu.py`, `test_cala.py`; creato `tests/sockets/test_turno.py`. `game.js` di Christian solo letto dal test.
- *Perché non sono sicuro*: dipende da come il server conta le pause (una durata fissa per tipo di momento, oppure un segnale della pagina) e da P85 (carte calate).

**P95 — Partita interrotta dal riavvio del server** · proposto: Christian
- *Probabili*: `app/static/js/pages/game.js` (`join`, con `not_found`); forse `components/Banner.js` o un avviso nella home; un test nuovo in `tests/frontend/` o `tests/table/`.
- **Lista definitiva** (04/10/2026): modificati `app/static/js/pages/game.js` (`join`, `showGone`), `app/static/css/components/table.css` (`.table__gone`); creato `tests/table/test_partita_interrotta.py`. Il server non è cambiato.
- *Perché non sono sicuro*: la causa è letta nel codice [L], non ancora riprodotta.

**P96 — Login con nome utente o email** · proposto: Giuseppe
- *Probabili*: `app/blueprints/auth/forms.py`, `routes.py`, `app/services/auth_service.py` (limite dei tentativi per account), `app/repositories/user_repo.py` (lettura per email), `app/templates/auth/login.html`; test in `tests/api/`.
- **Lista definitiva** (04/10/2026, Giuseppe): modificati `app/blueprints/auth/forms.py` (`LoginForm`), `app/services/auth_service.py`, `app/repositories/user_repo.py` (`get_by_email`), `tests/api/test_auth.py`. Non toccati `routes.py` né `login.html`.
- *Perché non sono sicuro*: dipende da come il limite dei tentativi riconosce l'account quando l'utente non esiste.

**P97, P98, P99, P100, P101, P102 — Tavolo (prova del 04/10/2026)** · proposto: Christian
- *Probabili*: `app/static/js/pages/game.js`, `components/Table.js`, `Hand.js`, `Trick.js`, `TablePhrases.js`; `app/static/css/components/table.css`, `hand.css`, `trick.css`, `table-phrases.css`, `scoreboard.css`, `app/static/css/pages/game.css` (P98: regole contro lo zoom); forse `app/static/fonts/icone.txt` e il font (P102, se serve un'icona); i test del tavolo in `tests/api/` e `tests/table/`.
- *Perché non sono sicuro*: posizioni, misure e animazioni si scoprono provando; P97 va prima riprodotto. **Regola**: sono tutti file di Christian; i punti si fanno uno dopo l'altro, con il pull di `dev` in mezzo.
- *Liste definitive* (05/10/2026):
  - **P97**: `app/static/css/components/card.css`, `app/static/js/pages/game.js` (`keepHover`); creato `tests/table/test_mano_ferma.py`.
  - **P98**: `app/static/css/pages/game.css`, `tests/table/test_tocchi_tavolo.py`.
  - **P99**: `app/static/js/pages/game.js`, `app/static/css/components/trick.css`, `tests/table/test_animazioni_in_fila.py`; creato `tests/table/test_lancio_mio.py`.
  - **P100 e P102**: `app/static/js/components/Trick.js`, `Table.js`, `app/static/css/components/table.css`, `trick.css`, `scoreboard.css`, `tests/api/test_grafica_tavolo.py`, `test_pagina_tavolo.py`, `test_frasi_di_lato.py`, `tests/table/test_carte_avversari.py` (correzione di P99).
  - **P101**: `app/static/js/components/Table.js`, `app/static/css/components/table.css`, `table-phrases.css`, `tests/table/test_frasi_pagina.py`, `tests/api/test_grafica_tavolo.py`.

**P103 — Suoni al tavolo** · proposto: Christian
- *Probabili*: una cartella nuova `app/static/sounds/` con i file e la loro licenza; un modulo nuovo in `app/static/js/core/` per suonare e ricordare la scelta; `app/static/js/pages/game.js`; la pagina delle impostazioni (`app/templates/profile/settings.html` e il suo script); forse `CSP_DIRECTIVES` in `app/__init__.py` (`media-src`, di Giuseppe: avvisarlo) e `tests/frontend/test_csp.py`.
- **Lista definitiva** (05/10/2026): creati `app/static/js/core/sounds.js`, `tests/table/test_suoni.py`; modificati `app/static/js/pages/game.js`, `app/templates/profile/settings.html`, `app/static/js/pages/profile.js`, `app/static/css/pages/profile.css`. Nessun file audio (poi P109) e CSP invariata.
- *Perché non sono sicuro*: dipende dai file audio scelti e da come la CSP tratta l'audio.

**P104–P112 — Correzioni del 05/10/2026** · proposto: Christian — **fatti il 05/10/2026**
- *Liste definitive*:
  - **P104**: `app/static/js/pages/game.js` (`touchend`, `DOUBLE_TAP_MS`), `tests/table/test_tocchi_tavolo.py`.
  - **P105**: `app/static/js/components/QueueOverlay.js`, `app/static/js/pages/home.js` (solo `renderQueue`), `tests/api/test_pagina_home.py`.
  - **P106**: `app/static/css/components/table.css`, `tests/api/test_grafica_tavolo.py`.
  - **P107**: `app/static/js/pages/game.js` (`throwStart`, `FAN_TILT`, `aimThrows`), `app/static/css/components/trick.css`, `tests/table/test_lancio_mio.py`.
  - **P108**: `app/static/js/components/Trick.js`, `Card.js`, `app/static/css/components/table.css`, `trick.css`, `tests/api/test_grafica_tavolo.py`, `test_pagina_tavolo.py`, `tests/table/test_carte_pronte.py`.
  - **P109**: creati `app/static/sounds/` (file MP3 e `LICENZA.md`); modificati `app/static/js/core/sounds.js`, `app/static/js/pages/game.js`, `app/templates/profile/settings.html`, `tests/table/test_suoni.py`.
  - **P110**: `app/static/js/pages/game.js`, `components/TablePhrases.js`, `Table.js` (commento); creato `tests/table/test_frasi_senza_lampeggio.py`.
  - **P111**: `config.py`, `tests/sockets/test_matchmaking_1v1.py`, `test_matchmaking_2v2.py`, `tests/api/test_pagina_home.py` (file di Giuseppe con il suo ok, tranne l'ultimo).
  - **P112**: `app/static/css/components/table-phrases.css`, `app/static/js/pages/game.js` (`placePhrasesMenu`), `tests/table/test_frasi_senza_lampeggio.py`.

**P113 — Pagina per ascoltare e confrontare i suoni** · proposto: Christian
- *Probabili*: se la pagina sta nel sito, una prova solo di sviluppo (per esempio una rotta in `app/blueprints/game/routes.py` o un parametro `?demo=` come il tavolo), un template e uno script di pagina; se sta fuori dal repository, nessun file del progetto finché non si sceglie. Dopo la scelta: i file in `app/static/sounds/`, `LICENZA.md`, `SOUNDS` in `app/static/js/core/sounds.js`, `tests/table/test_suoni.py`.
- *Perché non sono sicuro*: dove sta la pagina si decide all'inizio del punto con Christian; i file dei suoni dipendono dalla scelta dei tre (D47).

**~~P60 — Togliere le viste finte~~** · tolto il 29/09/2026
- *Sicuri*: `app/static/js/pages/game.js`, `home.js`; `tests/api/test_pagina_tavolo.py`, `test_pagina_home.py`, `tests/frontend/test_momenti_tavolo.py`, `test_frasi_pagina.py`.
- *Probabili*: `app/blueprints/game/routes.py`, `app/blueprints/main/routes.py`, `app/static/dev/`, una pagina di prova solo di sviluppo.
- *Perché non sono sicuro*: dipende se le viste finte si tolgono o si spostano; le usano anche i test del browser.

**P38 — Installazione demo separata** · proposto: Antonio (giorno 7); fatto a metà da Giuseppe, a cui è passato il 28/09/2026
- *Sicuri*: crea `docs/DEMO.md`.
- *Deciso* (28/09/2026, Giuseppe): anche `scripts/pianifica_backup.ps1`, lo script che crea l'attività pianificata di Windows per il backup, con il test `tests/db/test_demo.py`. Sono già in `dev`.
- *Cosa resta*: sul PC della demo, dopo D20, i passi 1–9 di `docs/DEMO.md` e i tre controlli del "Fatto quando"; nessun file nuovo nel repository. Il resto (cartella demo, `.env`, `PRODUZIONE`, firewall) è fuori dal repository e non crea conflitti.

**Nota su P31** (Giuseppe): i file di test sono sicuri. Se però i test trovano dei bug, le correzioni toccheranno altri file: ogni correzione diventa un punto nuovo, con la sua lista di file.
