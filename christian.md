# Riepiloghi di Christian

> **Questo file lo scrive solo Christian** (Studente 3: interfaccia e documenti). Giuseppe e Antonio lo leggono dopo il `git pull` di `dev`, per sapere cosa è cambiato: punti fatti, decisioni nuove e cosa devono fare loro. Nessun altro lo modifica, nemmeno per correggere un errore: si segnala a Christian.
>
> **Come si aggiorna** (regola in `CLAUDE.md`, "Consegna"): a fine punto, e dopo ogni aggiornamento dei documenti condivisi quando è di turno (a fine giornata il gruppo sceglie chi li aggiorna), Christian aggiunge il riepilogo **in cima** alla sezione "Riepiloghi", nello stesso branch e commit; così arriva in `dev` con il merge. È il gemello di `giuseppe.md` e `antonio.md`.

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

### P35 — Carte vere (28/09/2026)

- **Branch**: feature/p35-carte-vere
- **File**: creati `app/static/img/cards/` (40 carte `<seme>-<valore>.webp`, 316 KB in tutto) e `app/static/img/cards/LICENZA.md`; modificati `js/components/Card.js`, `css/components/card.css`; fuori elenco, miei (P20), `tests/frontend/test_carte.py` (controllava le immagini del segnaposto: ora le 40 carte, il peso sotto 1 MB e la licenza) e il titolo di `app/static/dev/carte.html`; questo file
- **Controlli**: 1167 PASS in 7 suite (1 nuovo), `ruff check .` pulito
- **Decisioni prese** (mie):
  - **D19 chiusa: le carte vengono dalle scansioni di Matsoftware** su Wikimedia Commons (`Carte_da_gioco_siciliane_-_<seme>.jpg`, CC BY-SA 3.0, la stessa fonte delle carte dello sfondo). Verificato: ogni foglio ha tutte le 10 carte del seme; autore e licenza confermati dall'API di Commons. La riga dei crediti che c'è già vale anche per queste carte;
  - **niente valore negli angoli**, come sulle carte siciliane vere (Claude consigliava una piccola etichetta, per le carte piccole al tavolo);
  - **carta intera** con il suo margine bianco; gli angoli arrotondati li fa il CSS, come prima;
  - nomi dei file uguali ai codici del motore (`coppe-10.webp`); il dorso resta `img/cards-bg/dorso.webp`; le carte di `img/cards-bg/` (sfondo, logo, carte-pulsante) non sono cambiate.
- **Domande nuove**: nessuna
- **Punti delicati**: le carte si sono ritagliate con uno script fuori dal progetto (Pillow, non è tra le dipendenze): come sono state fatte è scritto in `img/cards/LICENZA.md`. Le carte della colonna sinistra delle scansioni sono un po' tagliate dal bordo del foglio
- **Cosa devono fare gli altri**: **Chi è di turno sui documenti**: spuntare P35, chiudere D19 in `DA-DECIDERE.md` e spostarla in `DECISIONI.md` (Interfaccia) con le scelte qui sopra. **Giuseppe**: la proposta sull'ultima presa di ogni mano (`last_hand.last_trick`, tuo riepilogo di P44) è **approvata da tutti e tre** (Antonio tramite Christian): fai tu motore, vista, contratto 3.3 ed esempi, come proponevi; quando è in `dev`, io adatto `game.js` per mostrare le carte prima del riepilogo

### Correzione — Test della home dopo P44 (28/09/2026)

- **Branch**: feature/p56-frasi-tavolo (commit a parte, dopo il rebase su P29 e P44)
- **File**: modificato `tests/api/test_pagina_home.py`: `test_avviso_di_rientro_solo_se_previsto` ora aspetta il numero vero degli online ("1"), come proposto da Giuseppe in P44, invece di leggere subito il "24" dei dati finti
- **Controlli**: 1166 PASS in 7 suite (dopo il rebase su P44), `ruff check .` pulito
- **Decisioni prese**: nessuna
- **Domande nuove**: nessuna. La proposta di Giuseppe sull'ultima presa di ogni mano (`last_hand.last_trick`, riepilogo di P44) aspetta la risposta di Christian
- **Cosa devono fare gli altri**: **Giuseppe**: il test l'ho corretto io, come per P28

### P56 — Frasi del tavolo nella pagina (28/09/2026)

