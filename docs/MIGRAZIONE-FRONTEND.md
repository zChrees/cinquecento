# Migrazione del frontend a React + TypeScript + Vite

Analisi del 19/10/2026, prima di toccare il codice. Decisione e motivo in `DECISIONI.md` (19/10/2026). **Aggiornato lo stesso giorno**: il frontend nuovo è una **SPA** con il **proxy di Vite** in sviluppo, non più "isole" dentro le pagine Jinja (sezioni 4, 5 e 6).

**In breve**: il frontend di oggi è già ordinato (un solo modulo per Socket.IO, componenti come funzioni, attributi `data-*` stabili, niente `innerHTML`). Il problema vero è uno: **il tavolo si ridisegna tutto a ogni vista**, e per non far lampeggiare immagini e animazioni `game.js` ha accumulato molti accorgimenti e una quarantina di variabili di stato. React risolve proprio questo. Il resto si migra per avere un solo stile e i tipi, non perché sia rotto. Si va **una pagina alla volta**: le pagine già migrate fanno parte della SPA, le altre restano pagine Jinja finché non tocca a loro; il tavolo per ultimo.

Termini usati qui sotto:

- **React**: una libreria in cui si descrive *come deve essere* la pagina dato uno stato; è lei a cambiare solo i pezzi del DOM che cambiano davvero.
- **TypeScript**: JavaScript con i tipi (come in C: `Card[]`, `number`), controllati prima di eseguire.
- **Vite**: il programma che trasforma TypeScript e React in JavaScript normale per il browser (il "compilatore" del frontend), e durante lo sviluppo ricarica la pagina da solo.
- **SPA** (single-page application): il sito è **una sola pagina HTML**; React decide cosa mostrare (home, tavolo, impostazioni) e cambia il contenuto senza ricaricare. Flask risponde solo con dati (JSON) e Socket.IO.
- **Proxy di Vite**: in sviluppo si apre il server di Vite (`localhost:5173`), che serve la SPA e gira a Flask (`localhost:5000`) tutto il resto: dati, Socket.IO e le pagine Jinja non ancora migrate. Il browser vede un solo indirizzo.
- **Isola React** (scartata il 19/10): una pagina fatta da Flask con dentro un `<div>` che React riempie.

## 1. Stato attuale

Circa **6.000 righe** di JavaScript in `app/static/js/`, senza framework né bundler (moduli ES caricati così come sono).

**Come parte una pagina.** Ogni template Jinja (`main/index.html`, `game/table.html`, `auth/*.html`, `profile/settings.html`) carica **un solo** `<script type="module">` di `js/pages/`. I dati iniziali arrivano scritti nella pagina come attributi `data-*` (per esempio `data-game-id` sul tavolo, `data-demo-*` per le prove). Login, CSRF e scelta della pagina li fa Flask.

| Pagina | File | Righe | Cosa fa |
|---|---|---|---|
| Tavolo | `pages/game.js` | 1.087 | vista dal server, momenti, animazioni, timer, suoni, frasi, consigli |
| Home | `pages/home.js` | 500 | carte-pulsante, coda, inviti, online, stato della home |
| Impostazioni | `pages/profile.js` | 92 | avatar, password, cancellazione |
| Accesso/registrazione | `pages/auth.js` | 44 | invio una volta sola, blocco senza rete |
| Tutte (navbar) | `core/layout.js` | 193 | navbar, pannello statistiche, pannello amici |

**Tempo reale.** Tutto passa da `core/socket.js` (126 righe): **una connessione per scheda**, `on(evento, f)` restituisce la funzione per smettere di ascoltare, `send(evento, dati)` non fallisce mai (risponde sempre `{ok, data}` o `{ok: false, error}`), `onStatus` avvisa dei cambi di connessione, e l'avviso in cima alla pagina lo decide lui. I nomi degli eventi stanno in `core/events.js`. Gli ascolti (`on(EVENTS…)` e `send(EVENTS…)`) sono in tre file: `home.js` (18), `game.js` (10), `FriendsPanel.js` (8). Le richieste HTTP (`fetch`) sono 5, in home, tavolo, pannello amici, statistiche e suoni.

**Due stili di componenti.**

- **Componenti "puri"** (come vuole `CLAUDE.md`): ricevono dati e restituiscono elementi nuovi, senza cercare niente nella pagina. Sono quelli del tavolo: `Table`, `Hand`, `Card`, `Trick`, `Scoreboard`, `Timer`, `SingButtons`, `HandSummary`, `TablePhrases`, `Avatar`, `StatsPanel`.
- **Componenti "imperativi"**: costruiscono il loro pezzo una volta e poi lo **modificano a mano** (`querySelector`, `textContent`, `hidden`, `disabled`). Sono `ModeModal` (581 righe, 14 `textContent`), `FriendsPanel` (619), `ChatWindow`, `QueueOverlay`, `InviteDialog`, `Modal`, e `home.js` stesso.

**Dove sta lo stato.**

- Tavolo: in **variabili globali del modulo** `game.js`, circa 40 `let` e una dozzina di timer (`lastTrickTimer`, `summaryTimer`, `dealTimer`, `throwTimer`, `drawTimer`, `tickTimers`, …). A ogni vista e a ogni timer si chiama `render()`, che ricostruisce **tutto** il tavolo con `root.replaceChildren(Table(...))`.
- Home e pannelli: in parte in variabili dei moduli, in parte **nel DOM stesso** (quale input è selezionato, quale pulsante è spento, il testo del suggerimento).

## 2. Problemi concreti

