# Migrazione del frontend a React + TypeScript + Vite

Analisi del 19/10/2026, prima di toccare il codice. Decisione e motivo in `DECISIONI.md` (19/10/2026).

**In breve**: il frontend di oggi è già ordinato (un solo modulo per Socket.IO, componenti come funzioni, attributi `data-*` stabili, niente `innerHTML`). Il problema vero è uno: **il tavolo si ridisegna tutto a ogni vista**, e per non far lampeggiare immagini e animazioni `game.js` ha accumulato molti accorgimenti e una quarantina di variabili di stato. React risolve proprio questo. Il resto si migra per avere un solo stile e i tipi, non perché sia rotto. Si va **una pagina alla volta**, con React montato dentro le pagine Flask di adesso, e il tavolo per ultimo.

Termini usati qui sotto:

- **React**: una libreria in cui si descrive *come deve essere* la pagina dato uno stato; è lei a cambiare solo i pezzi del DOM che cambiano davvero.
- **TypeScript**: JavaScript con i tipi (come in C: `Card[]`, `number`), controllati prima di eseguire.
- **Vite**: il programma che trasforma TypeScript e React in JavaScript normale per il browser (il "compilatore" del frontend), e durante lo sviluppo ricarica la pagina da solo.
- **Isola React**: una pagina fatta da Flask (Jinja, come oggi) con dentro un `<div>` che React riempie. Il contrario di una SPA, dove tutto il sito è una sola pagina JavaScript.

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
- **Le pagine Jinja e il login di Flask**: React entra come isola dentro di loro (sezione 6). Restano CSRF, sessione, redirect e pagine di errore.
- **`core/socket.js` come idea**: va solo tradotto in TypeScript con i tipi degli eventi; il comportamento (una connessione, `send` che non fallisce, avviso di connessione) resta uguale.
- **Il CSS** (`base/`, `components/`, `pages/`) e le **variabili** di `variables.css`: i componenti React usano le stesse classi.
- **Gli attributi `data-*`** e la struttura dell'HTML prodotto: i test nel browser li usano (sezione 7).
- **Immagini, suoni, font** e le loro licenze.

## 4. Piano di migrazione

Passi piccoli, ciascuno su un branch suo e reversibile. La vecchia interfaccia resta finché la nuova non la sostituisce del tutto, una pagina per volta.

| Passo | Cosa | Pronto quando |
|---|---|---|
| **0** | Questo documento; decisione in `DECISIONI.md`; sezione "React e TypeScript" in `regole-codice.md` | il gruppo è d'accordo |
| **1** | Cartella `frontend/` con Vite, React, TypeScript; un componente di prova montato in una pagina di sviluppo; `npm run build` che scrive in `app/static/dist/`; Flask che legge il manifest di Vite (sezione 6) | la pagina di prova si vede, i test di adesso passano |
| **2** | `types/`: i tipi del contratto (Card, Suit, GameView, PlayerView, eventi dal server e verso il server) presi da `CONTRATTO-SOCKET.md` e controllati sugli esempi `app/static/dev/*.json` | gli esempi JSON passano il controllo dei tipi |
| **3** | `socket/`: `socket.js` tradotto in TypeScript con eventi tipizzati, più un hook React (`useSocketEvent`) che si iscrive e si toglie da solo | test unitari del modulo |
| **4** | Accesso e registrazione (la pagina più piccola) in React | i test di `api/` e `frontend/` su quelle pagine passano |
| **5** | Impostazioni del profilo | come sopra |
| **6** | Pannello statistiche, poi pannello amici e chat | test di `frontend2/` |
| **7** | Home (carte-pulsante, `ModeModal`, coda, inviti) | `test_pagina_home.py`, prove nel browser |
| **8** | Tavolo, prima **in parallelo** (per esempio su `/game/<id>?ui=react`), poi al posto di quello vecchio | tutte le suite `table*`, `sockets`, `e2e`, prova a mano su telefono |
| **9** | Tolti i file JS vecchi e i test che leggevano il loro testo (rifatti sul codice nuovo) | giro completo delle suite |

Il tavolo è per ultimo perché è il più delicato (animazioni, tempi uguali al server, iPhone). Si può anticipare **una piccola prova isolata** (per esempio solo la mano e la presa con una vista finta di `app/static/dev/`), senza sostituire niente.

## 5. Architettura React proposta