- **Branch**: feature/p56-frasi-tavolo
- **File**: creati `js/components/TablePhrases.js`, `css/components/table-phrases.css`, `tests/frontend/test_frasi_pagina.py` (non `test_frasi_tavolo.py` come in scaletta: c'è già in `tests/sockets/`, di P55, e due file con lo stesso nome fermano un `pytest` lanciato su tutte le cartelle); modificati `js/pages/game.js`, `templates/game/table.html`; fuori elenco, con il mio ok, `js/components/Table.js` (il pulsante sta nella barra in alto, i fumetti sugli avatar) e `tests/frontend/test_momenti_tavolo.py` (conta gli eventi `demo:` della prova, ora 4); questo file
- **Controlli**: 1131 PASS in 7 suite (12 nuovi), `ruff check .` pulito
- **Decisioni prese** (mie, sulle raccomandazioni di Claude):
  - **pulsante in alto a destra** (icona del fumetto, etichetta accessibile "Frasi"; su computer anche la scritta);
  - **elenco sotto il pulsante**, con le frasi come pillole che vanno a capo: a 360 px ci stanno tutte senza scorrere; si chiude con una frase, con Esc o toccando fuori;
  - **fumetto per 4 secondi** accanto all'avatar di chi ha parlato: a destra per chi sta in alto, sopra l'avatar per te e per chi sta ai lati (per te era previsto a destra, ma lì c'è il tuo nome e a 360 px non c'è spazio); una frase nuova dello stesso giocatore sostituisce la vecchia; il nome si legge solo con i lettori di schermo;
  - dopo l'invio il pulsante resta **spento 3 secondi**; con `too_fast` per i `retry_after` secondi, senza messaggi; senza connessione il messaggio va nella riga di stato;
  - **frasi anche a partita finita** (il server lo permette, P55);
  - nella prova (`?demo=`) il pulsante compare solo quando arriva l'elenco (evento `demo:phrases`); le frasi degli altri con `demo:phrase`; una frase scelta mostra subito il proprio fumetto, senza server
- **Domande nuove**: nessuna
- **Punti delicati**: il tavolo si ridisegna tutto a ogni vista, quindi elenco aperto, pausa e fumetti stanno in `game.js` (come i momenti di P57), e `render` rimette il fuoco sul pulsante o sulla frase che l'aveva, per chi usa la tastiera. `PHRASE_PAUSE_MS` in `game.js` deve restare uguale a `TABLE_PHRASE_MIN_INTERVAL_SECONDS` (lo controlla un test). La pagina non ha una copia delle frasi: un test controlla che nessun testo dell'elenco sia scritto nei file JS. L'invio vero (`game:send_phrase`) nel browser non è provato: lo provano i test di P55 lato server
- **Cosa devono fare gli altri**: **Chi è di turno sui documenti**: spuntare P56, registrare le decisioni qui sopra in `DECISIONI.md` (Interfaccia), il punto delicato in `CLAUDE.md`, e nella scaletta il nome del file di test. **Giuseppe**: niente; se cambi il limite delle frasi in `config.py`, cambia anche `PHRASE_PAUSE_MS` in `game.js`

### P30 — Pannello statistiche con dati reali (28/09/2026)

- **Branch**: feature/p30-statistiche (partito da `dev` con P28 già dentro)
- **File**: creati `app/services/stats_service.py`, `app/repositories/stats_repo.py`, `tests/api/test_statistiche.py`; modificati `app/blueprints/stats/routes.py`, `js/components/StatsPanel.js`; fuori elenco, con il mio ok, `templates/partials/navbar.html` (`data-stats-url` ora è `/stats/me`) e `tests/frontend/test_navbar.py` (il test controllava l'indirizzo dei dati finti); questo file
- **Controlli**: 1119 PASS in 7 suite (14 nuovi), `ruff check .` pulito
- **Correzione per P28** (commit a parte, stesso branch): in `tests/api/test_pagina_home.py` il test `test_partita_veloce_apre_e_annulla_la_coda` ora aspetta "tra 1400 e 1600", come proposto da Giuseppe: da P28 la home usa la coda vera e l'utente di prova ha 1500
- **Decisioni prese** (mie, sulle raccomandazioni di Claude):
  - il pannello usa **sempre i dati veri** (`GET /stats/me`), anche in sviluppo; `statistiche_esempio.json` resta solo come esempio del contratto (i dati finti della home non li ho toccati);
  - nel 2v2 la partita in cui **il compagno abbandona** non conta tra le "partite che contano per il rating" di chi è rimasto (il suo rating non cambia, D13), quindi non accorcia il suo "provvisorio"; nel conteggio generale resta una partita persa.
  - Scelte tecniche: percentuale di vittorie sulle partite giocate, pareggi compresi, arrotondata con la metà per eccesso (12,5% → 13%); rating arrotondato allo stesso modo; senza login `not_logged_in` con 401 in JSON, come le rotte degli amici
- **Domande nuove**: nessuna. La domanda di Giuseppe (P28) **"2v2 con più amici invitati"** (un solo amico invitato: in squadra insieme; più di uno: squadre a caso) è **approvata da tutti e tre** (28/09/2026: Christian, e Antonio tramite Christian). Cambia D27 ("un amico alla volta"), il contratto 5.3 e P47 (Giuseppe)
- **Antonio non potrà lavorare al progetto per un bel po'** (da 28/09/2026, detto da Christian): i suoi punti ancora aperti (P29, P48, P38, P39) vanno riassegnati
- **Punti delicati**: "provvisorio" si conta da `giocatori_partita` e `partite.conta_per_rating` (non si salva, P27): se un giorno cambia chi "conta per il rating", va cambiato `stats_repo.rated_games`. Le colonne `DOUBLE` di `rating` si convertono in `float` in `stats_repo.rating_values`. `fetchStats` ora restituisce il campo `data` della risposta del contratto e rifiuta una risposta senza `ok: true`
- **Cosa devono fare gli altri**: **Chi è di turno sui documenti**: spuntare P30, registrare la decisione sul compagno di chi abbandona in `DECISIONI.md` (Dati) e il punto delicato in `CLAUDE.md`. **Chi è di turno** registra anche la decisione sul 2v2 con più amici (aggiorna D27 in `DECISIONI.md`, contratto 5.3) e la riassegnazione dei punti di Antonio nella sezione 9 di `SCALETTA.md`. **Giuseppe**: il test della home l'ho corretto io come proponevi; la proposta sul 2v2 con più amici è approvata, per P29 e P47 (va aggiornato il contratto 5.3). `stats_repo.py` legge soltanto, `rating_repo.py` non l'ho toccato

### P57 — Momenti del tavolo: ultima presa, fine mano, carte del canto (28/09/2026)

- **Branch**: feature/p57-momenti-tavolo
- **File**: creati `js/components/HandSummary.js`, `css/components/hand-summary.css`, `tests/frontend/test_momenti_tavolo.py`; modificati `js/pages/game.js`, `js/components/Table.js`, `Trick.js`, `css/components/table.css`, `trick.css`; fuori elenco, con il mio ok, `templates/game/table.html` (una riga `<link>` per `hand-summary.css`); questo file
- **Controlli**: 1066 PASS in 7 suite (12 nuovi), `ruff check .` pulito
- **Decisioni prese** (mie, sulle raccomandazioni di Claude):
  - **ultima presa**: quando una presa si chiude, le carte restano al centro per **1,5 secondi** con "Prende *nome*" ("Prendi tu") e la carta di chi ha preso in risalto, poi scivolano verso di lui; spariscono subito se nel frattempo qualcuno gioca la prima carta della presa nuova; la mano non si blocca mai;
  - **riepilogo di fine mano**: riquadro sopra il centro del tavolo (mai sopra la mano, che resta giocabile), "Mano N finita", righe Carte prese / Canti / Mano / Punteggio, la tua squadra per prima ("Tu" e il nome nel 1v1, "Noi / Loro" nel 2v2); si chiude **da solo dopo 5 secondi** o con "Ok". Per quei secondi può coprire la prima carta della mano nuova (rischio accettato);
  - **fine partita**: prima si vede l'ultima presa, poi il riquadro "Hai vinto / Hai perso" con dentro il riepilogo dell'ultima mano (solo se la partita è finita a punti, non per abbandono);
  - **carte del canto** (D15): Re e Cavallo accanto a chi ha cantato, verso il centro (le tue sopra la tua riga), con "Canta 40/20", per `show_seconds`; si vedono anche a chi ha cantato; la frase nella riga di stato resta, per i lettori di schermo;
  - i momenti partono solo confrontando due viste: **mai alla prima vista** (apertura della pagina o rientro);
  - **solo nella prova** (`?demo=`) la pagina accetta gli eventi del browser `demo:state` e `demo:sang` su `[data-table]`: li usano i test e si possono mandare dalla console.
- **Domande nuove**:
  - **ultima presa di ogni mano** (per Giuseppe e il gruppo, cambia il contratto): quando l'ultima presa chiude la mano, il motore comincia subito la mano nuova con `last_trick` a `null` (`game.py`, `apply_game`), quindi la pagina non riceve mai quelle carte, e la carta che chiude la mano non si vede. Per ora si passa direttamente al riepilogo (scelta mia). Proposta: aggiungere l'ultima presa a `last_hand` (per esempio `last_hand.last_trick`), in `views.py` e nel contratto 3.3; la pagina va poi adattata con poche righe. Va decisa in tre (contratto);
  - **parametro `?demo=` a fine progetto** (per chi è di turno sui documenti): non voglio lasciare nella versione consegnata le prove nell'indirizzo (`?demo=` del tavolo e della home). Propongo un punto nuovo, mio, in fondo alla scaletta (prima di P36): togliere o spostare le viste finte, con le suite che le usano (`test_pagina_tavolo.py`, `test_pagina_home.py`, `test_momenti_tavolo.py`) da adattare
- **Punti delicati**: `game.js` decide i momenti in `noticeMoments(prima, dopo)` dentro `render`; i timer ridisegnano con `redraw()`, che non fa niente se la partita è aperta altrove (D14). `Table(view, handlers, status, moments)` riceve i momenti già decisi e li disegna soltanto. Marcatori: `data-last-trick` (con `data-winner-seat`), `data-hand-summary` (con `data-hand-number`) e `data-hand-summary-close`, `data-sang-seat` (con `data-suit`, `data-points`). `.seat` ora ha `position: relative` (le carte del canto si posizionano da lì). `HandSummary.js` ha una copia di `teamName` di `Scoreboard.js` (tre righe), per non toccare un file fuori elenco
- **Cosa devono fare gli altri**: **Giuseppe**: leggere la domanda sull'ultima presa di ogni mano qui sopra. **Chi è di turno sui documenti**: spuntare P57, registrare le decisioni qui sopra in `DECISIONI.md` (Interfaccia), le due domande in `DA-DECIDERE.md` e il punto delicato di P57 in `CLAUDE.md`; 1066 controlli. **Antonio**: niente

### Documenti: regola dei documenti a turno; registrati P26, P27, la correzione di P25 e P55 (28/09/2026)

- **Branch**: docs/regola-documenti
- **File**: modificati `CLAUDE.md` (punto 5 di "Prima di lavorare", riga "Stato", "Processo di lavoro", "Testing", "Consegna", punti delicati di P25, P26 e P27; tolto un "D4" rimasto per sbaglio davanti al titolo), `DECISIONI.md` (Dati; Processo), `SCALETTA.md` (regola in cima, P25, P26, P27, sezioni 3, 8 e 9), questo file
- **Controlli**: nessuno (soli documenti); 1054 PASS dall'ultimo giro di Giuseppe (P55)
- **Decisioni prese**: **documenti condivisi a turno** (scelta del gruppo, sostituisce D22): durante la giornata ognuno scrive solo il riepilogo nel proprio file; a fine giornata il gruppo sceglie chi dei tre aggiorna `SCALETTA.md`, `CLAUDE.md`, `DECISIONI.md` e `DA-DECIDERE.md`, che legge i riepiloghi nuovi dei **tre** file (compreso il suo). Chi è di turno lo dice a Claude a inizio sessione, altrimenti Claude non tocca i documenti. Fin dove sono registrati i riepiloghi lo dice la riga "Stato" di `CLAUDE.md`, uno per file. Registrate anche le decisioni di Antonio su P26 (la stanza tiene le mosse, formato delle mosse) e P27 (2v2: la squadra avversaria come un solo avversario)
- **Domande nuove**: nessuna; nella riga "Stato" tra le cose da concordare c'è il blocco occasionale della suite `api` segnalato da Antonio
- **Punti delicati**: `create_room` dentro Flask (P26); rating come `Decimal` (P27); con il turno corto nei test la carta che chiude una presa si vede solo in `last_trick` (P25)
- **Cosa devono fare gli altri**: **Giuseppe** e **Antonio**: aggiornate voi l'intestazione dei vostri file (`giuseppe.md`, `antonio.md`), che dice ancora "Christian lo legge e da qui aggiorna i documenti condivisi": ora li aggiorna chi è di turno, e quando siete di turno voi il riepilogo dell'aggiornamento va nel vostro file, nel branch `docs/…` (quindi nello schema il branch può essere anche `docs/…`). Non l'ho fatto io per non creare conflitti git con i vostri branch. Da ora nei branch dei punti scrivete solo il vostro riepilogo, e aggiornate i documenti solo quando il gruppo vi sceglie. **P55** (Giuseppe, arrivato in `dev` durante questo aggiornamento): spuntato, punto delicato in `CLAUDE.md`. Prossimi punti: Antonio **P28**, poi P29; Giuseppe P44 e P47 aspettano P29 (intanto `auth.js` o un aiuto ad Antonio); io **P57**, poi **P30** e **P56**

### P46 — Pannello amici e finestra chat; registrato P25 (28/09/2026)

- **Branch**: feature/p46-amici (codice, commit `392e3ea`, dopo il rebase su P25), poi docs/p46 (documenti)
- **File**: creati `js/components/FriendsPanel.js`, `ChatWindow.js`, `css/components/friends-panel.css`, `chat.css`, `tests/frontend/test_pannello_amici.py`, `tests/browser.py` (pilota di Chrome in comune); modificati `js/core/layout.js`, `docs/CONTRATTO-SOCKET.md` (2.2); fuori elenco, con il mio ok, `base.html`, `test_base.py`, `navbar.html`, `mode-modal.css`, `test_pagina_home.py` (ora usa `tests/browser.py`). Documenti: `SCALETTA.md`, `DECISIONI.md`, `CLAUDE.md`, questo file
- **Controlli**: 990 controlli (10 nuovi); nell'ultimo giro 989 PASS: il test `test_turno_scaduto_il_server_gioca_la_mossa_automatica` di P25 fallisce sul mio PC anche su `dev` senza P46; `ruff check .` pulito
- **Decisioni prese**: pannello con i dati veri di P45, chat finta fino a P48; niente "Invita" nel pannello; "Altro" (rimuovi, blocca) e sezione "Bloccati"; contratto 2.2 completato (accordo dei tre)
- **Domande nuove**: nessuna
- **P25** (fatto da Antonio con il permesso di Giuseppe, riepilogo in `antonio.md`): spuntato in `SCALETTA.md`, decisione "chi non arriva al tavolo non ha limite di tempo" in `DECISIONI.md`, punto delicato in `CLAUDE.md`
- **Punti delicati**: "indietro" chiude il pannello con `history.pushState`; `request_id` funziona anche in http (demo in rete locale); i test nel browser rispondono al posto del server (`routes` di `tests/browser.py`)
- **Cosa devono fare gli altri**: **Giuseppe**: il test di P25 qui sopra è instabile (ipotesi [D]: con 0,3 secondi il timer parte prima che i due giocatori siano seduti); per P47 gli avvisi `friends:changed` devono far ricaricare la lista del pannello: la funzione `load()` oggi è interna a `initFriendsPanel` in `FriendsPanel.js`, basta esporla. **Antonio**: per P48 la chat vera va in `openChat` e `onSend` di `FriendsPanel.js`; `ChatWindow.js` non va cambiato. Per P26 la chiamata al salvataggio va in `Room._apply` e `Room.abandon`

### Documenti: niente test per i soli documenti; registrato P45 (28/09/2026)

- **Branch**: docs/regola-test-documenti
- **File**: modificati `CLAUDE.md` ("Processo di lavoro", "Regole git", "Testing", riga "Stato", punto delicato di P45), `DECISIONI.md` (Processo; presenza degli amici), `SCALETTA.md` (P45), questo file
- **Controlli**: nessuno, per la regola nuova; 963 PASS calcolato (904 dell'ultimo giro completo più i 59 di P45)
- **P45 di Antonio** (dal suo riepilogo): spuntato in `SCALETTA.md`, presenza degli amici in `DECISIONI.md`, punto delicato su READ COMMITTED e riga "Stato" in `CLAUDE.md`. I dettagli che il contratto 2.2 non fissava (forma di `blocked`, ordine della lista, codici di errore, risposta di `POST /friends/requests`) restano nel suo riepilogo: aggiungerli al contratto richiede l'accordo dei tre (D8), lo propongo con P46
- **Decisioni prese**: quando aggiorno solo i documenti (branch `docs/…`) Claude non lancia i test, nemmeno dopo un pull o un rebase; il numero di controlli si prende dai vostri riepiloghi o dall'ultimo giro su un punto. Per i lotti che cambiano codice o test non cambia niente
- **Domande nuove**: nessuna
- **Punti delicati**: nessuno
- **Cosa devono fare gli altri**: niente; continuate a scrivere nel riepilogo il numero di PASS del vostro giro, perché ora è l'unica fonte per i documenti

### P22 — Home con dati finti; registrati P7, P18 e P17 (28/09/2026)

- **Branch**: feature/p22-home (codice), poi docs/p22 (documenti e correzione del test); dopo i rebase su P7, P18 e P17 i commit sono `9ae2f99` (P22) e `09a184d` (test)
- **File**: creati `css/pages/home.css`, `css/components/card-background.css`, `mode-modal.css`, `queue-overlay.css`, `js/components/ModeModal.js`, `CardBackground.js`, `QueueOverlay.js`, `ResumeBanner.js`, `tests/api/test_pagina_home.py`; modificati `templates/main/index.html`, `js/pages/home.js`, `blueprints/main/routes.py`; fuori elenco, con il mio ok, `css/base/variables.css` (2 variabili) e `tests/frontend/test_base.py` (conta solo i CSS di `base.html`). Documenti: `SCALETTA.md`, `DECISIONI.md`, `DA-DECIDERE.md`, `CLAUDE.md`, questo file
- **Controlli**: 904 PASS in tutto dopo il rebase su P7, P18 e P17 (38 nuovi), `ruff check .` pulito; la home confrontata con il prototipo a 360×640 (uguale, tranne il contatore degli amici di P46)
- **Decisioni prese**: dati finti solo in sviluppo e nei test, `?demo=rientro` per l'avviso di rientro; aspetto della schermata di coda e dell'avviso di rientro (il prototipo non li aveva); "uno contro uno" al posto di "tu contro lui"; `--on-tile` e `--ink` in `variables.css` (tutto in `DECISIONI.md`, Interfaccia)
- **Domande nuove**: **D40**, il font delle icone pesa 5,4 MB: caricare solo le icone usate?
- **P7 di Antonio** (dal suo riepilogo in `antonio.md`): spuntato in `SCALETTA.md`, decisione su log ed errori in `DECISIONI.md` (Tecnologia), punto delicato e riga "Stato" in `CLAUDE.md`. Pagine 404 e 500 senza navbar: per ora va bene così
- **P18 di Antonio** (dal suo riepilogo): spuntato in `SCALETTA.md`; in `CLAUDE.md` riga "Stato", punto delicato e "Comandi utili" (conferma con il nome del database, programmi `mysqldump` e `mysql`). Nessuna decisione nuova; D10 resta aperta
- **P17 di Antonio** (dal suo riepilogo): spuntato in `SCALETTA.md`; in `DECISIONI.md` la cancellazione dell'account e i 12 codici degli avatar (D29 aggiornata: resta aperto solo chi disegna le immagini e con che licenza, per P43); punto delicato e riga "Stato" in `CLAUDE.md`
- **Punti delicati**: la home non scorre grazie a `--tile-h` (`home.css`): qualunque cosa si aggiunga alla home va misurata, e `test_pagina_home.py` lo fa in Chrome o Edge senza finestra alle misure di `LEGGIMI.md` (porta 5099, saltato senza browser). Il test serve i font di Google da una copia in una cartella temporanea: la prima volta scarica il font delle icone (5,4 MB), poi la suite `api` sta sotto il minuto
- **Cosa devono fare gli altri**: **Antonio** (P28): "Gioca" arriva a `play(...)` in `home.js`; al posto dei dati finti manda `queue:join` e, con la risposta o con `queue:status`, metti lo stato in `state.queue` e chiama `render(state)`: la schermata di coda si apre da sola, conta i secondi e con "Annulla" chiama `leaveQueue()` (lì va `queue:leave`). Il modal non va toccato per la coda. **Giuseppe** (P47): gli inviti passano da `sendInvite` e `cancelInvite` in `home.js`; il risultato (`invite:update`) si dà al modal con `setInviteStatus(user_id, status)` di `ModeModal.js`; la lista degli amici è `state.friends` (forma di `GET /friends/`). (P44): `home:status` va in `state.status`, poi `render(state)`

### Documenti: file dei riepiloghi di Antonio (28/09/2026)

- **Branch**: docs/antonio-md
- **File**: creato `antonio.md` (intestazione e schema, nessun riepilogo); modificati `CLAUDE.md` ("Prima di lavorare" punto 5, "Processo di lavoro", "Consegna" punto 9, riga "Stato"), `SCALETTA.md` (nota in cima e tabella dei file condivisi), `DECISIONI.md` (decisione nuova, quella su `giuseppe.md` aggiornata), questo file; in `giuseppe.md` solo l'intestazione (ora dice che lo leggono Christian e Antonio), su richiesta esplicita di Christian: i riepiloghi non sono toccati e il file resta scritto solo da Giuseppe
- **Controlli**: nessun codice cambiato; 790 PASS restano quelli di P24
- **Decisioni prese**: Antonio scrive i suoi riepiloghi in **`antonio.md`**, come Giuseppe in `giuseppe.md`. Ognuno scrive solo il proprio file e legge gli altri due dopo il pull di `dev`: io leggo `giuseppe.md` e `antonio.md` e ne ricavo gli aggiornamenti dei documenti condivisi; Giuseppe legge `christian.md` e `antonio.md`; Antonio legge `christian.md` e `giuseppe.md`
- **Domande nuove**: nessuna
- **Punti delicati**: nessuno
- **Cosa devono fare gli altri**: **Antonio**: a fine punto aggiungi il riepilogo in cima ad `antonio.md`, nel branch del punto e nello stesso commit, invece di mandarmelo per messaggio; dopo ogni pull leggi `christian.md` e `giuseppe.md`. **Giuseppe**: dopo il pull leggi anche `antonio.md`; nell'intestazione di `giuseppe.md` ho cambiato solo la frase sui lettori (eccezione unica, chiesta da Christian): se hai un branch che tocca l'intestazione, fai il pull prima

### Documenti: P24 (28/09/2026)

- **Branch**: docs/p24
- **File**: modificati `SCALETTA.md` (P24 spuntato, **P57 aggiunto**, "Da dove si parte"), `DECISIONI.md` (stanze di gioco, P57), `CLAUDE.md` (riga "Stato", numero di test, punto delicato di P24), questo file
- **Controlli**: nessun codice cambiato; `python tests/esegui_tutti.py` su `dev` con P24: 790 PASS in 6 suite (confermato il conteggio di Giuseppe)
- **Decisioni prese**: registrate quelle tecniche di P24 (dal riepilogo di Giuseppe)
- **Decisione nuova**: **P57**, punto nuovo mio dopo P25: al tavolo l'ultima presa per un momento, il riepilogo di fine mano e le carte del canto per 3 secondi (P24 li lascia fuori e P25 non li tocca)
- **Domande nuove**: nessuna
- **Punti delicati**: nessuno in più
- **Cosa devono fare gli altri**: **Giuseppe** P25 (dopo tocca a me con P57 su `game.js`); **Antonio** (P28, P29) crea le partite con `create_room(...)` senza modificare `room_manager.py`

### Documenti: P21, P23 e D18 (28/09/2026)

- **Branch**: docs/p21-p23
- **File**: modificati `SCALETTA.md` (P21 e P23 spuntati, "Da dove si parte"), `DECISIONI.md` (D18, tavolo, client Socket.IO), `DA-DECIDERE.md` (D18 chiusa), `CLAUDE.md` (riga "Stato", numero di test, punti delicati di P21 e P23), questo file
- **Controlli**: nessun codice cambiato; 761 PASS restano quelli di P21
- **Decisioni prese**: registrate quelle di P21 e di P23 (dal riepilogo di Giuseppe)
- **Domande nuove**: nessuna
- **Punti delicati**: **correzione**: nei riepiloghi di P20 avevo scritto `legal.cards`, ma nel contratto le carte giocabili sono `legal.play`; corretto qui sotto, in `SCALETTA.md` e nei commenti del codice
- **Cosa devono fare gli altri**: niente in più di quanto scritto in P21

### P21 — Tavolo di gioco con le viste finte (28/09/2026)

- **Branch**: feature/p21-tavolo (commit `450bb53`, in `dev` e su GitHub dopo un rebase su P23, senza conflitti)
- **File**: creati `app/templates/game/table.html`, `app/static/js/pages/game.js`, `app/static/js/components/Table.js`, `Trick.js`, `Scoreboard.js`, `Timer.js`, `SingButtons.js`, `app/static/css/components/table.css`, `trick.css`, `scoreboard.css`, `timer.css`, `app/static/css/pages/game.css`, `tests/api/test_pagina_tavolo.py`; modificato `app/blueprints/game/routes.py`. Fuori elenco, solo commenti: `Hand.js`, `app/static/dev/carte.html` (`legal.play`)
- **Controlli**: 761 PASS in tutto (13 nuovi), `ruff check .` pulito; foto a 360×640, 1366×657, 1440×900 e 1920×1080
- **Cosa fa**:
  - `/game/<game_id>` (l'indirizzo di `game:start`) con il login; `?demo=1v1` e `?demo=2v2` disegnano le viste finte, solo in sviluppo e nei test;
  - `game.js` ha un'unica `render(vista)` che ridisegna tutto il tavolo; in prova carte e "Canta" mostrano solo una scritta, "Esci" chiede conferma e torna alla home;
  - navbar nascosta; tu in basso e gli altri verso destra (nel 2v2 compagno in alto); anello del tempo attorno all'avatar; presa, mazzo e briscola al centro; canti come icone accanto al nome; "compagno", "mazziere", "scollegato · 48 s" sotto il nome.
- **Decisioni prese**: D18 chiusa (stesso panno della home); navbar nascosta al tavolo; anello del tempo; mazzo con il numero e briscola con l'Asso del seme.
- **Domande nuove**: nessuna
- **Punti delicati**: l'etichetta "Canta 40 / 20" la ricava la pagina (40 se `sings` è vuoto): se si preferisce che la mandi il server, va cambiato il contratto. Il test del tavolo nel browser usa la porta 5099, come la suite `sockets`.
- **Cosa devono fare gli altri**:
  - **Giuseppe** (P24): in `game.js` i punti da collegare sono segnati con "P24:"; a ogni `game:state` basta chiamare `render(vista)`; `onPlay` riceve la carta già come `{suit, rank}` (il campo `card` di `game:play_card`), `onSing` il seme; mentre si aspetta la risposta vanno disattivati i pulsanti (con un messaggio nella riga di stato, `setStatus`). Restano a P24/P25: ultima presa per un momento, riepilogo di fine mano, carte del canto per 3 secondi (`game:sang`).

### Documenti: P20, D39, P16 e correzione di `migrate.py` (28/09/2026)

- **Branch**: docs/p20-d39-p16
- **File**: modificati `SCALETTA.md` (P16 e P20 spuntati, nota di P35 sulla fonte delle carte, "Da dove si parte"), `DECISIONI.md` (accesso di P16, D39, carte segnaposto, pagina di prova), `DA-DECIDERE.md` (D39 chiusa, proposta in D19), `CLAUDE.md` (riga "Stato", numero di test, punti delicati di P16 e P20)
- **Controlli**: nessun codice cambiato; 736 PASS restano quelli di P20
- **Decisioni prese**: registrate quelle di P16 (dal riepilogo di Giuseppe) e di P20 e D39 (sotto)
- **Domande nuove**: nessuna; da concordare `js/pages/auth.js` ("Da dove si parte")
- **Punti delicati**: nessuno in più
- **Cosa devono fare gli altri**: leggere la proposta sulla fonte delle carte vere (sotto, in P20)

### P20 — Componenti carta e mano, e D39 (28/09/2026)

- **Branch**: feature/p20-carte (commit `74e3727` per D39 e `d69f517` per P20, in `dev` e su GitHub dopo un rebase su P16 e sulla correzione di `migrate.py`, senza conflitti)
- **File**: creati `app/static/js/components/Card.js`, `Hand.js`, `app/static/css/components/card.css`, `hand.css`, `app/static/dev/carte.html`, `carte.css`, `carte.js`, `tests/frontend/test_carte.py`. Per D39: modificati `LoginPrompt.js`, `Modal.js` (opzione `footer`, fuori elenco: file mio di P19) e `test_navbar.py`
- **Controlli**: 736 PASS in tutto (17 nuovi: 16 di P20 e 1 di D39), `ruff check .` pulito; foto a 360×640 e 1440×900
- **Cosa fa**:
  - `Card(carta)` disegna una carta scoperta, `Card(carta, { onPlay, playable })` una carta-pulsante della mano, `CardBack()` il dorso; ogni carta ha `data-suit` e `data-rank`;
  - `Hand(carte, { playable, onPlay })` mette le carte in fila dritta e rende giocabili solo quelle di `legal.play`; `HiddenHand(n)` mostra n carte coperte (per `cards_in_hand` degli avversari);
  - la pagina di prova `http://localhost:5000/static/dev/carte.html` mostra le 40 carte, il dorso, una mano da 5 e 3 carte coperte.
- **Decisioni prese**: faccia con valore e Asso del seme, mano in fila dritta, pagina di prova con i font di Google; D39 chiusa (crediti anche nella finestra di accesso).
- **Domande nuove**: nessuna
- **Punti delicati**: queste carte si vedono **in gioco** finché P35 non porta quelle vere; P35 cambia solo la faccia (`Card.js`, `card.css`).
- **Proposta importante per le carte vere (P35, D19)**: le immagini che usiamo già (Cavallo, Re, Asso e Tre) sono ritagli delle scansioni di **Matsoftware** su Wikimedia Commons, un foglio per seme, con licenza **CC BY-SA 3.0**. Probabilmente ogni foglio contiene tutte le 10 carte del seme: si potrebbero ritagliare da lì **tutte le 40 carte**, con la riga dei crediti che c'è già. **Non è ancora verificato**: va controllato all'inizio di P35 aprendo le quattro scansioni. Se avete immagini vostre da proporre, ditelo (D19).
- **Cosa devono fare gli altri**:
  - **Giuseppe** (P24): la mano del tavolo si costruisce con `Hand(view.hand, { playable: view.legal.play, onPlay })`; la carta toccata arriva come `{suit, rank}`, già nella forma del campo `card` di `game:play_card`;
  - **Giuseppe** (grafica di P16): senza uno script di pagina, nelle pagine di accesso e registrazione la navbar non si apre ("Da concordare" in `SCALETTA.md`).

### Documenti: P40, P6 e correzione di `checks.py` (28/09/2026)

- **Branch**: docs/p40-p6
- **File**: modificati `SCALETTA.md` (P6 e P40 spuntati, `pages/home.js` spostato da P22 a P40, "Da dove si parte"), `DECISIONI.md`, `DA-DECIDERE.md` (D39), `CLAUDE.md` (riga "Stato", numero di test, punti delicati di P6 e P40)
- **Controlli**: nessun codice cambiato; 687 PASS restano quelli di P40
- **Decisioni prese**: quelle di P40, scritte sotto
- **Domande nuove**: D39 (crediti delle immagini per chi non ha fatto il login)
- **Punti delicati**: nessuno in più
- **Cosa devono fare gli altri**: niente in più di quanto scritto in P40

### P40 — Navbar, pannello statistiche, finestra "Accedi o registrati" (28/09/2026)

- **Branch**: feature/p40-navbar (commit `9e9d445`, in `dev` e su GitHub dopo un rebase su P6 e sulla correzione di `checks.py`, senza conflitti)
- **File**: creati `app/templates/partials/navbar.html`, `app/static/css/components/navbar.css`, `stats-panel.css`, `app/static/js/core/layout.js`, `app/static/js/components/StatsPanel.js`, `LoginPrompt.js`, `app/static/img/cards-bg/` (21 immagini del prototipo e `LICENZA.md`), `tests/frontend/test_navbar.py`; modificato `app/templates/base.html`. Fuori elenco, con il mio ok: creato `app/static/js/pages/home.js`, modificati `app/templates/main/index.html`, `app/static/css/base/variables.css` (6 variabili "(P40)") e `tests/frontend/test_base.py` (2 controlli)
- **Controlli**: 687 PASS in tutto (15 nuovi), `ruff check .` pulito; foto con Chrome a 360×640, 1366×657, 1440×900 e 1920×1080
- **Cosa fa**:
  - la navbar del prototipo compare in ogni pagina (`base.html` la include); con il login l'avatar mostra l'iniziale e apre il pannello statistiche (dati finti di `statistiche_esempio.json`, "provvisorio" sotto un rating provvisorio, Impostazioni, Esci e crediti delle immagini);
  - senza login avatar e amici aprono la finestra "Accedi o registrati per giocare", riutilizzabile (`openLoginPrompt()`);
  - il logo ha le due carte che si girano su Cavallo e Re, un seme alla volta; con "riduci movimento" resta fermo;
  - la classe `.felt-text` (scritte in rilievo sul panno con l'alone scuro) è pronta per "giocatori online" e i titoli di P22.
- **Decisioni prese**:
  - navbar senza login: icona generica e "Accedi"; avatar e amici aprono la finestra di accesso;
  - indirizzi `/auth/login`, `/auth/register`, `/auth/logout` e `/profile/settings`; "Esci" è un modulo POST con il token CSRF;
  - `pages/home.js` nasce con P40 (avvia solo `layout.js`): P22 lo modifica invece di crearlo;
  - `test_base.py`: 9 CSS in `base.html`, e i link normali (`<a href>`) verso siti esterni sono ammessi nei template (serve per la licenza nei crediti); le risorse esterne restano solo in `base.html`.
- **Domande nuove**: D39 (crediti per chi non ha fatto il login)
- **Punti delicati**: ogni pagina nuova deve importare `core/layout.js` e chiamare `initLayout()`; i colori scritti a mano vanno solo in `variables.css`. Con il login il pulsante degli amici per ora non fa niente: il pannello arriva con P46.
- **Cosa devono fare gli altri**:
  - **Antonio** (P16): creare `/auth/login` e `/auth/register`, e `/auth/logout` **solo in POST** con il controllo CSRF (il modulo "Esci" manda il campo `csrf_token`); il modello utente deve avere `username` (lo legge la navbar); per P17, la pagina è `/profile/settings`;
  - **Giuseppe**: niente per P40; se vuole, la correzione di `scripts/migrate.py` che ha segnalato ("Da dove si parte" in `SCALETTA.md`, "Da assegnare").

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