1. **Ridisegno totale del tavolo e i suoi accorgimenti.** Siccome `render()` butta via e ricrea tutto, ogni cosa che "vive" nel DOM va salvata e rimessa a mano:
   - le immagini delle carte riusate per non lampeggiare (`reuseCardImages`, `REUSED_IMAGES`, `reusedImage`: P70, P119, P135);
   - ogni animazione riceve il tempo già passato come ritardo negativo, altrimenti ripartirebbe da capo (`animationDelay`, `shownFor`, `openFor`: P70, P110, P119, P130);
   - la carta sotto il mouse rifatta "già sollevata" (`keepHover`);
   - il fuoco della tastiera e lo scorrimento dell'elenco delle frasi rimessi dopo ogni ridisegno (P110);
   - il doppio tocco su iPhone ascoltato sull'elemento toccato, perché un ridisegno a metà tocco lo toglieva (P133).

   Molti bug della scaletta (P70, P97, P110, P112, P119, P130, P133) vengono da qui. Con React gli elementi che non cambiano **restano gli stessi**, e quasi tutti questi accorgimenti spariscono.
2. **`game.js` è troppo grande e fa troppe cose**: 1.087 righe con vista, momenti (presa chiusa, riepilogo, carte calate, canti), animazioni, timer del turno, suoni, frasi e consigli, tutto nelle stesse variabili globali. Per capire una funzione bisogna sapere quali di quelle 40 variabili tocca.
3. **Due stili diversi** (puri e imperativi): nei componenti imperativi lo stato è sparso tra variabili e DOM, e ogni cambiamento va scritto due volte (nel dato e nel testo della pagina).
4. **Nessun tipo.** La forma della vista (`game:state`: `you`, `players`, `hand`, `trick`, `legal`, `last_hand`, …) è scritta solo in `docs/CONTRATTO-SOCKET.md` e negli esempi di `app/static/dev/vista_*.json`. Un campo sbagliato si scopre solo nel browser.
5. **Costanti copiate in più posti**: le durate delle animazioni sono in `game.js`, nei CSS e in `room.py` (`THROW_MS`, `DRAW_MS`, `SHUFFLE_MS`…); `AVATAR_CODES` è sia in `Avatar.js` sia in `avatars.py`. Oggi le tengono allineate dei test. Con TypeScript il lato JS si può raccogliere in un file solo; il confronto con CSS e Python resta.

Non sono problemi: dipendenze circolari (non ce ne sono), ascolti Socket.IO sparsi (passano tutti da `socket.js`), rientro dopo una disconnessione (gestito: `game:join` a ogni ricollegamento, ordine dato da `version`).

## 3. Cosa NON va riscritto

- **Tutto il backend**: Flask, Socket.IO, servizi, repository, modelli, MySQL, e soprattutto il **motore di gioco** in Python. Il server resta l'unico che decide (regole, mosse valide, punti, rating).
- **Il contratto** `docs/CONTRATTO-SOCKET.md`: stessi eventi, stessi dati. I tipi TypeScript si scrivono **copiandolo**, non cambiandolo.
- **Il login di Flask**: restano Flask-Login (la sessione nel cookie), il CSRF di Flask-WTF e le pagine di errore. Cambia il modo di parlarci: le pagine React mandano JSON, con il codice CSRF in un'intestazione (sezione 6). Le pagine Jinja restano finché la loro pagina non è migrata.
- **`core/socket.js` come idea**: va solo tradotto in TypeScript con i tipi degli eventi; il comportamento (una connessione, `send` che non fallisce, avviso di connessione) resta uguale.
- **Il CSS** (`base/`, `components/`, `pages/`) e le **variabili** di `variables.css`: i componenti React usano le stesse classi.
- **Gli attributi `data-*`** e la struttura dell'HTML prodotto: i test nel browser li usano (sezione 7).
- **Immagini, suoni, font** e le loro licenze.

## 4. Piano di migrazione

**Stato (23/10/2026)**: fatti i passi 0–8 (avanzamento e commit in `REVIEW.md`, "Migrazione del frontend"). Dal 7d la home React è su `/` e quella Jinja resta su `/vecchia-home` (solo sviluppo e test); dall'8h `/game/<id>` è il tavolo React e quello Jinja resta su `?ui=jinja`; tutti e due fino al passo 9. Il passo 8 l'ha fatto Giuseppe (8a–8h, 20–23/10), con le suite del tavolo in modalità React e la prova su iPhone e Android di Christian (8g). Il prossimo è il **passo 9**: il piano è qui sotto, "Piano del passo 9", con le scelte da confermare prima del 9a.

Passi piccoli, ciascuno su un branch suo e reversibile. La vecchia interfaccia resta finché la nuova non la sostituisce del tutto, una pagina per volta. **La SPA e il proxy partono dal passo 1** (deciso il 19/10): così nessuna pagina si migra due volte (prima come isola, poi dentro la SPA) e non si scrive codice per le isole che poi andrebbe tolto. Tra una pagina della SPA e una pagina Jinja non ancora migrata si passa con un normale link, che ricarica la pagina.

