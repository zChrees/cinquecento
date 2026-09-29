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

### P70 (secondo lotto) — Carte degli avversari e pescata (29/09/2026)

- **Branch**: fix/p70-carte-avversari
- **File**: creato `tests/frontend/test_carte_avversari.py`; modificati `app/static/js/components/Hand.js`, `Table.js`, `app/static/js/pages/game.js`, `app/static/css/components/table.css`, `hand.css`, `tests/api/test_grafica_tavolo.py`
- **Controlli**: suite `frontend` 143 PASS (8 nuovi), suite `api` 274 PASS, `ruff check` pulito; tutte le suite non lanciate
- **Fatto**: (1) le carte coperte degli avversari non stanno più sotto il nome: sono un **ventaglio agganciato al bordo dello schermo** dal loro lato (`EdgeHand` di `Hand.js`, marcatore `data-edge-hand`), carte da 44 px (56 da 1024 px in su), aperto verso il centro; quello in alto esce per metà dal bordo alto, **dietro la barra** con "Esci" e il punteggio (la barra resta sopra e si tocca); ai lati sporge circa un terzo di carta e i giocatori ai lati si spostano di 14 px verso il centro, così il ventaglio non copre avatar e nome; (2) **pescata**: quando nella stessa mano il mazzo cala, pesca per primo chi ha preso e poi gli altri a turno (0,15 s l'uno dall'altro, 0,5 s ciascuno: `DRAW_MS`, `DRAW_STEP_MS` in `game.js`, uguali alle animazioni di `hand.css`, un test li confronta); nel ventaglio la carta nuova arriva dal centro del tavolo e le altre si allargano dal ventaglio di prima; la tua carta nuova scende nella mano dall'alto; (3) come per il lancio, i tempi passano al tavolo come ritardi delle animazioni (un ridisegno a metà non le fa ripartire) e con "riduci movimento" niente animazioni
- **Effetto in più**: sparito il difetto trovato in P71 (sui portatili bassi, nel 1v1, la presa entrava nel posto dell'avversario, perché le sue carte coperte stavano sotto il nome): tolta l'eccezione da `tests/api/test_grafica_tavolo.py`, che a 1280×720 ora passa; non va più in P34
- **Decisioni prese**: nessuna nuova (applicate quelle di Christian registrate nel primo lotto); scelte di Claude: ventagli ai lati che sporgono un terzo di carta e giocatori ai lati spostati di 14 px, carte degli avversari da 56 px da 1024 px in su
- **Domande nuove**: nessuna
- **Punti delicati**: i ventagli sono `position: fixed` rispetto allo schermo e stanno sotto la barra in alto grazie a `z-index` (`.table__top` 2, `.edge-hand` 0): chi aggiunge cose nella barra o ai bordi del tavolo deve tenerne conto. L'angolo di ogni carta del ventaglio viene da `--i` e `--n` (scritti da `Hand.js` con `style.setProperty`, ammesso dalla CSP). La pescata si riconosce dal mazzo che cala nella stessa mano (`noticeDraws` in `game.js`): a inizio mano non c'è, arriverà con la distribuzione (P70, terzo lotto)
- **Contratto di P65** (richiesta di Giuseppe): **ok di Christian** alla frase nuova del 5.2 (`friends:changed` a tutti e due gli utenti); ok anche a correggere in **P34** lo stesso scambio di risposte in `FriendsPanel.js` (vale solo l'ultima lettura di `GET /friends/`, come in `home.js`)
- **Cosa devono fare gli altri**: niente

### P70 (primo lotto) — Lancio della carta e carte bianche (29/09/2026)

- **Branch**: fix/p70-lancio-carta
- **File**: creato `tests/frontend/test_lancio_carta.py`; modificati `app/static/js/pages/game.js`, `app/static/js/components/Card.js`, `Trick.js`, `Table.js` (aggiunto all'elenco con l'ok di Christian), `app/static/css/components/trick.css`
- **Controlli**: suite `frontend` 135 PASS (7 nuovi), suite `api` 274 PASS, `ruff check` pulito; tutte le suite non lanciate
- **Fatto**: (1) **lancio**: ogni carta che arriva sul tavolo, compresa quella che chiude la presa o la mano, vola al suo posto dal lato di chi l'ha giocata, più grande e ruotata, girando leggermente su sé stessa (0,4 s, `THROW_MS` in `game.js` = `card-throw` in `trick.css`, un test li confronta); (2) finché una carta vola, un tocco sulle proprie carte non gioca niente (le carte non si spengono, per non farle lampeggiare a ogni carta degli altri); (3) **ridisegni**: la pagina si ricorda quando sono iniziati i lanci e la presa chiusa, e li passa al tavolo come ritardi delle animazioni: un ridisegno a metà (fumetto, timer, scollegato) non fa più ripartire né il lancio né l'uscita della presa chiusa, che prima ripartiva da capo; (4) **carte bianche** [D]: a ogni ridisegno le immagini delle carte erano elementi nuovi, che il telefono può mostrare vuoti (fondo bianco) per un fotogramma; ora `reuseCardImages(root)` di `Card.js` riusa le immagini già disegnate. La causa non si riproduce in Chrome sul PC: il test controlla che le immagini restino le stesse; **da riprovare sul telefono**; (5) con "riduci movimento" niente lancio e niente attesa
- **Decisioni prese** (per P70, di Christian): distribuzione a inizio mano **dopo il riepilogo**; carte dell'avversario in alto **dal bordo alto, dietro la barra** con "Esci" e il punteggio; carte degli avversari da circa **44 px**; la pescata animata vale **anche per sé**; P70 in tre lotti: lancio (questo), carte degli avversari, mescolata e distribuzione (da registrare in `DECISIONI.md`, Interfaccia)
- **Domande nuove**: nessuna
- **Punti delicati**: il tavolo si ridisegna tutto a ogni vista: un'animazione nuova deve ricevere da `game.js` il tempo già passato e usarlo come ritardo negativo (`animationDelay`), altrimenti riparte a ogni ridisegno; un'immagine di carta si crea solo con `Card`/`CardBack` di `Card.js`, che riusano quelle di prima (`reuseCardImages`, chiamata in `render` subito prima di `replaceChildren`). Nei test del browser "riduci movimento" è acceso (`tests/browser.py`): per provare un'animazione va spento (`Emulation.setEmulatedMedia`), e il suo avanzamento si legge con `getComputedTiming().progress`, non con `currentTime`
- **Cosa devono fare gli altri**: **Giuseppe**, ho controllato le tue modifiche di P59 a `ModeModal.js` e `QueueOverlay.js`: vanno bene. Un dettaglio: nel 2v2, se un amico ha già accettato e un altro poi rifiuta o scade, sotto la lista resta solo "L'invito a … è stato rifiutato" e sparisce "puoi giocare", anche se "Gioca" resta acceso: se ti va, dopo l'avviso rimetti `acceptedHint()` quando c'è almeno un amico che ha accettato

### P71 — Grafica del tavolo (29/09/2026)

- **Branch**: fix/p71-grafica-tavolo
- **File**: creato `tests/api/test_grafica_tavolo.py`; modificati `app/static/js/components/Trick.js`, `Table.js`, `app/static/css/components/trick.css`, `table.css`, `table-phrases.css`, `tests/api/test_pagina_tavolo.py`
- **Controlli**: suite `api` 274 PASS (6 nuovi), suite `frontend` 125 PASS, `ruff check` pulito; tutte le suite non lanciate (le lancia Christian quando lo chiede)
- **Fatto**: (1) via "Carte franche": prima del 40 accanto al mazzo non c'è niente; (2) il seme della briscola (la figura dell'Asso) sta al centro sopra il mazzo, senza nome (resta nell'etichetta per i lettori di schermo); a mazzo finito spariscono mazzo, seme e la scritta "Mazzo finito"; (3) sopra la mano, a sinistra, un tondo con il seme della briscola (dal 40 a fine mano, anche a mazzo finito; marcatore `data-trump-badge`); (4) via "mazziere"; (5) il pulsante delle frasi è sopra la mano a destra (riga `.table__me`: briscola, tu, frasi) e l'elenco si apre verso l'alto senza coprire la mano; (6) al telefono carte della presa da 48 a 60 px e mazzo da 40 a 56 px; il mazzo nel 1v1 sta sul bordo destro a metà tavolo, nel 2v2 nell'angolo in alto a destra (a metà c'è il giocatore di destra). Su tablet e computer la presa resta com'era e il mazzo passa da 52 a 60 px
- **Decisioni prese**: segno della briscola accanto alla mano = tondo con il seme a sinistra sopra la mano (scelta di Christian); mazzo del 2v2 al telefono nell'angolo in alto a destra (scelta di Claude: a metà a destra c'è il giocatore di destra); sul computer la presa non si ingrandisce (la richiesta era per il telefono, e più grande coprirebbe l'avversario sui portatili bassi) (da registrare in `DECISIONI.md`, Interfaccia)
- **Contratto di P59** (richiesta di Giuseppe): **ok di Christian** al campo `opponents` di `queue:status` e al nuovo 5.3 (2v2 con più amici); con l'ok di Giuseppe il cambiamento vale (regola del 29/09/2026)
- **Domande nuove**: nessuna
- **Punti delicati**: (a) **difetto già presente prima di P71**, trovato con il test nuovo: sui portatili bassi, nel 1v1, la presa entra nel posto dell'avversario (17 px a 1280×720, 33 px a 1366×657; misurato anche sul codice di prima [T]): da sistemare in **P34**; il test lo salta solo per 1280×720, con un commento; (b) il test nuovo sta nella suite `api` (come `test_pagina_tavolo.py` e `test_pagina_home.py`, che usano già il browser): nella suite `frontend` superava il limite di 120 s del runner (116 s senza, in questo giro); Giuseppe nel frattempo ha portato il limite a 240 s; (c) il commento in cima a `TablePhrases.js` dice ancora "pulsante in alto a destra": non l'ho toccato perché fuori dall'elenco del punto
- **Cosa devono fare gli altri**: niente

### P69 — Tocchi e clic al tavolo (29/09/2026)

- **Branch**: fix/p69-tocchi-tavolo
- **File**: creato `tests/frontend/test_tocchi_tavolo.py`; modificati `app/static/css/pages/game.css`, `app/static/js/pages/game.js`, `tests/frontend/test_momenti_tavolo.py`, `tests/frontend/test_frasi_pagina.py`
- **Controlli**: **1340 PASS** in 8 suite (6 nuovi nella suite `frontend`, 1 capovolto), `ruff check` pulito; il giro completo si lancia solo quando lo chiede Christian (29/09/2026)
- **Fatto**: (1) al tavolo il doppio tocco non ingrandisce (`touch-action: manipulation` su `:root:has(.page--game)`; lo zoom con due dita resta), tenendo premuto non si seleziona il testo e su iPhone non si apre l'anteprima delle immagini; le immagini del tavolo non ricevono il tocco (va al pulsante della carta: su Android niente menù "apri immagine"); (2) a fine mano, finché si vedono l'ultima presa della mano e il riepilogo, carte e canti sono spenti; "Ok" chiude il riepilogo e li riaccende; le prese in mezzo alla mano non spengono niente
- **Resta aperto**: (3) le **frasi del tavolo a raffica** non si riproducono: un test con clic veri del mouse a raffica sul pulsante spento e sulla frase conferma una sola frase per pausa (3 secondi) nella prova con dati finti, e il server ne rifiuta più di una ogni 3 secondi [L]. Da riprovare in una partita vera dal telefono annotando cosa si vede (fumetti che escono davvero anche dall'altra parte? elenco che si apre con il pulsante spento?)
- **Decisioni prese**: cambia la decisione di P57/P58 "la mano non si blocca mai" **solo a fine mano**: chi apre la mano nuova aspetta la fine dell'ultima presa e del riepilogo (fino a circa 6,5 secondi, meno con "Ok"), che il timer del server conta nei suoi 30 secondi (da registrare in `DECISIONI.md`, Interfaccia)
- **Domande nuove**: nessuna
- **Punti delicati**: le regole contro lo zoom stanno su `:root:has(.page--game)`, così valgono anche per le finestre aggiunte fuori da `<main>` (la conferma di "Esci"); una pagina nuova del tavolo deve tenere la classe `page--game`. In `game.js` le carte si spengono con `nextSummary || summary`: chi cambia i momenti di fine mano deve tenerne conto
- **Cosa devono fare gli altri**: niente

### Documenti: punti nuovi dalla prova sul telefono (29/09/2026)

- **Branch**: docs/punti-prova-telefono
- **File**: modificati `SCALETTA.md` (tracker, sezioni 3, 4, 9 e 9.2), `DECISIONI.md` (Progetto e tempi, Dati, Interfaccia, Gioco), `DA-DECIDERE.md` (D31, D43 e D44 nuove), `CLAUDE.md` (riga "Stato", paragrafo "Progetto")
- **Controlli**: nessuno (soli documenti); 1320 PASS dall'ultimo giro (P33)
- **Registrati**: nessun riepilogo nuovo di Giuseppe o di Antonio dopo l'ultimo aggiornamento
- **Tracker**: punti nuovi dalla prova a mano dal telefono (io e un amico, server sul mio PC in rete locale). **Giuseppe**: P63 (spazi prima o dopo il nome nella richiesta di amicizia), P64 (niente canto nella prima presa, regola nuova), P65 (amico bloccato, sbloccato e di nuovo amico che non compare online nella carta-pulsante), P66 (mossa automatica dei 30 secondi che non parte più dopo essere usciti dal browser e rientrati), P67 (punti della mano in corso nella vista, solo della propria squadra), P68 (CPU: mosse e stanza). **Christian**: P69 (tocchi e clic al tavolo: zoom sul telefono, carta giocata durante il riepilogo, frasi a raffica), P70 (animazioni: lancio, mescolata e distribuzione, carte degli avversari, carte bianche per un attimo), P71 (grafica: briscola sul mazzo, niente "Carte franche" né "mazziere", mazzo e carte più grandi, pulsante delle frasi sopra la mano), P72 (i propri punti sopra la mano), P73 (CPU nella home). Le correzioni del tavolo che erano dentro P34 ora sono P69–P72
- **Decisioni registrate**: partita contro la CPU nella prima versione; spazi attorno allo username tolti nella richiesta di amicizia; ritocchi del tavolo; niente canto nella prima presa di ogni mano
- **Domande nuove**: **D43** (CPU: strategia, 1v1 o 2v2, salvataggio e rating, posto nella home), **D44** (punti al tavolo: cosa resta del tabellone e del riepilogo di fine mano); D31 aggiornata (la CPU è il punto più grande da tagliare se manca tempo)
- **Da revisionare, Giuseppe**:
  - l'**ordine** dei tuoi punti in "Da dove si parte" è una mia proposta: prima i difetti (P66, P65, P63), poi P64, P59, P61, P67 e P68, e P38 e P39 l'ultimo giorno;
  - **P64**: ho inteso "primo giro" come la **prima presa di ogni mano**; se nel tuo riepilogo scrivi un dubbio, lo sistemiamo prima che parta il punto;
  - **P67** cambia il contratto 3.3 e gli esempi in `app/static/dev/`, che leggono anche i miei test del tavolo: il nome del campo lo fissiamo insieme; P72 parte dopo che P67 è in `dev`;
  - **P68** (CPU) aspetta D43, da decidere insieme; se serve salvare le partite con la CPU nel database, è una modifica di tabelle da discutere prima.

### Documenti: registrati i lotti del 29/09 (29/09/2026)

- **Branch**: docs/registra-29-09-christian
- **File**: modificati `SCALETTA.md` (tracker, sezioni 3, 4, 6, 9 e 9.2), `DECISIONI.md` (Progetto e tempi, Tecnologia, Dati, Sicurezza, Interfaccia, Gioco, Processo), `DA-DECIDERE.md`, `CLAUDE.md` (riga "Stato", "Regole git", "Convenzioni", punti delicati, "Testing"), `docs/CONTRATTO-SOCKET.md` (5.4: `cannot_write`, D41), questo file
- **Controlli**: nessuno (soli documenti); 1320 PASS dall'ultimo giro (P33)
- **Registrati**: di Christian i quattro riepiloghi del 29/09 (test del pannello amici dopo P48 con le decisioni del giorno, D40, pagina di P58, P33). Di Giuseppe e di Antonio niente di nuovo dopo l'ultimo aggiornamento (fermi a "Documenti: registrati P58, P31 e P32" e a P27)
- **Tracker**: spuntati **P33** e **P62** (punto nuovo: font delle icone nel progetto, D40); nota a P48 (test sistemati) e a P58 (pagina fatta); **P60 tolto** (barrato, anche in sezione 4, 9 e 9.2; tolto dalle dipendenze di P36); punto nuovo **P61** (regole della password, D8) proposto a Giuseppe, **da confermare con lui**; lista definitiva di P33 in 9.2; P38 si installa da `main`; P39 con ngrok e QR code; righe nuove in sezione 3 (`InviteDialog.js`, `auth/forms.py`) e 6 (`app/static/fonts/`); "Da dove si parte" riscritto
- **Decisioni registrate**: D1 in parte (cosa si consegna), D5, D8, D10, D20, D29, D40, D41, D42 chiuse; `main` come branch di produzione con i soli file del sito (sostituisce "portare `dev` in `main` non si propone"); contratto con Antonio assente (ok di Giuseppe e Christian); test solo delle suite toccate mentre si lavora, tutte prima del commit (e la seconda proposta abbandonata); P60 tolto; ultima presa della mano al tavolo (P58); le tre di P33. Le decisioni vecchie che cambiano hanno la nota "Aggiornata il 29/09/2026"
- **Domande**: restano aperte D1 (solo la data), D21 e D31; nessuna nuova
- **Punti delicati** (in `CLAUDE.md`): nuovi quelli di icone (P62), connessione (P33), test nel browser e tempo reale; aggiornati Home (P22: niente più font delle icone da 5,4 MB) e Momenti del tavolo (P57/P58)
- **Da revisionare, Giuseppe** (scelte fatte da me mentre ero di turno, che toccano anche te: se qualcosa non va, scrivilo nel tuo riepilogo):
  - **P61** (regole della password) è scritto come tuo, perché accesso e account sono passati a te: se non lo vuoi, dillo e lo prendo io o lo assegna chi è di turno;
  - in "Da dove si parte" il tuo ordine è: P59 (dopo il pull di P33), P61, `auth.js` se confermato, il blocco occasionale delle suite, P38 e P39 (da `main`, con ngrok e QR code);
  - nel contratto 5.4 ho scritto `cannot_write` (D41); l'esempio in `app/static/dev/amici_esempio.json` non lo ha ancora (non l'ho toccato: è un file che i test leggono, e con i soli documenti non si lanciano i test).

### P33 — Errori e connessione nell'interfaccia (29/09/2026)

- **Branch**: feature/p33-connessione
- **File** (lista definitiva per 9.2, confermata da me prima di cominciare; Giuseppe non stava lavorando a P59): creati `app/static/js/components/Banner.js`, `app/static/css/components/banner.css`, `tests/frontend/test_niente_alert.py` e, in più, `tests/frontend/test_banner_connessione.py`; modificati `app/static/js/core/socket.js`, `app/templates/base.html` (il CSS dell'avviso), `pages/game.js`, `pages/home.js`, `components/ModeModal.js`, `components/InviteDialog.js` (non era tra i probabili: i pulsanti dell'invito ricevuto), `components/FriendsPanel.js`, `components/ChatWindow.js`, `tests/frontend/test_base.py` (12 CSS in `base.html`, non più 11), questo file
- **Cosa cambia**:
  - **avviso in cima alla pagina** (sotto la navbar, sopra le finestre aperte grazie al *popover*), in ogni pagina che usa il tempo reale; lo decide `socket.js` dallo stato della connessione: "Connessione persa: riprovo a collegarmi…" mentre Socket.IO riprova (sparisce da solo al ritorno); "Sei stato scollegato (per esempio sei uscito da un'altra scheda): ricarica la pagina." con **Ricarica**, quando il server chiude e non si riprova (P32); "Non sei più collegato al tuo account: ricarica la pagina." se il login non vale più; al **primo collegamento** "Collegamento al server in corso…" solo dopo 3 secondi (così non lampeggia a ogni apertura). Lasciando la pagina (tavolo, "Esci") l'avviso non compare;
  - **pulsanti spenti senza connessione**, solo quelli del tempo reale: al tavolo carte, "Canta" e frasi; nella home "Gioca", "Invita" e "Accetta"/"Rifiuta" dell'invito ricevuto; nella chat "Invia". Quelli che usano HTTP (richieste di amicizia, statistiche, "Esci") restano attivi. I componenti continuano a non parlare con il server: la pagina li avvisa con `setModeModalOnline(online)`, `invite.setOnline(online)`, `setChatOnline(chat, online)`;
  - **al ritorno la pagina si aggiorna da sola**: il tavolo con `game:join` (c'era già); la home riceve `home:status` e, se si è ancora in coda, `queue:status`, e rilegge gli amici; il pannello amici rilegge la lista e la chat aperta riceve i messaggi arrivati nel frattempo;
  - al tavolo la riga di stato non scrive più "Connessione persa…": lo dice l'avviso.
- **Controlli**: **1320 PASS** in 8 suite (7 nuovi), `ruff check .` pulito, giro completo in 290 s. Test nuovi: `test_niente_alert.py` (3: niente `alert`/`confirm`/`prompt` nel JS, tranne `js/vendor/`, e nei template, senza contare i commenti; l'espressione stessa è provata) e `test_banner_connessione.py` (4, nel browser con il server e il database dei test: connessione persa e tornata nella home con la carta-modal aperta, chat con "Invia" spento e il messaggio arrivato nel frattempo, scollegamento deciso dal server con "Ricarica", primo collegamento lento). Con il codice di prima i 4 test nel browser falliscono [T]. **Non provati nel browser** [L]: carte e canti spenti al tavolo (serve una partita vera: la prova `?demo=` non si collega) e i pulsanti dell'invito ricevuto
- **Decisioni prese** (mie, 29/09/2026, sulla proposta di Claude; **chi è di turno le registra** in `DECISIONI.md`, Interfaccia):
  1. un solo avviso comune in cima alla pagina per la connessione, con i testi qui sopra; al primo collegamento solo dopo 3 secondi;
  2. senza connessione si spengono solo i pulsanti del tempo reale; quelli HTTP restano attivi;
  3. **quando la connessione cade la schermata di coda si chiude e un invito mandato si considera annullato**: il server fa uscire dalla coda e annulla gli inviti di chi chiude tutte le schede (P28, P47), e al ritorno non manda niente per dirlo; se si è ancora in coda (un'altra scheda aperta) `queue:status` al ritorno riapre la schermata. L'invito rimasto aperto sul server si annulla al ritorno con `invite:cancel`
- **Domande nuove**: nessuna
- **Punti delicati**:
  - `socket.js` ora importa `components/Banner.js` (come `core/layout.js` importa i pannelli): ogni pagina che chiama `connect()`, `on()` o `send()` ha l'avviso; il pannello amici si collega in ogni pagina con la navbar e il login, quindi l'avviso c'è anche nelle impostazioni;
  - un componente nuovo con pulsanti del tempo reale deve spegnerli senza connessione: la pagina lo avvisa con `onStatus` di `socket.js` (vedi home e pannello amici);
  - nei test la connessione "cade" bloccando nel browser le richieste a `/socket.io/` e chiudendo il collegamento dal server (`socketio.server.eio.disconnect`): così la pagina riprova da sola come dopo un calo di rete; `disconnect_user` invece è lo scollegamento deciso (niente nuovi tentativi)
- **Cosa devono fare gli altri**: **Giuseppe**: P33 tocca `home.js` e `ModeModal.js`, che P59 può toccare: fai il pull prima di cominciare P59; se aggiungi pulsanti del tempo reale (per esempio la scelta di più amici), spegnili con `setModeModalOnline`. **Chi è di turno sui documenti**: spuntare P33, lista definitiva in 9.2, le tre decisioni in `DECISIONI.md`, i punti delicati in `CLAUDE.md`

### P58 (pagina) — Ultima presa della mano al tavolo, e due test instabili (29/09/2026)

- **Branch**: feature/p58-ultima-presa-pagina
- **File**: modificati `app/static/js/pages/game.js` (mio, P21/P57), `tests/frontend/test_momenti_tavolo.py` (mio, P57), `tests/frontend/test_chat_pannello.py` e `tests/frontend/test_icone.py` (miei, di oggi: due test instabili, sotto), questo file (anche la nota sulla decisione 2 dei test nel riepilogo di D40)
- **Cosa cambia**: a fine mano la pagina mostra **prima l'ultima presa della mano** (da `last_hand.last_trick`, P58 di Giuseppe), al centro per 1,5 secondi come ogni altra presa, con "Prende *nome*"; **poi il riepilogo di fine mano** per 5 secondi o fino a "Ok". Se nel frattempo qualcuno gioca la prima carta della mano nuova, la presa sparisce e il riepilogo compare subito: la mano non si blocca mai. Se `last_hand` arrivasse senza `last_trick` (la forma di prima di P58), il riepilogo compare subito come prima. Fine partita, rientro nella pagina e prima vista non cambiano
- **Controlli**: **1313 PASS** in 8 suite (2 nuovi), `ruff check .` pulito, giro completo in 273 s. 2 test nuovi in `test_momenti_tavolo.py` (fine mano: prima la presa poi il riepilogo; carta nuova che apre subito il riepilogo), provati prima con il `game.js` vecchio: fallivano tutti e due [T]
- **Due test instabili, trovati e corretti** [T]:
  1. `test_chat_pannello.py::test_aprire_la_chat_azzera_i_non_letti` (mio, di stamattina) apriva la chat appena arrivava il contatore (HTTP), **senza aspettare il collegamento al tempo reale**: se il collegamento non era pronto `chat:history` non partiva e la chat non si apriva ("Tempo scaduto: apertura della chat", o 15 secondi di ritardo). Ora aspetta anche "1 online", come gli altri due test del file;
  2. `test_icone.py::test_icone_disegnate_nel_browser` (mio, D40) chiudeva Chrome e il server **mentre la home si stava ancora collegando** al tempo reale: a volte (1 volta su 5 con i due file insieme) il file dopo, `test_invito_ricevuto.py` di Giuseppe, non riusciva più a collegarsi e **la suite `frontend` si bloccava** fino al limite di 120 s del runner. Ora aspetta "1 online" prima di chiudere, come gli altri test della home: 8 giri su 8 senza blocchi, e la suite `frontend` due volte di fila 112 PASS. La causa esatta dentro il server non l'ho trovata [D]: resta vero che **un test che apre una pagina collegata al tempo reale deve aspettare il collegamento prima di chiudere**
- **Decisioni prese**: nessuna (il comportamento era già nella nota di P58: "le carte dell'ultima presa prima del riepilogo")
- **Domande nuove**: nessuna
- **Punti delicati**: in `game.js` il riepilogo che aspetta la fine dell'ultima presa sta in `nextSummary`; lo apre `hideLastTrick()`, chiamata sia dal timer sia dalla prima carta della presa nuova (`render`). Il punto delicato sui test del browser (aspettare il collegamento al tempo reale prima di chiudere) vale per ogni test nuovo che apre una pagina con la navbar e il login
- **Cosa devono fare gli altri**: **Giuseppe**: il blocco della suite `sockets` di stamattina (riepilogo "Correzione — Test del pannello amici") potrebbe avere la stessa origine, un collegamento lasciato a metà che blocca il server dopo [D]. **Chi è di turno sui documenti**: nota a P58 nel tracker (pagina fatta), il punto delicato qui sopra in `CLAUDE.md`

### D40 — Icone subito: font delle icone nel progetto (29/09/2026)

- **Branch**: feature/d40-icone
- **File**: creati `app/static/fonts/material-symbols-rounded.woff2` (6 KB), `app/static/fonts/icone.txt` (le 31 icone usate), `tests/frontend/test_icone.py`; modificati `app/templates/base.html` (tolta la riga di Google per le icone, aggiunto il `preload` del font), `app/static/css/base/typography.css` (`@font-face`), `docs/prototipo/LEGGIMI.md` (risorse esterne e sezione "Icone" con i passi per aggiungerne una), `tests/frontend/test_base.py` (solo un commento), questo file. Tutti miei; `app/__init__.py` (CSP) non serve toccarlo: `font-src 'self'` c'era già
- **Perché**: le icone arrivavano dopo qualche secondo (sul mio PC anche 20–45) perché il font di Google era quello completo, **5,4 MB** [T], con `display=block`: finché non arriva le icone sono invisibili. Con solo le icone usate e le varianti fisse (riempite, spessore 500, come già in `typography.css`) il file pesa **6 KB** [T]; sta nel progetto e `base.html` lo precarica, quindi arriva con la pagina e non dipende più da Google
- **Controlli**: **1311 PASS** in 8 suite (6 nuovi), `ruff check .` pulito, giro completo in 270 s. Effetto collaterale: `api` passa da circa 64 a 47 s e `frontend` da circa 82 a 73 s, perché i test nel browser non caricano più il font da 5,4 MB. Provato anche che un'icona non presente nel font viene misurata larga (390 px contro 30), cioè che il controllo nel browser se ne accorge
- **Decisioni prese** (mie, 29/09/2026; chiude D40): **opzione b**, font delle icone **nel progetto** invece che da Google Fonts con `icon_names` (la proposta scritta in D40): è l'unica che fa comparire le icone subito e funziona anche se alla demo Google è lento o bloccato. Quando serve un'icona nuova si aggiunge a `icone.txt` e si **riscarica** il font (passi in `LEGGIMI.md`, "Icone"). I font del testo (Fredoka, Nunito) restano da Google, con `display=swap` (si vede subito un font di riserva)
- **Decisioni del gruppo sui test** (29/09/2026, approvate da tutti, su Discord; **chi è di turno le registra**):
  1. **mentre si lavora a un punto si lanciano solo le suite toccate** (`python tests/esegui_tutti.py <suite>`), **tutte le suite solo prima del commit**. Cambia la regola "Testing" di `CLAUDE.md` ("per ogni lotto … esegui tutte le suite"): il giro completo resta obbligatorio prima dell'ok al commit;
  2. ~~**un solo Chrome per file di test**, con una scheda nuova per ogni test invece di un browser nuovo~~ — **provato e abbandonato lo stesso giorno** (scelta mia, nessun punto nuovo da registrare): la stima di partenza era sbagliata. Misurato [T]: avviare Chrome costa **0,3 s** (non 2–3 s) e i test che aprono il browser sono circa 28 (non 49); con un Chrome per file e una scheda in un contesto nuovo per ogni test la suite `frontend` passava da 73 a 70,5 s. Per 3 secondi non valeva la pena cambiare `tests/browser.py` e sette file di test: modifiche scartate, niente commit. I 2,5–3 s che si vedono all'inizio di ogni file sono il **primo caricamento della pagina** (server appena avviato, pagina, font), non l'avvio di Chrome; il resto del tempo sono attese vere dei test (riepilogo che si chiude dopo 5 s, pausa di 3 s tra le frasi) e la suite `sockets` (94 s). Da ora per risparmiare tempo vale la decisione 1
- **Domande nuove**: nessuna
- **Punti delicati**: `test_icone.py` trova le icone usate nei template (`<span class="icon">nome</span>`, anche i valori di un dizionario Jinja come in `flash.html`), nelle chiamate `icon('nome')` e `iconButton('nome')` del JS e in tre posti con il nome calcolato (`DYNAMIC_CALLS`: il pulsante "Invita" e le righe "In breve" di `ModeModal.js`, `MESSAGE_ICONS` di `home.js`); **una chiamata nuova con il nome in una variabile fa fallire il test** finché non la si aggiunge a `DYNAMIC_CALLS`. Il `preload` ha bisogno di `crossorigin` anche se il file è dello stesso sito (i font si scaricano sempre in quel modo; senza, il browser lo scaricherebbe due volte). Il prototipo (`docs/prototipo/`) chiede ancora le icone a Google: è un file a parte, non cambia
- **Cosa devono fare gli altri**: **Giuseppe**: se aggiungi un'icona (per esempio in P59), segui i passi di `LEGGIMI.md`, "Icone": il test te lo ricorda. **Chi è di turno sui documenti**: chiudere D40 in `DECISIONI.md` (Interfaccia) con l'opzione b; registrare la decisione 1 sui test (cambia "Testing" in `CLAUDE.md`; la 2 è stata abbandonata, niente punto nuovo); aggiungere `app/static/fonts/` alla mappa dei file (sezione 6 di `SCALETTA.md`) e un punto delicato in `CLAUDE.md` sulle icone

### Correzione — Test del pannello amici dopo P48, e decisioni del 29/09 (29/09/2026)

- **Branch**: fix/test-pannello-amici
- **File**: modificati `tests/frontend/test_pannello_amici.py` (mio, P46), `app/templates/partials/navbar.html` (mio, P40: tolto `data-chat-demo-url`, non più usato da P48); creato `tests/frontend/test_chat_pannello.py`; questo file. Lista confermata da me prima di cominciare; `test_chat_vera.py` di Giuseppe non è toccato
- **Cosa cambia**: `test_chat_di_prova_testo_come_testo` e la parte chat di `test_indietro_ed_esc_chiudono` provavano la chat finta di P46, tolta da P48: con la chat vera la finestra si apre solo con `chat:history` dal server, che legge MySQL, e quel file finge solo le rotte HTTP (per questo scadeva "apertura della chat"). In `test_pannello_amici.py` restano il pannello, "indietro" ed Esc sulla lista; i controlli della chat che nessun altro test faceva (campo visibile a 360×640, messaggio vuoto rifiutato, massimo 1000 caratteri, contatore dei non letti azzerato aprendo la chat, "indietro" dalla chat alla lista e poi chiusura) stanno nel file nuovo `test_chat_pannello.py`, con il server e il database dei test come `test_chat_vera.py` (vuole MySQL). Il testo con i tag lo prova già `test_chat_vera.py`
- **Controlli**: **1305 PASS** in 8 suite (3 nuovi, 1 tolto: `test_chat_di_prova_testo_come_testo`), `ruff check .` pulito; i 2 FAIL noti del pannello amici non ci sono più. **Attenzione**: nel giro completo la suite `sockets` ha passato i suoi 226 controlli ma poi **si è bloccata per 25 minuti** (il runner l'ha fermata a 1508 s, anche se il limite è 120 s), e nello stesso giro `test_fumetti_di_tutti_i_posti_a_360_px` (`test_frasi_pagina.py`) è fallito una volta. Rilanciate da sole con il runner: `sockets` 226 PASS in 94 s, `frontend` 104 PASS. Nessuno dei file del lotto riguarda il tempo reale [D]: sembra il blocco occasionale già visto da Antonio in P27
- **Decisioni prese** (mie, 29/09/2026; non sono di turno: **chi è di turno le registra** in `DECISIONI.md`, `DA-DECIDERE.md`, `SCALETTA.md` e `CLAUDE.md`):
  - **P60 tolto** dalla scaletta (va barrato come P41 e P54). Motivo: già da P21 e P22 il server accetta `?demo=` solo in sviluppo e nei test, e nella demo risponde 404 ([L] `blueprints/game/routes.py`, `main/routes.py`); nella demo vera i dati finti non si vedono già. Va tolto anche da P36 ("Dipende da") e dalla sezione 9;
  - **D1** (in parte): si consegnano **il repository, la dimostrazione dal vivo e una relazione scritta**; la relazione si fa alla fine. Resta aperta la data esatta;
  - **D5 chiusa**: non serve un piano B, tutto funziona con Python 3.14;
  - **D8 chiusa**: la password deve avere **almeno 8 caratteri, almeno una maiuscola, almeno un numero e almeno un simbolo**. "Simbolo" = un carattere che non è una lettera, un numero o uno spazio (per esempio `! ? @ # $ % & * - _ . , ; :`): va bene qualunque segno, così nessuno resta bloccato da un elenco troppo stretto. Serve un **punto nuovo** (modulo di registrazione in `auth/forms.py`, `config.py`, testo della pagina di registrazione, test di P16; vale solo per le password nuove). Accesso e account sono di Giuseppe da quando Antonio è fuori: chi è di turno lo assegna;
  - **D10 chiusa**: i backup si tengono **14 giorni** (il valore già in `config.py` non è più provvisorio);
  - **D20** (in parte): la demo gira sul **PC di Giuseppe**, con un **tunnel ngrok** e un **QR code** per collegarsi subito dal telefono (così provano anche i colleghi); se ngrok si rivela troppo complesso o lento da preparare, si usa la stessa rete Wi-Fi. Va aggiunto al lavoro di Giuseppe in P39 (e a `docs/DEMO.md`);
  - **`main` è il branch di produzione** (usato per la presentazione e per la demo): si lavora in `dev`, e quando `dev` è pronto si aggiorna `main` portandoci **solo quello che serve a far funzionare il sito**. **Non vanno in `main`**: `christian.md`, `giuseppe.md`, `antonio.md`, `SCALETTA.md`, `CLAUDE.md`, `DECISIONI.md`, `DA-DECIDERE.md`, `docs/archivio/`, `REVIEW.md` (l'elenco può cambiare). Chiunque chieda a Claude di aggiornare `main`: Claude porta solo quei file, chiede prima per quelli dubbi (per esempio `tests/`, `docs/`, `app/static/dev/`, `README.md`) e aspetta l'ok per ogni commit e push. Cambia la regola di `CLAUDE.md` "portare `dev` in `main` è una decisione dell'utente: non proporla" (la decisione ora c'è) e chiude la parte "da quale branch" di D20: **la demo si installa da `main`**;
  - **D21 e D31 restano aperte** (D21 è per un futuro lontano);
  - **D29 chiusa**: le immagini degli avatar le **genera Claude** in SVG (niente problemi di licenza); serve a P43;
  - **D40 chiusa**: si caricano da Google Fonts solo le icone usate (`icon_names`) con gli assi fissi; è un **punto nuovo mio**. Tocca `base.html`, `CSP_DIRECTIVES` se cambia l'indirizzo, `docs/prototipo/LEGGIMI.md` e un test che controlla che ogni icona usata sia nell'elenco;
  - **D41 approvata** da me (`cannot_write` in `chat:history`): l'ha proposta Giuseppe, quindi con la decisione qui sotto è approvata: chi è di turno la scrive nel contratto 5.4;
  - **contratto con Antonio assente**: finché Antonio è fuori dal progetto, un cambiamento al contratto vale con l'ok di **Giuseppe e mio** (vale per D41 e per il 5.3 di P59);
  - **D42 chiusa, opzione b**: i messaggi con un ex amico restano salvati ma si rivedono solo tornando amici; niente sezione "conversazioni passate". Va aggiornata la decisione del 27/09 sulla chat ("la conversazione resta visibile").
- **Domande nuove**: nessuna
- **Punti delicati**: nei test del browser, riaprire la **stessa pagina** con il pannello aperto vale come ricaricarla e la cronologia tiene lo stato del pannello (`friendsPanel: 'chat'`): con un browser unico per più test il secondo "indietro" non chiude il pannello. Per questo `test_chat_pannello.py` usa un browser nuovo per ogni test. [D] Può succedere anche a un utente che ricarica la pagina con la chat aperta: dopo il ricaricamento, aprire il pannello e fare due volte "indietro" non lo chiude (resta sulla lista). È un difetto piccolo di `FriendsPanel.js`: lo propongo come correzione da fare in P33 o P34
- **Cosa devono fare gli altri**: **Giuseppe**: guardare il blocco della suite `sockets` a fine giro e perché il limite di 120 s del runner non l'ha fermata subito (vedi "Controlli"); ngrok e QR code in P39 (vedi D20); la demo si installa da `main`, aggiornato solo con i file del sito; il punto nuovo per le password di D8, se te lo assegnano. **Chi è di turno sui documenti**: registrare tutte le decisioni qui sopra, barrare P60, aggiungere i punti nuovi (D8, D40), aggiornare la regola su `main` in `CLAUDE.md` e il numero dei controlli

### P42 — Logo vero e icona della scheda (28/09/2026)

- **Branch**: feature/p42-logo
- **File**: creati `app/static/img/favicon.svg`, `favicon-32.png`, `apple-touch-icon.png`, `tests/frontend/test_logo.py`; modificati `app/templates/base.html` (tre `<link>` per l'icona) e, fuori elenco, mio (P19), `tests/frontend/test_base.py` (si aspettava che i primi collegamenti della pagina fossero i CSS); questo file. `navbar.html` e `navbar.css` non sono cambiati
- **Controlli**: 1202 PASS in 7 suite (8 nuovi), `ruff check .` pulito. È anche il primo giro completo con P47 e P35 insieme: tutto PASS
- **Decisioni prese** (mie, sulle raccomandazioni di Claude):
  - **il logo della navbar resta quello di P40** (due carte vere che si girano, "Cinque**cento**" in Fredoka): è già alto 34 px sul telefono e 44 su computer, nitido, e porta alla home; niente scritta ridisegnata in SVG;
  - **icona della scheda**: una carta rossa (il dorso) dietro e una crema davanti con un denaro giallo, nei colori della palette; SVG per i browser moderni, PNG da 32 px per gli altri, PNG da 180 px su panno verde per la schermata Home di iPhone e Android. Le PNG le ha fatte Chrome dall'SVG (nessuno strumento nuovo nel progetto). Prima il browser chiedeva `/favicon.ico` e riceveva 404
- **Domande nuove**: nessuna
- **Punti delicati**: nei commenti dell'SVG non si scrive il doppio trattino (un nome di variabile CSS come `--red`): l'SVG diventa non valido e non si vede; lo controlla `test_logo.py`. Se cambia l'SVG, vanno rifatte le due PNG
- **Cosa devono fare gli altri**: **Chi è di turno sui documenti**: spuntare P42 e registrare le due decisioni in `DECISIONI.md` (Interfaccia). **Giuseppe**: niente

### Correzione — Test della home dopo P47 (28/09/2026)

- **Branch**: feature/p35-carte-vere (commit a parte, dopo il rebase su P47)
- **File**: modificato `tests/api/test_pagina_home.py`: tolti `test_invito_finto_poi_gioca_e_coda_con_il_compagno` e `test_con_un_amico_1v1_messaggio_di_prova`, che provavano l'invito finto della home (P22), sostituito da quello vero di P47; il flusso vero lo provano `tests/sockets/test_inviti.py` e `tests/frontend/test_invito_ricevuto.py` (proposta di Giuseppe, opzione "toglierli")
- **Controlli**: **suite non rilanciate** dopo il rebase su P47 e dopo questa modifica, per scelta di Christian; l'ultimo giro (P35, prima del rebase) era 1167 PASS. `ruff check` pulito sul file
- **Decisioni prese**: nessuna
- **Domande nuove**: nessuna
- **Cosa devono fare gli altri**: **Chi fa il prossimo punto**: lanciare tutte le suite prima di cominciare, perché dopo P47 e P35 insieme non sono state lanciate. **Chi è di turno sui documenti**: in `DECISIONI.md` (P22, "Home con dati finti") amici e inviti non sono più finti, come scrive Giuseppe in P47

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
