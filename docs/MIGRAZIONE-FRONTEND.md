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

**Stato (20/10/2026)**: fatti i passi 0–7 (avanzamento e commit in `REVIEW.md`, "Migrazione del frontend"): dal 7d la home React è su `/` e quella Jinja resta su `/vecchia-home` (solo sviluppo e test) fino al passo 9. Il prossimo è il **passo 8** (tavolo): il piano è qui sotto, "Piano del passo 8", con le scelte già fatte e quelle da fare all'8a.

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
| **9** | Tolti i file JS vecchi, i template Jinja delle pagine migrate (con `/vecchia-home`) e i test che leggevano il loro testo (rifatti sul codice nuovo); le rotte JSON di oggi spostate sotto `/api/` (contratto, sezione 5); la SPA presa da una regola sola invece dell'elenco `SPA_PATHS` (sezione 6) | giro completo delle suite |

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