| Passo | Cosa | Pronto quando |
|---|---|---|
| **0** | Questo documento; decisione in `DECISIONI.md`; sezione "React e TypeScript" in `regole-codice.md` | il gruppo è d'accordo |
| **1** | Cartella `frontend/` con Vite, React, TypeScript e React Router; la SPA con una sola pagina di prova; il **proxy** di Vite verso Flask (anche Socket.IO e le pagine Jinja); `npm run build` che scrive in `app/static/dist/`; Flask che serve `dist/index.html` per gli indirizzi della SPA (sezione 6) | da `localhost:5173` si vedono la pagina di prova e le pagine di adesso, con il login; dopo il build la pagina di prova la serve anche Flask; i test di adesso passano |
| **2** | `types/`: i tipi del contratto (Card, Suit, GameView, PlayerView, eventi dal server e verso il server) presi da `CONTRATTO-SOCKET.md` e controllati sugli esempi `app/static/dev/*.json` | gli esempi JSON passano il controllo dei tipi |
| **3** | `socket/`: `socket.js` tradotto in TypeScript con eventi tipizzati, più un hook React (`useSocketEvent`) che si iscrive e si toglie da solo | test unitari del modulo |
| **4** | Accesso e registrazione (la pagina più piccola) e la navbar di chi non ha fatto il login; rotte JSON per accesso e registrazione e il codice CSRF letto da una rotta, **già sotto `/api/`** | i test di `api/` e `frontend/` su quelle pagine passano |
| **5** | La cornice delle pagine con il login: navbar, pannello statistiche, pannello amici e chat (servono a tutte le pagine dopo); la rotta che dice chi è l'utente collegato. In tre lotti: **5a** navbar, statistiche e avviso di connessione; **5b** pannello amici; **5c** chat e suoni del menu. Fino al passo 6 la cornice si vedeva solo su `/prova-react` | test di `frontend2/` |
| **6** | Impostazioni del profilo, con le rotte `/api/profile/` (contratto 2.4); si toglie `/prova-react` (doveva sparire al passo 4, ma era l'unica pagina della SPA con il login) | i test di quella pagina passano |
| **7** | Home (carte-pulsante, `ModeModal`, coda, inviti). In quattro lotti: **7a** base, **7b** carta-modal, coda e CPU, **7c** inviti, **7d** `/` diventa la home React (la home Jinja su `/vecchia-home` fino al passo 9) | `test_spa_home*.py` (anche le misure di `test_pagina_home.py`), prove nel browser |
| **8** | Tavolo, prima **in parallelo** (per esempio su `/game/<id>?ui=react`), poi al posto di quello vecchio. Da qui home e tavolo stanno nella stessa SPA: entrando in partita la pagina non si ricarica (stesso collegamento Socket.IO, stesso audio). Nota del 20/10: al tavolo oggi non ci sono né navbar né pannello amici e chat, quindi "restano aperti" non vale: aggiungerli sarebbe una funzione nuova | tutte le suite `table*`, `sockets`, `e2e`, prova a mano su telefono |
| **9** | Tolti i file JS vecchi, i template Jinja delle pagine migrate (con `/vecchia-home` e il tavolo `?ui=jinja`) e i test che leggevano il loro testo (rifatti sul codice nuovo); le rotte JSON di oggi spostate sotto `/api/` (contratto, sezione 5); la SPA presa da una regola sola invece dell'elenco `SPA_PATHS` (sezione 6). In cinque lotti, **9a**–**9e** (vedi "Piano del passo 9") | giro completo delle suite |

Il tavolo è per ultimo perché è il più delicato (animazioni, tempi uguali al server, iPhone). Si può anticipare **una piccola prova isolata** (per esempio solo la mano e la presa con una vista finta di `app/static/dev/`), senza sostituire niente.

### Piano del passo 8 (20/10/2026)

Preparato da un sotto-agente in sola lettura (legenda: **[L]** letto nel codice, **[D]** dedotto, **[N]** non verificato); da riprendere con Christian prima dell'8a.

**Scelte già fatte da Christian (20/10)**: indirizzo **`/game/<id>?ui=react`** fino all'8h (tocca `app/blueprints/game/routes.py`: l'ok di Christian vale anche per Giuseppe, come ai passi 4 e 6); stato del tavolo in uno **"store" TypeScript** (`frontend/src/game/tableStore.ts`, quasi una traduzione 1:1 di `game.js`) letto da React con `useSyncExternalStore`, invece di `useReducer`; codice in **`frontend/src/game/`**, con **tutte le durate in `animations.ts`** (una per riga, `export const LAST_TRICK_MS: number = 1500;`, così i test le leggono con una regex).

**Da decidere all'8a**:
- `?ui=react` in tutti gli ambienti (consigliato: si prova dal telefono con `APP_ENV=demo`) o solo sviluppo e test;
- terza copia di `AVATAR_CODES` in TypeScript, controllata da `test_avatar.py` (consigliato), per l'avatar al tavolo (`SeatAvatar.tsx`: robot per la CPU, iniziale per un codice sconosciuto);
- interruttore **`TABLE_UI`** (`tests/table_ui.py`: `jinja` predefinito, `react` a mano), così i test del tavolo valgono per tutte e due le versioni senza raddoppiare le suite;
- `bypass` del proxy di Vite per servire `/game/...?ui=react` con l'aggiornamento al salvataggio [D];
- il blocco `declare module 'react'` delle variabili CSS spostato da `CardBackground.tsx` a `frontend/src/types/css.d.ts`.

**I lotti** (in fila: toccano gli stessi file):