```
frontend/
├── package.json         dipendenze a versione fissa (come requirements.txt)
├── vite.config.ts       una "entrata" per pagina, uscita in ../app/static/dist/
├── tsconfig.json        TypeScript in modalità rigorosa
└── src/
    ├── entries/         un file per pagina Flask: monta React nel <div> della pagina
    │   ├── auth.tsx, profile.tsx, home.tsx, game.tsx, layout.tsx
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

## 6. Strategia Flask + Vite

**In produzione** (e sul PC della demo): `npm run build` crea i file in `app/static/dist/` più un `manifest.json` (l'elenco "pagina → file con nome e codice di versione", per esempio `home-3f9a1c.js`). Una piccola funzione di Flask, usata nei template, legge il manifest e scrive il `<script>` giusto. Flask serve quei file come ogni altro file statico. Così:

- non serve Node sul server, se il build si fa prima;
- la CSP resta `script-src 'self'`, come oggi;
- il nome con la versione evita che il browser usi una copia vecchia dopo un aggiornamento.

**In sviluppo**, due modi:

1. **`vite build --watch`** (consigliato all'inizio): Vite ricompila i file in `app/static/dist/` a ogni salvataggio, Flask li serve come in produzione. Niente CSP da cambiare, un solo indirizzo, si ricarica la pagina a mano.
2. **Server di sviluppo di Vite** (più avanti, se serve): ricarica istantanea dei componenti, ma la pagina di Flask deve caricare gli script da `http://localhost:5173` e la CSP di sviluppo deve permetterlo (solo con `APP_ENV=development`).

**Da decidere** (D54 in `DA-DECIDERE.md`): se `app/static/dist/` va nel repository (e quindi in `main`, così la demo non ha bisogno di Node) o se si compila dove si installa (la demo vuole Node). Per una demo semplice conviene il primo; per il sito online di solito il secondo.

Il client Socket.IO oggi è il file `vendor/socket.io.min.js` (versione 4.8.1); nel frontend nuovo si usa il pacchetto npm `socket.io-client` **alla stessa versione**.

## 7. Rischi

1. **Test che leggono il testo dei file JS**: 22 file di test (per esempio `test_icone.py`, `test_carte.py`, `test_avatar.py`, `test_navbar.py`, `test_suoni.py`, quelli delle animazioni in `table*`) aprono i `.js` e cercano nomi, durate o elenchi; 2 (`test_carte.py`, `test_avatar.py`) eseguono `Card.js` e `Avatar.js` con Node. Ogni pagina migrata deve portarsi dietro i suoi test, rifatti sul codice nuovo, **senza perdere controlli**.
2. **Test nel browser**: 53 file usano gli attributi `data-*` con Chrome (`tests/browser.py`). Se React produce lo stesso HTML con gli stessi `data-*`, restano validi così come sono: è la rete di sicurezza più grande della migrazione. Va rispettato.
3. **Animazioni e tempi del tavolo**: le durate devono restare uguali a quelle del server (`room.py`) e dei CSS. Con React alcuni accorgimenti spariscono, ma i momenti del tavolo (P57, P58, P69, P85, P93) vanno riportati uno per uno. In sviluppo React esegue due volte certi pezzi apposta (StrictMode): i timer vanno scritti in modo che si possano fermare.
4. **Telefono e iPhone**: zoom, doppio tocco, rotazione (P98, P104, P116, P133) vanno riprovati sul telefono vero a ogni pagina.
5. **CSP**: niente stili scritti nell'HTML (`style="..."`); React con `style={{...}}` imposta le proprietà dal JS (`element.style.x`), che la CSP permette, ma va controllato con `test_csp.py`.
6. **Node e npm** servono sul PC di tutti e tre (qui c'è Node 24.19 con npm 11.17) e, se `dist/` non va nel repository, anche dove si installa la demo.
7. **Regole del codice**: React e TypeScript si scrivono con forme che `regole-codice.md` oggi toglie (JSX, `.map` nelle liste, `useState` che restituisce due valori). Serve una sezione apposta prima del passo 1.
8. **File di altri**: Flask + Vite tocca `app/__init__.py` e la funzione per i template (backend), e i template; la decisione su chi tocca cosa va presa con Giuseppe e Antonio.
9. **Due interfacce insieme** per un po': ogni correzione fatta nella vecchia va rifatta nella nuova, finché quella pagina non è migrata. Conviene migrare una pagina per volta fino in fondo.

## 8. Per dopo: partite in memoria e Redis

Non si fa adesso. Da riprendere quando il sito va online (D21).

- **Com'è oggi**: le partite in corso, la coda, chi è online e gli inviti stanno nella memoria dell'unico processo (`app/realtime/`, `SocketIO(async_mode="threading")`, `use_reloader=False`). Se il processo si riavvia, le partite in corso si perdono: chi rientra riceve `not_found` e la pagina mostra "La partita è stata interrotta" (P95). Le partite finite sono salvate in MySQL (P26). Più processi o più server oggi **non funzionano**: ognuno avrebbe le sue stanze.
- **Possibili passi futuri**: Redis per presenza, coda e smistamento dei messaggi Socket.IO (`message_queue`); ogni partita assegnata sempre allo stesso processo; una copia dello stato della partita (o l'elenco delle mosse) per riprenderla dopo un riavvio. Redis da solo non basta per le partite, perché lock e timer delle stanze vivono dentro il processo.
- **Su Windows** Redis non ha una versione ufficiale: servono WSL, Docker o Memurai.

Andrà scritto un documento a parte, con le prove su cosa succede oggi in caso di riavvio.