| Lotto | Cosa | Test di riferimento (con `TABLE_UI=react`) |
|---|---|---|
| **8a** | Tavolo raggiungibile e disegnato "fermo" da una vista: `GamePage.tsx` (`page--game`, niente navbar, `ConnectionBanner`), viste finte `?demo=1v1` e `?demo=2v2` ed eventi `demo:state`; componenti `cards.ts`, `CardView.tsx`, `Hand.tsx`, `Trick.tsx`, `Table.tsx`, `Scoreboard.tsx`, `SingButtons.tsx`, `HandSummary.tsx`, `Timer.tsx`, `SeatAvatar.tsx`; `animations.ts` con tutte le durate; i 9 CSS del tavolo in `index.html` | nuovo confronto del DOM di `.table__inner` con il tavolo Jinja (più viste, 360×640, 390×844, 1280×720); `table3/test_grafica_tavolo.py`; `api/test_pagina_tavolo.py`, `test_csp.py`, `test_carte.py`, `test_avatar.py` |
| **8b** | Partita vera: `tableStore.ts` e `useTable.ts`; `game:join` a ogni collegamento, `game:state` per `version`, mosse con `version` e `waiting`, `game:replaced` (D14), `not_found` e ritorno alla home (P95), "Esci" con `Modal.tsx`, secondi che scendono, `preloadSounds`, `data-cards-ready` (P79) | `table6/test_partita_interrotta.py`, `table4/test_carte_pronte.py`, `api/test_rating_tavolo.py`, più una partita vera contro la CPU |
| **8c** | Momenti: presa chiusa, riepilogo (P58), canti, calata (P85), compagno e consiglio (P93, P123), punti della mano (P72) | `test_momenti_tavolo.py`, `test_calata.py`, `test_carte_compagno.py`, `test_punti_mano.py`, `test_presa_affiancata.py`, `test_tavolo_telefono.py` |
| **8d** | Lanci (P70, P78, P99, P107), presa che scivola via, pescate, `notifyAfter` con `TIMER_SLACK_MS` (P91) | `test_lancio_carta.py`, `test_carte_avversari.py`, `test_lancio_mio.py`, `test_animazioni_in_fila.py`, `test_timer_in_anticipo.py`, `test_niente_lampeggi.py` |
| **8e** | Distribuzione, mescolata, prima distribuzione (P118), anello del tempo in pausa (P132) | `test_distribuzione.py`, `test_prima_distribuzione.py`, `test_anello_tempo.py` |
| **8f** | Frasi (P56, P80, P110, P112, P130) e suoni (P103, P109); proposta: `scheduleSound` annullabile in `sounds.ts` | `test_frasi_pagina.py`, `test_frasi_senza_lampeggio.py`, `test_frasi_di_lato.py`, `test_suoni.py` |
| **8g** | Doppio tocco (P104, P133), regole di `page--game` (P69, P98), carta sotto il mouse (P97); suite `table*` intere in modalità React (da chiedere a Christian); **prova a mano su iPhone e Android** | `test_tocchi_tavolo.py`, `test_mano_ferma.py`, `test_grafica_tavolo.py`, `test_stile_tavolo.py`, `test_rifinitura.py`, `test_gira_telefono.py`, `test_hover.py` |
| **8h** | Il cambio: `/game/<id>` sempre SPA, `navigate()` dalla home al tavolo e ritorno **senza ricaricare**; `stop()` del tavolo ferma timer, ticchettio, suoni e ascolti; `TABLE_UI` predefinito `react`; il tavolo Jinja raggiungibile con `?ui=jinja` fino al passo 9 (consigliato) | i test toccati, `table*`, `sockets`, `e2e` (da autorizzare), prova sul telefono |

**Il pezzo di Giuseppe** (dopo il merge dell'8a, in parallelo con 8b e 8c): i confronti delle durate tra `room.py` e `animations.ts`. Oggi li fanno, con `game.js`, `sockets/test_turno.py::test_pause_uguali_a_quelle_della_pagina`, `table6/test_calata.py` e `table5/test_frasi_pagina.py`. Proposta: un file suo, `tests/sockets/test_durate_tavolo.py`, che fino al passo 9 controlla tutti e due i file. Da concordare con lui il nome del file e la forma delle righe.

**Rischi principali**:
- **Ritardi negativi** (P70, P119): in React un elemento che resta lo stesso continua la sua animazione da solo, e cambiare `animation-delay` a metà la sposterebbe [D]. Regola: lo store passa **quando** il momento è cominciato; il componente calcola il ritardo **una volta**, quando nasce (`useState`), e per far ripartire un'entrata si cambia la `key`.
- **Anello del tempo** (P132): una `key` per turno e pausa, perché cambiare `--timer-left` a metà lo fa saltare [D].
- **Immagini** (P70, P119, P135): React non sposta un `<img>` da un genitore a un altro; con le immagini già decodificate (P79) il lampo non dovrebbe vedersi [D]. Da provare anche sul telefono.
- **Misure al pixel**: il CSS è lo stesso, quindi contano gli spazi nel JSX e gli attributi in più (come `checked` nel 7b).
- **Quattro copie delle durate** fino al passo 9: `room.py`, `game.js`, `animations.ts`, CSS.
- **StrictMode** e uscita dal tavolo (dall'8h): `start` e `stop` dello store devono fermare tutto.
- **Tempo delle suite**: raddoppierebbe; per questo `TABLE_UI`, invece di girare sempre su tutte e due le versioni.
- **Buco già aperto**: `test_icone.py` non guarda il TSX (le icone del tavolo sono `logout`, `campaign`, `playing_cards`, `chat_bubble`, `smart_toy`).

**Com'è andata** (20–23/10, Giuseppe; dettagli in `giuseppe.md`): i lotti sono stati fatti nell'ordine. Scelte all'8a: le quattro raccomandazioni qui sopra, più il disegno delle frasi anticipato. Cambiamenti rispetto al piano: consiglio al compagno anticipato all'8b; `soundLater` dello store invece di `scheduleSound` in `sounds.ts` (8f); niente `keepHover` (8g: React tiene la stessa carta, che resta sollevata); evento nuovo **`home:refresh`** (8h, contratto 5.1), perché la home che ricompare senza ricaricare non riceve `home:status`.

### Piano del passo 9 (23/10/2026)

Preparato da Claude per Christian, leggendo il codice e i test (legenda: **[L]** letto, **[D]** dedotto). Si fa dal 24/10. **Prima del 9a si confermano le scelte qui sotto** e la lista dei file di ogni lotto.

**Cosa c'è oggi da togliere** [L]:

- **JavaScript vecchio**: 28 file in `app/static/js/` (circa 5.400 righe, più `vendor/socket.io.min.js`). Usati solo dal tavolo: `pages/game.js`, `components/Table.js`, `Hand.js`, `Trick.js`, `Scoreboard.js`, `Timer.js`, `SingButtons.js`, `HandSummary.js`, `TablePhrases.js`. Il resto (`home.js`, `core/*`, `utils/dom.js`, `Card.js`, `Avatar.js`, `Modal.js`, pannelli, carta-modal, …) lo usano la home e la cornice.
- **Template**: `game/table.html`, `main/index.html`, `partials/navbar.html`, `partials/avatar.html`, `partials/flash.html`, `partials/rotate_notice.html` (la SPA ha la sua copia in `frontend/index.html`); `base.html` serve ancora alle pagine di errore `errors/404.html` e `errors/500.html`.
- **Rotte con il ramo Jinja**: `/vecchia-home` (`main/routes.py`); `?ui=jinja` e `?ui=react` (`game/routes.py`).
- **Interruttori dei test**: `TABLE_UI` e `tests/table_ui.py`; `SPA_ONLY` di `test_tipi.py`; `GAME_TABLE` di `vite.config.ts` (l'eccezione per `?ui=jinja`).
- **Rotte JSON fuori da `/api/`**: `GET /online`, `GET /stats/me`, le 8 rotte `/friends/...` (contratto, sezione 2) e `POST /auth/logout` (un modulo, non JSON). Le chiamano `api/home.ts`, `api/friends.ts`, `StatsSheet.tsx`, `Navbar.tsx` (`data-friends-url`) e `api/client.ts` (commenti); sul server anche `JSON_PREFIXES` di `app/errors.py`.
- **Elenco `SPA_PATHS`** in `spa/routes.py` e in `vite.config.ts`, confrontati da `test_spa.py`; React non ha una pagina "non trovata".

**Test toccati** [L], in tre gruppi:

1. **Aprono `/vecchia-home` o il tavolo con `?ui=jinja`** (24 file): `api/test_pagina_home.py` (22 test, tutti sulla home Jinja), `test_amicizie.py`, `test_auth.py`, `test_avvio.py`, `test_impostazioni.py`, `test_online_senza_login.py`, `test_sicurezza.py`, `test_statistiche.py`; `frontend/test_base.py`, `test_chat_pannello.py`, `test_chat_vera.py`, `test_csp.py`, `test_icone.py`, `test_logo.py`, `test_navbar.py`, `test_rifinitura.py`, `test_spa_home_coda.py`; `frontend2/test_banner_connessione.py`, `test_inviti_2v2.py`, `test_invito_ricevuto.py`, `test_pannello_amici.py`, `test_spa_home.py`, `test_spa_home_inviti.py`, `test_suoni_menu.py`; i circa 30 file del tavolo che usano `table_path` (`table*`, più `api/test_pagina_tavolo.py`, `test_rating_tavolo.py`, `frontend/test_avatar.py`, `test_csp.py`, `test_rifinitura.py`, `frontend2/test_gira_telefono.py`).
2. **Leggono il testo dei file JS vecchi o li eseguono con Node** (circa 30 file): durate e nomi in `game.js` (`sockets/test_turno.py`, `test_durate_tavolo.py`, `table/test_animazioni_in_fila.py`, `test_carte_avversari.py`, `test_distribuzione.py`, `test_lancio_carta.py`, `table2/test_carte_compagno.py`, `test_lancio_mio.py`, `table5/test_frasi_pagina.py`, `test_momenti_tavolo.py`, `test_timer_in_anticipo.py`, `table6/test_calata.py`, `test_suoni.py`); `Card.js` e `Avatar.js` eseguiti con Node (`frontend/test_carte.py`, `test_avatar.py`); icone di `ModeModal.js` e dei template (`test_icone.py`); `alert` nel JS (`test_niente_alert.py`); colori e risorse esterne di `base.html` (`test_base.py`); `events.js` (`test_tipi.py`); `sounds.js` (`frontend2/test_spa_amici.py`, `test_suoni_menu.py`); limite della chat in `ChatWindow.js` (`test_spa_chat.py`).
3. **Confrontano la pagina React con quella Jinja** (DOM elemento per elemento): `test_spa_home.py`, `test_spa_home_coda.py` (`SIGNATURE`), `table2/test_tavolo_react.py`. Senza la pagina Jinja il confronto non si può più fare.

**Scelte da confermare** (raccomandazione per prima):

1. **I test della pagina vecchia**: per ogni file del gruppo 1 che prova il JavaScript vecchio, **si porta sulla pagina React** (stesso HTML e stessi `data-*`, quindi spesso basta l'indirizzo) se controlla qualcosa che i test `test_spa_*` non controllano già, altrimenti **si cancella**. All'inizio del 9b si scrive la tabella "file → portato / cancellato, perché". *Scartato*: cancellarli tutti, come diceva la decisione del 7d (si perderebbero, per esempio, la rete persa negli inviti di P83 e l'avviso di connessione di P33, se non hanno già un gemello React [D]).
2. **I confronti del DOM** (gruppo 3): **si tolgono** i test di confronto, tenendo gli altri controlli dei file; hanno servito a dimostrare che le pagine React sono uguali, e da qui in poi l'HTML lo controllano i test con i `data-*`. *Alternativa*: salvare l'albero di oggi in un file e confrontare con quello (ma ogni cambiamento voluto della pagina obbligherebbe a rifarlo).
3. **`Card.js` e `Avatar.js` con Node**: i test leggono **le costanti dei file TypeScript come testo** (come fa già `test_durate_tavolo.py`), senza eseguirli. *Alternativa*: compilarli con `tsc` per Node (più lento e una cosa in più da tenere).
4. **Vecchi indirizzi JSON**: dopo lo spostamento rispondono **404**, senza rimandi (li chiama solo la nostra pagina, che cambia nello stesso lotto). Con `POST /auth/logout` che diventa **`POST /api/auth/logout`** in JSON: con la regola unica (scelta 5) il proxy di Vite manda a Flask solo `/api`, `/static` e `/socket.io`, e un modulo verso `/auth/logout` non arriverebbe più a Flask.
5. **Regola unica della SPA** (già decisa il 19/10, sezione 6; da riconfermare): Flask risponde con la SPA per ogni indirizzo che non è `/api/`, `/static/` o `/socket.io`, e un indirizzo che non esiste lo mostra React con una pagina **"Pagina non trovata"** nuova (stesso testo di `errors/404.html`), con codice 200. Restano rotte Flask apposta solo dove il server controlla qualcosa prima di mandare la pagina: `/` (`?demo=rientro`), `/auth/login` e `/auth/register` (chi ha il login va alla home), `/profile/settings` e `/game/<id>` (login; codice della stanza e `?demo=`). *Alternativa*: tenere l'elenco degli indirizzi in Flask per rispondere 404 vero (ma l'elenco doppio è proprio ciò che si vuole togliere).
6. **Pagine di errore**: `errors/404.html` (per `/static/...` che non esiste) e `errors/500.html` restano Jinja, con un `base.html` ridotto (senza navbar, script e messaggi); `app/errors.py` risponde JSON per tutto `/api/`. Si tolgono i `partials/`.
7. **Dove stanno le rotte che restano**: **dove sono oggi** (meno file toccati, nessun conflitto con il lavoro di Giuseppe); il blueprint `game` resta con la sola rotta della pagina. *Alternativa*: spostarle tutte nel blueprint `spa` (come diceva la sezione 6, "`game` sparisce").
8. **Chi fa cosa**: come scritto in `REVIEW.md` (Christian il frontend e i test del frontend, Giuseppe le rotte e il giro completo); dal 20/10 Giuseppe può fare anche i lotti di Christian.

**I lotti** (in fila: toccano gli stessi file di test; ciascuno su un branch suo):

| Lotto | Cosa | Chi | Test da lanciare |
|---|---|---|---|
| **9a** | **Il tavolo vecchio**: via `game/table.html`, `pages/game.js` e i componenti solo del tavolo (vedi sopra); `game/routes.py` senza `?ui=` (un `?ui=` qualsiasi si ignora o 404: da decidere con la lista dei file); `tests/table_ui.py` e `TABLE_UI` tolti (`table_path` sostituito dall'indirizzo); `GAME_TABLE` di Vite senza l'eccezione `ui=jinja`; i test del gruppo 2 del tavolo leggono le durate da `animations.ts`; `test_durate_tavolo.py` senza `game.js` e `Trick.js`, con dentro i confronti di `test_turno.py`, `test_calata.py`, `test_frasi_pagina.py`; da `test_tavolo_react.py` tolto il confronto con il tavolo Jinja | Christian (rotta: Giuseppe, o Christian con il suo ok) | i file toccati; poi le sei suite `table*` intere (da chiedere a Christian) |
| **9b** | **La home e la cornice vecchie**: via `/vecchia-home`, `main/index.html`, i `partials/`, il resto di `app/static/js/` (con `vendor/`), `base.html` ridotto; i test del gruppo 1 portati o cancellati secondo la tabella (scelta 1); i confronti del DOM tolti (scelta 2); `test_carte.py`, `test_avatar.py` (scelta 3), `test_icone.py` (che finalmente guarda il TSX), `test_niente_alert.py`, `test_base.py` (risorse esterne in `frontend/index.html`), `test_navbar.py`, `test_logo.py` rifatti sul codice nuovo; `test_tipi.py` senza `SPA_ONLY`, con gli eventi confrontati con il contratto; via i confronti con `sounds.js` e `ChatWindow.js`; `api/test_pagina_home.py` cancellato o ridotto a ciò che resta vero (la home è della SPA) | Christian | i file toccati; `frontend` e `frontend2` intere (da chiedere: cambiano molti file) |
| **9c** | **Rotte JSON sotto `/api/`**: `/api/online`, `/api/stats/me`, `/api/friends/...`, `POST /api/auth/logout` (JSON); vecchi indirizzi 404 (scelta 4); `JSON_PREFIXES` = solo `/api/`; contratto (sezione 2, 5.1, 5.2) e tipi; le chiamate della SPA; i test di `api` ed `e2e` (`helpers.py`, `conftest.py`) | Giuseppe (le chiamate della SPA: Christian, o Giuseppe) | `api`, `e2e` |
| **9d** | **Regola unica**: Flask manda la SPA per ogni indirizzo fuori da `/api/`, `/static/`, `/socket.io` (scelta 5); pagina React "Pagina non trovata"; proxy di Vite ridotto a `/api`, `/static`, `/socket.io`; via `SPA_PATHS` dai due lati e `GAME_TABLE`; `test_spa.py` e `test_errori.py` rifatti | Christian (rotta: Giuseppe) | i file toccati, `api`, `e2e` |
| **9e** | **Giro completo** delle suite (con il tempo di ogni suite: con meno test qualche suite può essere unita), `ruff`, `tsc`, build; prova a mano su telefono e computer di tutto il giro (accesso, home, coda, CPU, inviti, tavolo, chat, impostazioni) | Giuseppe, con l'ok di Christian per il giro completo | tutte |

**Dopo il passo 9** (da chi è di turno sui documenti): in `CLAUDE.md` vanno riscritti lo "Stack" (niente più JavaScript vanilla), le convenzioni "Pagine" e "Dipendenze" (client Socket.IO da npm) e molti punti delicati che citano `game.js`, `home.js`, `FriendsPanel.js`, `Table.js`, `core/socket.js`, `base.html`; `docs/prototipo/LEGGIMI.md` (risorse esterne in `frontend/index.html`); il `README.md`. Per `main` si toglie `app/static/js/` alla prossima volta che si aggiorna.

**Rischi**:

- **Controlli persi**: è il rischio più grande. Nella tabella del 9b ogni test cancellato deve avere scritto **quale test React fa lo stesso controllo**; i numeri PASS scenderanno, ed è giusto, ma va detto di quanto e perché.
- **Indirizzi che non dicono più 404**: con la regola unica un link sbagliato dà la pagina React "non trovata" con codice 200; per i motori di ricerca (sito pubblico, D21) andrà eventualmente rivisto.
- **Login sulle pagine React senza rotta propria** (scelta 5): una pagina nuova che vuole il login ha bisogno della sua rotta Flask (come `/profile/settings`), altrimenti la regola unica la manda anche a chi non è collegato.
- **CSS non più usati**: classi che servivano solo al JavaScript vecchio possono restare nei CSS; non si toccano nel passo 9 (sarebbe un refactoring a parte, da proporre come punto nuovo).
- **Suite e tempi**: togliere tanti test può rendere qualche suite molto corta; la divisione si rivede solo dopo il 9e.

## 5. Architettura React proposta

```
frontend/
├── package.json         dipendenze a versione fissa (come requirements.txt)
├── index.html           l'unica pagina HTML della SPA
├── vite.config.ts       proxy verso Flask in sviluppo, uscita in ../app/static/dist/
├── tsconfig.json        TypeScript in modalità rigorosa
└── src/
    ├── main.tsx         avvia React e il router
    ├── routes.tsx       indirizzo → pagina (React Router); gli indirizzi non ancora migrati sono link normali
    ├── layout/          la cornice: navbar, pannello statistiche, pannello amici, avviso di connessione
    ├── types/           i tipi del contratto: card.ts, view.ts, events.ts, api.ts
    ├── socket/          client.ts (la connessione), events.ts (i nomi), hooks.ts (useSocketEvent, useConnection)
    ├── api/             le poche richieste HTTP (amici, statistiche), tipizzate
    ├── components/      componenti semplici e riusabili: Card, Avatar, Modal, Banner, Button
    ├── game/            il tavolo: Table, Hand, Trick, Scoreboard, Timer…
    │   ├── moments.ts   presa chiusa, riepilogo, carte calate, canti: oggi sparsi in game.js
    │   ├── animations.ts  le durate (un solo posto lato JS)
    │   └── useTable.ts  lo stato del tavolo (un reducer)
    ├── pages/           i pezzi di pagina più grandi: Home, ModeModal, FriendsPanel, Chat
    └── styles/          solo ciò che serve in più; il CSS di app/static/css si riusa
```

Regole:

- **Niente regole del gioco in React**: le carte giocabili sono `legal.play`, i canti `legal.sing`, la calata `legal.lay_down`. Come oggi.
- **I componenti non usano Socket.IO direttamente**: passano da `socket/` (hook o funzioni).
- **Stato del server e stato dell'interfaccia separati**: la vista ricevuta (`GameView`) non si modifica mai; quello che è solo della pagina (pannello aperto, carta sotto il dito, animazione in corso, momento mostrato) sta a parte.
- **Niente Redux né altre librerie di stato per cominciare**: bastano `useState`, `useReducer` e `Context`. Per il tavolo un reducer basta, perché lo stato oggi è già tutto in un posto (`game.js`). Una libreria piccola (Zustand) solo se servirà davvero.
- **Niente Next.js, Tailwind, librerie di componenti**: Flask fa già il server, il CSS c'è già.
- **Un collegamento Socket.IO per tutta la SPA**, aperto una volta: cambiando pagina dentro la SPA non si chiude.

## 6. Strategia Flask + Vite

**In produzione** (sul server online, e su ogni PC dove si prova il sito come in produzione): `npm run build` crea in `app/static/dist/` l'`index.html` della SPA e i suoi file, con un codice di versione nel nome (per esempio `index-3f9a1c.js`). Flask serve `index.html` per ogni indirizzo della SPA (un elenco in un posto solo, che cresce a ogni pagina migrata) e i suoi file come ogni altro file statico; gli altri indirizzi restano le rotte di adesso. Così:

- nel repository c'è solo il sorgente: il build si fa dove si installa, quindi Node serve anche lì (D54);
- la CSP resta `script-src 'self'`, come oggi;
- il nome con la versione evita che il browser usi una copia vecchia dopo un aggiornamento.

**In sviluppo**, con il **proxy** (deciso il 19/10): si accendono Flask (`python run.py`, porta 5000) e Vite (`npm run dev`, porta 5173), e si apre `http://localhost:5173`. Vite serve la SPA e la aggiorna a ogni salvataggio **senza ricaricare e senza perdere lo stato** (comodo sul tavolo: si cambia un'animazione senza rigiocare la partita); tutto il resto (rotte JSON, `/socket.io` anche come WebSocket, pagine Jinja, `/static`) lo gira a Flask. Il browser vede un solo indirizzo, quindi il cookie del login e il CSRF funzionano come in produzione. La CSP di Flask non vale per le pagine servite da Vite in sviluppo: si controlla sul build (`test_csp.py`).

**Login e CSRF nella SPA**: le pagine React mandano JSON alle rotte di Flask con il cookie della sessione (stesso indirizzo) e il codice CSRF nell'intestazione `X-CSRFToken`, che Flask-WTF accetta già; il codice si legge da una rotta (passo 4).

**Rotte JSON sotto `/api/`** (deciso il 19/10): ogni rotta che risponde con dati comincia con `/api/` (per esempio `/api/auth/login`, `/api/friends/`). Le nuove nascono così dal passo 4; quelle di oggi (`/friends/...`, `/stats/me`, `/online`) si spostano al passo 9, insieme al contratto (`CONTRATTO-SOCKET.md`, sezione 5) e alle pagine che le chiamano. A migrazione finita la regola è una sola: `/api/` sono dati, `/static/` file, `/socket.io` il tempo reale, **tutto il resto è la SPA** (Flask risponde con `index.html`, e un indirizzo che non esiste lo mostra React). Così il proxy di Vite diventa "gira a Flask `/api`, `/static` e `/socket.io`" e un indirizzo della SPA non può scontrarsi con una rotta di dati con lo stesso nome.

**I blueprint a migrazione finita**: restano solo l'API (gli ingressi sottili verso i services, come oggi). `main` tiene `/online` e la rotta "chi sono" del passo 5; `auth` e `profile` diventano solo JSON (i moduli di `auth/forms.py` restano per controllare i dati, anche arrivati in JSON); `stats` e `friends` restano; `game` sparisce (la partita è tutta Socket.IO e la pagina la fa la SPA); `spa` serve `index.html` per ogni indirizzo che non è API. Da `app/templates/` restano al massimo le pagine di errore per quando React non parte; `app/errors.py` risponde JSON per gli errori dell'API.

**Deciso** (D54, 19/10/2026, in `DECISIONI.md`): `app/static/dist/` **non** va nel repository, né in `dev` né in `main` (la esclude già la regola `dist/` di `.gitignore`); si compila con `npm run build` su ogni PC o server dove gira il sito.

Il client Socket.IO oggi è il file `vendor/socket.io.min.js` (versione 4.8.1); nel frontend nuovo si usa il pacchetto npm `socket.io-client` **alla stessa versione**.

## 7. Rischi

1. **Test che leggono il testo dei file JS**: 22 file di test (per esempio `test_icone.py`, `test_carte.py`, `test_avatar.py`, `test_navbar.py`, `test_suoni.py`, quelli delle animazioni in `table*`) aprono i `.js` e cercano nomi, durate o elenchi; 2 (`test_carte.py`, `test_avatar.py`) eseguono `Card.js` e `Avatar.js` con Node. Ogni pagina migrata deve portarsi dietro i suoi test, rifatti sul codice nuovo, **senza perdere controlli**.
2. **Test nel browser**: 53 file usano gli attributi `data-*` con Chrome (`tests/browser.py`). Se React produce lo stesso HTML con gli stessi `data-*`, restano validi così come sono: è la rete di sicurezza più grande della migrazione. Va rispettato.
3. **Animazioni e tempi del tavolo**: le durate devono restare uguali a quelle del server (`room.py`) e dei CSS. Con React alcuni accorgimenti spariscono, ma i momenti del tavolo (P57, P58, P69, P85, P93) vanno riportati uno per uno. In sviluppo React esegue due volte certi pezzi apposta (StrictMode): i timer vanno scritti in modo che si possano fermare.
4. **Telefono e iPhone**: zoom, doppio tocco, rotazione (P98, P104, P116, P133) vanno riprovati sul telefono vero a ogni pagina.
5. **CSP**: niente stili scritti nell'HTML (`style="..."`); React con `style={{...}}` imposta le proprietà dal JS (`element.style.x`), che la CSP permette, ma va controllato con `test_csp.py`.
6. **Node e npm** servono sul PC di tutti e tre (qui c'è Node 24.19 con npm 11.17) e, dato che `dist/` non va nel repository (D54), anche su ogni server dove si installa il sito.
7. **Regole del codice**: React e TypeScript si scrivono con forme che `regole-codice.md` oggi toglie (JSX, `.map` nelle liste, `useState` che restituisce due valori). Serve una sezione apposta prima del passo 1.
8. **File di altri**: Flask + Vite tocca `app/__init__.py`, le rotte che servono la SPA e le rotte JSON nuove (accesso, registrazione, utente collegato, codice CSRF), cioè il backend; la decisione su chi tocca cosa va presa con Giuseppe (Antonio è assente).
9. **Due interfacce insieme** per un po': ogni correzione fatta nella vecchia va rifatta nella nuova, finché quella pagina non è migrata. Conviene migrare una pagina per volta fino in fondo.
10. **Test nel browser sulle pagine della SPA**: il server dei test (porta 5099) serve la SPA da `app/static/dist/`, che non è nel repository (D54): prima dei test serve `npm run build`. Il runner deve farlo da sé o rifiutarsi di partire se manca (da decidere al passo 1).
11. **Tasto "indietro" e indirizzi**: nella SPA li gestisce React Router; il pannello amici oggi usa `history.pushState` per chiudersi con "indietro" (P46) e va rifatto con il router.

## 8. Per dopo: partite in memoria e Redis

Non si fa adesso. Da riprendere quando il sito va online (D21).

- **Com'è oggi**: le partite in corso, la coda, chi è online e gli inviti stanno nella memoria dell'unico processo (`app/realtime/`, `SocketIO(async_mode="threading")`, `use_reloader=False`). Se il processo si riavvia, le partite in corso si perdono: chi rientra riceve `not_found` e la pagina mostra "La partita è stata interrotta" (P95). Le partite finite sono salvate in MySQL (P26). Più processi o più server oggi **non funzionano**: ognuno avrebbe le sue stanze.
- **Possibili passi futuri**: Redis per presenza, coda e smistamento dei messaggi Socket.IO (`message_queue`); ogni partita assegnata sempre allo stesso processo; una copia dello stato della partita (o l'elenco delle mosse) per riprenderla dopo un riavvio. Redis da solo non basta per le partite, perché lock e timer delle stanze vivono dentro il processo.
- **Su Windows** Redis non ha una versione ufficiale: servono WSL, Docker o Memurai.

Andrà scritto un documento a parte, con le prove su cosa succede oggi in caso di riavvio.
