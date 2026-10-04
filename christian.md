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

### P103 — Suoni al tavolo (05/10/2026)

- **Branch**: feature/p103-suoni (fatto da Claude, con il permesso di Christian per commit, merge e push dei punti P85–P103)
- **File** (lista definitiva per 9.2): creati `app/static/js/core/sounds.js`, `tests/table/test_suoni.py`; modificati `app/static/js/pages/game.js`, `app/templates/profile/settings.html`, `app/static/js/pages/profile.js`, `app/static/css/pages/profile.css`, questo file. **Nessun file audio** e **CSP invariata** (`app/__init__.py` di Giuseppe non è toccato)
- **Cosa cambia** (scelte di Christian del 04/10): suoni **creati nel browser con Web Audio** (al posto dei file audio della scheda: niente file, niente licenze, niente `media-src`); `sounds.js` pesa **7,5 kB**. Momenti: **mescolata** (scatti a raffica per 0,6 s) e un fruscio per **ogni carta distribuita**; **lancio** (fruscio e, a fine volo, la carta che si posa: 0,55 s per la tua, 0,4 per le altre, in fila come le animazioni di P78); **pescata** (una per giocatore, in fila); **presa** raccolta quando le carte scivolano verso chi ha preso (1,1 s); **canto** (tre note in salita); **calata**; **tocca a te** (un rintocco) quando il tavolo ha finito le pause (lanci, pescate, ultima presa, calata, riepilogo, distribuzione), cioè quando il server fa partire i 15 s (P94), e non dopo un tuo canto; **tempo che scade**: 4 tic e un ultimo tic più acuto negli ultimi 5 s del tuo turno; **fine mano** quando si apre il riepilogo; **fine partita** quando compare il riquadro, diverso per vittoria (arpeggio in salita), sconfitta (in discesa) e pareggio. Con "riduci movimento" niente animazioni, ma il lancio e la pescata suonano lo stesso, subito. **Interruttore** "Suoni al tavolo" (`role="switch"`) nella pagina delle impostazioni, sezione "Suoni": la scelta si salva subito **nel browser** (`localStorage`, chiave `cinquecento.sounds`), all'inizio sono **accesi**. Se il browser blocca l'audio (prima di un tocco nella pagina) o non ha Web Audio, non suona niente e il tavolo funziona; al primo tocco o tasto l'audio riparte
- **Scelte di Claude**: i suoni (note e fruscii), volume generale 0,35; "tocca a te" e ticchettio partono dalla fine delle pause; un evento `cinquecento:sound` sul documento a ogni suono, per i test
- **Controlli**: `tests/table/test_suoni.py` **11 PASS**, 2 giri su 2 (nessun file audio; presa chiusa da te: lancio subito, pescate a 0,55 s e 0,5 s dopo, presa a 1,1 s, tocca a te a pause finite, 4 tic più l'ultimo a un secondo l'uno dall'altro; un canto non ripete "tocca a te"; fine mano, poi mescolata e una distribuzione per carta; calata; vittoria, sconfitta e pareggio; spenti anche dopo aver ricaricato: nessun suono; senza Web Audio il tavolo va avanti; interruttore acceso all'inizio, salva "off" e "on" e si ricorda); rilanciati `test_csp.py`, `test_base.py`, `test_niente_alert.py`, `test_icone.py`, `test_impostazioni.py`, `test_lancio_carta.py`, `test_lancio_mio.py`, `test_animazioni_in_fila.py`, `test_carte_avversari.py`, `test_momenti_tavolo.py`, `test_distribuzione.py`, `test_calata.py`, `test_timer_in_anticipo.py`, `test_mano_ferma.py`: **120 PASS**. `ruff check .` pulito. Il suono vero non si può ascoltare nei test: va provato a mano (telefono e computer)
- **Decisioni prese**: suoni sintetizzati invece dei file (scelta di Christian, cambia la scheda di P103)
- **Domande nuove**: nessuna
- **Punti delicati**: (1) se il riepilogo si chiude prima con "Ok", "tocca a te" e il ticchettio partono prima del conto del server (che aspetta i 5 s del riepilogo, P94): il ticchettio può anticipare fino a 5 s; lo stesso vale per l'anello del tempo; (2) un suono nuovo va in `SYNTHS` di `sounds.js` (un nome sconosciuto dà errore); (3) `TRICK_AWAY_MS` in `game.js` deve restare uguale ad `AWAY_DELAY_MS` di `Trick.js` (1,1 s)
- **Cosa devono fare gli altri**: **Giuseppe**: niente (la CSP non cambia). **Chi è di turno sui documenti**: spuntare P103, lista definitiva in 9.2; in `DECISIONI.md` "suoni sintetizzati, nessun file" (cambia la scheda, che parlava di file audio con licenza); in `CLAUDE.md` un punto delicato per i suoni (evento `cinquecento:sound`, `TRICK_AWAY_MS`)

### P101 — Frasi del tavolo sul telefono aperte sopra le proprie carte (05/10/2026)

- **Branch**: feature/p101-frasi-telefono (fatto da Claude, con il permesso di Christian per commit, merge e push dei punti P85–P103)
- **File** (lista definitiva per 9.2): modificati `app/static/js/components/Table.js` (l'elenco è figlio di `.table__mine`, non più della tua riga), `app/static/css/components/table.css` (`.table__mine` con `position: relative` a ogni misura), `table-phrases.css`, `tests/table/test_frasi_pagina.py`, `tests/api/test_grafica_tavolo.py`, questo file
- **Cosa cambia**: **sul telefono** (sotto 640 px) l'elenco delle frasi aperto copre **solo la zona delle tue carte**: dalla fine della tua riga (avatar, punti, pulsante "Frasi", che restano visibili per richiuderlo) fino in fondo, cioè pulsanti "Canta" e mano; presa, mazzo, avversari e compagno restano visibili. Le frasi che non ci stanno **scorrono** dentro l'elenco (a 360×640 circa 4 righe nel 1v1, 3 nel 2v2 quando non ci sono pulsanti "Canta"). **Sul tablet** l'elenco si apre come prima, sopra la tua riga (posizione misurata uguale a prima); **da computer** resta il pannello di lato (P80), uguale
- **Scelte di Claude**: la zona coperta comincia sotto la tua riga (così il pulsante per richiudere resta visibile); "telefono" = sotto 640 px, come gli altri stili del telefono
- **Controlli**: `test_grafica_tavolo.py` nuovi `test_sul_telefono_le_frasi_sopra_le_tue_carte` (1v1 e 2v2 a 360×640 e 390×844: l'elenco va dalla tua riga al fondo, non copre presa, mazzo, ventaglio e giocatori, scorre, la pagina non scorre) e `test_sul_tablet_elenco_delle_frasi_verso_l_alto`; `test_frasi_pagina.py` aggiornato (l'elenco al telefono può coprire la mano; nei tocchi rapidi la frase si porta in vista prima del clic); con `test_frasi_di_lato.py`, `test_tavolo_telefono.py`, `test_calata.py`, `test_carte_compagno.py`: **89 PASS**. `ruff check .` pulito. Guardato con gli screenshot a 360×640 (1v1 e 2v2), 390×844, 768×1024
- **Decisioni prese**: nessuna oltre a quella del 04/10
- **Domande nuove**: nessuna
- **Punti delicati**: sul telefono l'elenco usa la griglia di `.table__mine` (`grid-row: 2`, fine "auto" = fondo della griglia): la tua riga deve restare la **prima** riga di `.table__mine`; sul tablet il bordo destro si allinea alla tua riga, larga al massimo 560 px (`max-width` di `.table__me`): se cambia, va cambiato anche in `table-phrases.css`
- **Cosa devono fare gli altri**: **Chi è di turno sui documenti**: spuntare P101, lista definitiva in 9.2

### P100 e P102 — Mazzo del 1v1 e indicatore della briscola (05/10/2026)

- **Branch**: feature/p100-p102-mazzo-briscola (fatto da Claude, con il permesso di Christian per commit, merge e push dei punti P85–P103)
- **File** (lista definitiva per 9.2): modificati `app/static/js/components/Trick.js` (`TrumpBadge`, `EmptyDeck` senza seme), `components/Table.js` (`.table__corner` con tondo e tabellone), `app/static/css/components/table.css` (angolo, tondo, mazzo del 1v1 da computer, `--mine-card-max`), `trick.css` (mazzo del 1v1 da 64 px sul telefono), `scoreboard.css` (fisso è l'angolo, non più il tabellone), `tests/api/test_grafica_tavolo.py`, `test_pagina_tavolo.py`, `test_frasi_di_lato.py`, `tests/table/test_carte_avversari.py` (correzione di P99, sotto), questo file. Nessuna icona nuova (il seme è l'immagine del mazzo)
- **P100** (mazzo del 1v1): **da computer** il mazzo esce dalla fila della presa e sta **sopra la pillola "Frasi"**, con il centro sulla sua verticale (misurato: scarto 0 px a 1024×768, 1280×720, 1440×900), alla stessa altezza della presa; la presa va **al centro**, sotto il ventaglio dell'avversario (prima era circa 55 px a sinistra). **Sul telefono** il mazzo del 1v1 è da **64 px** (prima 56). Nel 2v2 non cambia niente. La posizione si calcola da metà mano (`--mine-card-max`, ora su `.table__inner`, la stessa misura delle carte della mano), lo spazio tra le colonne (20 px) e metà pillola (circa 47 px)
- **P102** (briscola): un **tondo da 52 px** di vetro scuro (come "Esci"), con il seme su un disco chiaro come sopra il mazzo, **solo quando c'è la briscola**: sul telefono e sul tablet in alto a destra, simmetrico a "Esci" (stessa distanza dal bordo, stesso centro in altezza; non fa crescere la riga); da computer a **sinistra del tabellone**, 12 px prima, centrato con lui. Per i lettori di schermo "Briscola: coppe". **A mazzo finito** il seme sopra il mazzo **sparisce** (cambia P77): resta il tondo e, al posto del mazzo, uno **spazio vuoto** della stessa misura (nascosto ai lettori di schermo); presa e tondo non si spostano. Il seme sopra il mazzo, finché c'è il mazzo, resta
- **Scelte di Christian** (05/10): presa al centro; mazzo da 64 px sul telefono; tondo da 52 px; da computer nel 1v1 il **pannello delle frasi aperto copre il mazzo** (P80 lo apre sul bordo destro, proprio dove ora sta il mazzo): solo finché il pannello è aperto, la briscola resta nel tondo
- **Correzione di P99**: `tests/table/test_carte_avversari.py` aspettava ancora 0,4 s per il lancio del 7 di Mario prima della pescata: ora 0,55 s (e il test del ridisegno a metà pescata aspetta 1,3 s invece di 1,15). Nei controlli di P99 non l'avevo lanciato: in `dev` è rimasto rotto da P99 fino a questo punto
- **Controlli**: `test_grafica_tavolo.py` e `test_pagina_tavolo.py` **46 PASS** (nuovi: mazzo del 1v1 da computer sotto "Frasi" a 4 misure senza toccare presa, ventaglio, avversario, tabellone e tondo; tondo a sinistra del tabellone nel 1v1 e nel 2v2 a 3 misure; nel 2v2 il mazzo resta da 56 px; aggiornati: tondo simmetrico a "Esci" al telefono, mazzo finito con spazio vuoto e tondo a 360×640 e 1280×720); `test_frasi_di_lato.py` 7 PASS; `test_carte_avversari.py` 8 PASS; rilanciati `test_tavolo_telefono.py`, `test_stile_tavolo.py`, `test_rating_tavolo.py`, `test_presa_affiancata.py`, `test_calata.py`, `test_carte_compagno.py`, `test_distribuzione.py`, `test_momenti_tavolo.py`, `test_punti_mano.py`, `test_csp.py`: PASS. `ruff check .` pulito. Guardato con gli screenshot a 360×640 (1v1, 2v2, senza briscola, mazzo finito), 1024×768, 1280×720 (1v1 e 2v2), 1440×900
- **Decisioni prese**: quelle sopra
- **Domande nuove**: nessuna
- **Punti delicati**: (1) da computer `.table__corner` è fisso (`top: 14px; right: 24px`), non più `.scoreboard`: chi misura il tabellone lo trova nello stesso posto; (2) la posizione del mazzo del 1v1 da computer dipende da 5 carte della mano (`rules.hand_size`), dagli spazi di `.table__mine` e dalla larghezza della pillola "Frasi": se cambiano va rimisurata (lo segnala `test_da_computer_mazzo_del_1v1_sotto_frasi`); (3) il marcatore del tondo è `data-trump-badge` (valore: il seme); `[data-trump]` c'è solo sopra il mazzo
- **Cosa devono fare gli altri**: **Chi è di turno sui documenti**: spuntare P100 e P102, lista definitiva in 9.2; in `DECISIONI.md` le scelte sopra (e che P102 cambia "Briscola solo sul mazzo" del 01/10 anche a mazzo finito); in `CLAUDE.md` aggiornare i punti delicati "Briscola (P77)" (niente seme a mazzo finito, tondo `data-trump-badge`) e "Tavolo da computer (P74)" (angolo fisso `.table__corner`)

### P99 — Lancio della propria carta più realistico (05/10/2026)

- **Branch**: feature/p99-lancio-realistico (fatto da Claude, con il permesso di Christian per commit, merge e push dei punti P85–P103)
- **File** (lista definitiva per 9.2): modificati `app/static/js/pages/game.js` (`MY_THROW_MS`, `throws` con durata e punto di partenza, `aimMyThrows`), `app/static/css/components/trick.css` (`card-throw-mine`), `tests/table/test_animazioni_in_fila.py` (la prima pescata dopo la tua carta aspetta 0,55 s), questo file; creato `tests/table/test_lancio_mio.py`
- **Cosa cambia** (animazione scelta da Christian il 04/10): la **tua** carta parte **dal suo posto nella mano**, grande com'era e dritta; nei primi 0,1 s **si solleva** (ombra più grande), poi **vola ad arco** verso il centro (in orizzontale si sposta prima che in verticale) **girando di circa 14°** verso il centro, e **si posa con un piccolo assestamento** (si schiaccia al 97% e gira di poco dall'altra parte); in tutto **0,55 s** (`MY_THROW_MS`, uguale a `card-throw-mine`). Mentre vola passa **sopra** le carte della mano. Vale anche per la carta giocata dalla mossa automatica. Se la carta non era nella mano disegnata (per esempio la prima vista dopo un rientro) arriva dal basso come prima. Le carte degli **avversari** volano come prima (0,4 s). Con "riduci movimento" niente lancio, come prima
- **Server** (scelta di Christian del 05/10): `room.py` **non cambia**: la pausa dopo una presa conta ancora 0,4 s per il volo; quando chiudi tu la presa, sul tuo schermo le pescate finiscono fino a 0,15 s dopo che il server ha fatto partire il turno (14,85 s giocabili invece di 15). `test_pause_uguali_a_quelle_della_pagina` confronta ancora `THROW_MS` (0,4) con `THROW_SECONDS`: passa
- **Calcolo** [T]: lo spostamento si misura dopo il ridisegno, tra il rettangolo della carta nella mano (preso prima del ridisegno) e quello della carta a riposo nella presa, tolti la rotazione della casella (−2°) e l'ingrandimento della carta che vince (P76); scarto misurato all'inizio e alla fine del volo: meno di 4 px a 360×640 e 1280×720
- **Controlli**: `tests/table/test_lancio_mio.py` **7 PASS** (durata uguale nel CSS e nella pagina, più lunga di quella degli avversari e al massimo 0,6 s; a 360×640 e 1280×720, con la prima e l'ultima carta: parte dal posto nella mano con la stessa misura, si solleva, arco, finisce al suo posto, sopra la mano; la carta dell'avversario ha ancora `card-throw` da 0,4 s; senza la carta nella mano arriva dal basso); rilanciati `test_lancio_carta.py`, `test_animazioni_in_fila.py`, `test_momenti_tavolo.py`, `test_timer_in_anticipo.py`, `test_calata.py`, `test_carte_compagno.py`, `test_mano_ferma.py`, `test_distribuzione.py`, `test_presa_affiancata.py`, `test_grafica_tavolo.py`: 83 PASS; `test_turno.py -k pagina` (Giuseppe): 6 PASS. `ruff check .` pulito. Guardato con i fotogrammi del volo a 360×640 e 1280×720
- **Decisioni prese**: server invariato (sopra), scelta di Christian sulla raccomandazione di Claude
- **Domande nuove**: nessuna
- **Punti delicati**: `throws` in `game.js` ora tiene `{ at, ms, from }` per carta: la fila dei lanci (P78) somma la durata di ogni carta, quindi le pescate dopo la tua carta partono 0,55 s dopo. La tua carta in volo è sempre `.trick__card--bottom` (in basso c'è sempre chi guarda): se cambia questa regola, `aimMyThrows` e `card-throw-mine` vanno rivisti
- **Cosa devono fare gli altri**: **Giuseppe**: niente; sappi che il lancio della carta di chi guarda dura 0,55 s (quelli degli altri 0,4, come `THROW_SECONDS`), e Christian ha scelto di non cambiare la pausa del server. **Chi è di turno sui documenti**: spuntare P99, lista definitiva in 9.2; registrare in `DECISIONI.md` l'animazione scelta e "server invariato"; in `CLAUDE.md`, punto delicato "Animazioni in fila (P78)": le durate in fila non sono più tutte `THROW_MS`

### P98 — Zoom con il doppio tocco al tavolo su iPhone (05/10/2026)

- **Branch**: fix/p98-zoom-iphone (fatto da Claude, con il permesso di Christian per commit, merge e push dei punti P85–P103)
- **File** (lista definitiva per 9.2): modificati `app/static/css/pages/game.css`, `tests/table/test_tocchi_tavolo.py` (due test nuovi), questo file
- **Causa** [L]: `touch-action` **non si eredita**. La regola di P69 stava solo su `<html>` (`:root:has(.page--game)`): Chrome unisce i valori di tutti gli antenati dell'elemento toccato, quindi su Android funzionava; Safari su iPhone guarda l'elemento toccato, che aveva `auto`, e lasciava lo zoom con il doppio tocco [D: Safari non si può provare con Chrome dei test]
- **Cosa cambia**: `touch-action: manipulation` su **ogni elemento** della pagina del tavolo (`:root:has(.page--game) *`), comprese le finestre fuori da `<main>`; lo zoom con due dita resta. Su Android e da computer il comportamento è lo stesso di prima
- **Controlli**: `tests/table/test_tocchi_tavolo.py` **5 PASS** (2 nuovi: ogni elemento della pagina, anche uno aggiunto fuori da `<main>`, ha `manipulation`; senza la classe del tavolo una carta torna `auto`); senza la correzione il primo test nuovo fallisce. Rilanciato `test_csp.py`: in tutto 9 PASS. `ruff check .` pulito
- **Da provare a mano**: su un iPhone vero, con Safari, il doppio tocco su carte, panno, nomi e pulsanti non deve ingrandire il tavolo (il "Fatto quando" del punto); se ingrandisce ancora, la strada successiva è un controllo in JavaScript sul secondo tocco ravvicinato, che però rischia di perdere un tocco veloce su una carta: da decidere con Christian
- **Decisioni prese**: nessuna (correzione)
- **Domande nuove**: nessuna
- **Punti delicati**: un elemento nuovo del tavolo con un suo `touch-action` (per esempio `pan-y` per una lista che scorre) va scritto dopo questa regola o con un selettore più forte
- **Cosa devono fare gli altri**: **Chi è di turno sui documenti**: spuntare P98 dopo la prova sull'iPhone, lista definitiva in 9.2; in `CLAUDE.md`, punto delicato "Tocchi al tavolo (P69)": la regola sta su ogni elemento perché Safari non la eredita

### P97 — Le carte della propria mano "lampeggiano" (05/10/2026)

- **Branch**: fix/p97-carte-lampeggiano (fatto da Claude, con il permesso di Christian per commit, merge e push dei punti P85–P103)
- **File** (lista definitiva per 9.2): modificati `app/static/css/components/card.css` (fuori dai file "probabili": l'aveva indicato Christian nell'ipotesi), `app/static/js/pages/game.js` (`keepHover`, `dropKeptHover`), questo file; creato `tests/table/test_mano_ferma.py`
- **Causa** [T]: il tavolo si ridisegna tutto a ogni vista e il pulsante della carta che era sotto il puntatore nasceva abbassato; appena il browser si accorgeva del puntatore sopra, si rialzava con la transizione di `card.css` (0,15 s). Riprodotto da computer con il mouse fermo su una carta: a ogni vista la carta scendeva a 0 e risaliva a −8%. Sul telefono il browser lascia `:hover` sulla carta appena toccata (il "mouse" resta dove hai toccato) [D: Chrome dei test, con il tocco emulato, non lo lascia], quindi succedeva lì a ogni vista
- **Cosa cambia**: (1) il sollevamento al passaggio vale solo con un puntatore vero (`@media (hover: hover)`): sul telefono la carta non si alza più al tocco (resta il piccolo sollevamento di `:active` mentre il dito preme e quello del fuoco da tastiera); (2) da computer la carta sotto il mouse, ridisegnata, **nasce già sollevata** (classe `card--hover-kept`, tolta al primo movimento del mouse, quando decide di nuovo `:hover`); vale anche per le carte del compagno (P93)
- **Controlli**: `tests/table/test_mano_ferma.py` **4 PASS** (regola dentro `@media (hover: hover)`; con il mouse fermo, in 3 viste per 40 fotogrammi l'una la carta resta sollevata ferma e le altre non si muovono; uscito il mouse torna giù; con il tocco emulato nessuna carta si muove); prima della correzione la riproduzione mostrava la carta che ripartiva da 0 a ogni vista. Rilanciati `test_lancio_carta.py`, `test_carte_compagno.py`, `test_tocchi_tavolo.py`, `test_carte.py`: in tutto 38 PASS. `ruff check .` pulito
- **Decisioni prese**: nessuna (correzione)
- **Domande nuove**: nessuna
- **Punti delicati**: la carta sotto il mouse si riconosce da `data-suit`, `data-rank` e `data-advise-card` (mano tua o del compagno): se cambiano quegli attributi di `Card`/`RevealedHand`, va cambiato `keepHover`
- **Cosa devono fare gli altri**: **Chi è di turno sui documenti**: spuntare P97, lista definitiva in 9.2; in `CLAUDE.md`, punto delicato nuovo: sul telefono niente `:hover` sulle carte (P97)

### P95 — Partita interrotta dal riavvio del server (04/10/2026)

- **Branch**: fix/p95-partita-interrotta (fatto da Claude, con il permesso di Christian per commit, merge e push dei punti P85–P103)
- **File** (lista definitiva per 9.2): modificati `app/static/js/pages/game.js` (`join`, `showGone`), `app/static/css/components/table.css` (`.table__gone`), questo file; creato `tests/table/test_partita_interrotta.py`. Il server non è cambiato: rispondeva già `not_found`
- **Causa** [T]: dopo il riavvio la pagina si ricollega e manda `game:join`; il server risponde `not_found` ("Questa partita non esiste o è già finita."), ma `join` con il tavolo già disegnato scriveva il messaggio solo nella riga di stato e lasciava il tavolo com'era. Il test nuovo, prima della correzione, falliva su "Tempo scaduto: riquadro della partita interrotta"
- **Cosa cambia**: con `not_found` al rientro, al posto del tavolo c'è il riquadro **"La partita è stata interrotta"**, "Il server si è riavviato o la partita non esiste più." e **"Torna alla home"**; dopo **5 s** si torna alla home da soli (scelta di Christian); la pagina si ferma come per `game:replaced`. Se la pagina si apre su una partita che non c'è (nessuna vista ancora), resta il messaggio di prima
- **Controlli**: `tests/table/test_partita_interrotta.py` **1 PASS**, 3 giri su 3 (partita vera contro la CPU, stanza tolta come dopo un riavvio, collegamento chiuso dal server come in P33: riquadro, niente tavolo, ritorno alla home tra 4 e 9 s); rilanciati `test_pagina_tavolo.py`, `test_calata.py`, `test_csp.py`: 27 PASS. `ruff check .` pulito
- **Decisioni prese**: nessuna oltre a quella del 04/10 (riquadro e home in 5 s)
- **Domande nuove**: nessuna
- **Punti delicati**: nel test la home vera **non si apre** (il browser risponde da sé all'indirizzo `/`): al primo giro, con la home vera, il test si è bloccato una volta a fine test (collegamento della home lasciato a metà, come nel punto delicato di P58); la suite `table` non prepara MySQL, quindi il test sostituisce `_ratings_of` e `friends_events.notify_presence`
- **Cosa devono fare gli altri**: **Chi è di turno sui documenti**: spuntare P95, lista definitiva in 9.2

### P93 — Carte del compagno scoperte e consiglio al tavolo (04/10/2026)

- **Branch**: feature/p93-carte-compagno (fatto da Claude, con il permesso di Christian per commit, merge e push dei punti P85–P103)
- **File** (lista definitiva per 9.2): modificati `app/static/js/core/events.js` (`GAME_ADVISE`, `GAME_ADVICE`), `components/Hand.js` (`RevealedHand` con le carte da toccare, carta consigliata nella `Hand`), `components/Table.js`, `pages/game.js`, `app/static/css/components/table.css`, questo file; creato `tests/table/test_carte_compagno.py`
- **Cosa cambia**: (1) quando la vista ha `partner_hand` (2v2, briscola e mazzo finito), il ventaglio del compagno in alto **entra scoperto** nel tavolo (lo stesso di P85), un po' più grande di quello coperto (52 px sul telefono, 80 da computer), fino a fine mano; per **2,5 s** la scritta "Mazzo finito: ora vedi le carte di Salvo" (non alla prima vista, per esempio rientrando); (2) il compagno **si sposta**: sotto il ventaglio sul telefono e sul tablet, più a sinistra da computer, dove anche presa e mazzo scendono di un po'; niente resta coperto e l'anello del suo tempo si vede; (3) toccando una sua carta parte `game:advise` con quella carta: la carta resta **sollevata e bordata** di giallo ("premuta" per i lettori di schermo, etichetta "Consiglia a Salvo: …"); un'altra carta la sostituisce, la stessa carta toglie il consiglio (`card: null`); finché non arriva la risposta le sue carte sono spente, e anche senza connessione o a fine mano; il segno sparisce quando la carta non è più in mano al compagno; (4) il consiglio ricevuto (`game:advice`, o `advice` nella vista) segna la carta nella tua mano con il bordo giallo e la scritta "consiglio di Salvo" dentro la carta ("consigliata da Salvo" per i lettori di schermo)
- **Scelte di Christian** (04/10): il compagno si sposta invece di farsi coprire dal ventaglio; chi consiglia vede il segno sulla carta consigliata. **Approvati** da Christian i nomi del contratto di P92 (`game:advise`, `game:advice`, `partner_hand`, `advice`) e di P68 (`cpu:start` in 4.1, `cpu` per giocatore)
- **Scelte di Claude**: misure (52/80 px), scritta in fondo al centro del tavolo per 2,5 s, scritta del consiglio dentro la carta; guardato con gli screenshot a 360×640, 768×1024, 1024×768 e 1280×720
- **Controlli**: `tests/table/test_carte_compagno.py` **7 PASS** (nomi degli eventi; ventaglio solo con `partner_hand` e con le carte giuste, avversari ancora coperti; scritta che sparisce in 1,5–4 s con le carte che restano; a 6 misure il ventaglio non copre avatar e nome del compagno, la presa e "Esci", e il tavolo non scorre; consiglio dato segnato, sostituito, tolto e sparito con la carta; consiglio ricevuto nella tua mano; nel 1v1 niente); rilanciati `test_calata.py`, `test_momenti_tavolo.py`, `test_pagina_tavolo.py`, `test_grafica_tavolo.py`, `test_icone.py`: 67 PASS. `ruff check .` pulito
- **Decisioni prese**: quelle sopra
- **Domande nuove**: nessuna
- **Punti delicati**: il compagno si sposta con la classe `table__inner--mate-cards` (Table.js): se cambiano la misura del ventaglio scoperto o la posizione del posto in alto da computer (`--top-fan-half`, P74), va rimisurato (lo segnala `test_non_copre_ne_compagno_ne_presa`)
- **Cosa devono fare gli altri**: **Giuseppe**: nel contratto puoi togliere "da approvare da Christian" accanto ai nomi di P92 e P68 (approvati il 04/10). **Chi è di turno sui documenti**: spuntare P93, lista definitiva in 9.2; registrare in `DECISIONI.md` (Processo) i contratti di P92 e P68 approvati

### P85 — "Cala le carte": pulsante e carte calate al tavolo (04/10/2026)

- **Branch**: feature/p85-cala-le-carte (fatto da Claude, con il permesso di Christian per commit, merge e push dei punti P85–P103)
- **File** (lista definitiva per 9.2): modificati `app/static/js/core/events.js` (`GAME_LAY_DOWN`), `components/SingButtons.js` (pulsante "Cala le carte"), `components/Hand.js` (`RevealedHand`), `components/Table.js`, `pages/game.js`, `app/static/css/components/table.css`, questo file; creato `tests/table/test_calata.py`
- **Cosa cambia**: (1) accanto ai pulsanti "Canta" c'è **"Cala le carte"** (icona `playing_cards`, già nel font) solo quando `legal.lay_down` è vero; manda `game:lay_down` con la `version` come una carta (doppio clic: la seconda volta il pulsante è già spento); (2) quando arriva una mano finita **nuova** con `last_hand.laid_down`, per **3 s** (`LAID_DOWN_MS`, uguale a `LAID_DOWN_SECONDS` del server) i ventagli degli altri **entrano scoperti nel tavolo**, interi e dritti (anche quello in alto), con l'entrata da 0,3 s; la tua mano è quella del momento della calata (non si gioca); al centro, al posto della presa, la scritta gialla "Turi cala le carte" ("Hai calato le carte" se sei tu), con tutte le carte per i lettori di schermo; poi il riepilogo come sempre; se la calata **chiude la partita** dopo i 3 s arriva il riquadro finale; (3) con una calata `last_hand.last_trick` non si rilancia (è una presa già vista)
- **Scelte di Christian** (04/10, chieste prima di cominciare): ventagli scoperti invece delle carte in righe al centro; quando i ventagli, che stanno per metà fuori dallo schermo, si sono rivelati illeggibili, ha scelto che **entrino nel tavolo** coprendo per un momento nome e avatar di quel giocatore
- **Scelte di Claude**: ventaglio scoperto aperto al massimo 12° tra due carte e 40° in tutto (due ventagli di 5 carte stanno ai lati di un telefono); sotto i 1024 px i ventagli ai lati scendono al 60% dell'altezza per lasciare libera la scritta; testo "Hai calato le carte" per chi cala. Guardato con gli screenshot a 360×640, 768×1024, 1024×768 e 1280×720, nel 1v1 e nel 2v2 con 3 e 5 carte a testa
- **Controlli**: `tests/table/test_calata.py` **10 PASS** (durata uguale alla pausa del server, nome dell'evento, pulsante solo con `lay_down`, carte calate e poi riepilogo nel 1v1 e nel 2v2 a 360×640 e 1280×720 con le carte giuste di ogni posto e dentro lo schermo, "Hai calato", calata che chiude la partita, nessuna carta rilanciata); rilanciati anche `test_momenti_tavolo.py`, `test_pagina_tavolo.py`, `test_grafica_tavolo.py`, `test_tavolo_telefono.py`, `test_icone.py`: in tutto 82 PASS. Il giro completo si fa alla fine di P85–P103. `ruff check .` pulito
- **Decisioni prese**: quelle sopra (ventagli che entrano nel tavolo)
- **Domande nuove**: nessuna
- **Punti delicati**: `RevealedHand` (Hand.js) servirà anche a P93 per il ventaglio del compagno; la calata si riconosce da `last_hand.hand_number` cambiato con `laid_down` non nullo (non da `hand_number`, che a partita finita non sale); se cambia `LAID_DOWN_MS` va cambiato anche `LAID_DOWN_SECONDS` in `room.py` (lo controlla `test_durata_uguale_alla_pausa_del_server`)
- **Cosa devono fare gli altri**: **Giuseppe**: niente; nel contratto (3.2, 3.3) c'è ancora "da approvare da Christian" accanto a `game:lay_down`, `legal.lay_down` e `last_hand.laid_down`: sono approvati dal 04/10 (`DECISIONI.md`), puoi togliere la nota quando tocchi il contratto. **Chi è di turno sui documenti**: spuntare P85, lista definitiva in 9.2

### Documenti: prova del tavolo del 04/10 (P94–P103) e registrazione di P84 (04/10/2026)

- **Branch**: docs/cose-da-sistemare-04-10
- **File**: modificati `SCALETTA.md` (P84 spuntato con la nota e la lista definitiva in 9.2; P94–P103 nel tracker, nelle schede, nella tabella di 9.1, nei controlli di parallelismo e in 9.2; "Da dove si parte"), `DECISIONI.md` (Interfaccia: prova del 04/10; Gioco: turno da 15 s, partita interrotta dal riavvio, login con nome utente o email; Processo: contratto di P84; rimandi nelle decisioni dei 30 s e di D12), `docs/REGOLE-GIOCO.md` (turno da 15 s che parte dopo le pause), `CLAUDE.md` (riga "Stato", numero dei controlli, punto delicato "Calata (P84)"), questo file. `DA-DECIDERE.md` non cambia
- **Controlli**: nessuno (soli documenti); ultimo giro completo **1676 PASS** in 9 suite (P84, dal riepilogo di Giuseppe)
- **Riepiloghi registrati**: `giuseppe.md` P84; `christian.md` e `antonio.md` niente di nuovo
- **Prova del 04/10** (Christian, telefono e computer, appunti in `cose-da-sistemare.txt`, che non va nel repository): 13 annotazioni, diventate **P94** (Giuseppe: turno da 15 s che parte dopo le pause), **P95** (partita interrotta dal riavvio del server: avviso e ritorno alla home; causa probabile in `game.js` [L]), **P96** (Giuseppe: login con nome utente o email in un campo solo), **P97** (carte della mano che lampeggiano), **P98** (zoom con il doppio tocco su iPhone Safari), **P99** (lancio più realistico), **P100** (mazzo del 1v1), **P101** (frasi sul telefono sopra le tue carte), **P102** (indicatore della briscola; cambia P77 a mazzo finito), **P103** (suoni, interruttore nelle impostazioni, scelta salvata nel browser)
- **Decisioni registrate**: quelle della prova (sopra, scelte da Christian dopo le domande di Claude) e il **contratto di P84** (`game:lay_down`, `legal.lay_down`, `last_hand.laid_down`), approvato da Christian
- **Domande**: nessuna nuova
- **Cosa devono fare gli altri**: **Giuseppe**: i tuoi punti nuovi sono **P94** (le durate delle pause devono essere quelle di `game.js`: chiedile a Christian, o leggile, e un test le confronta) e **P96**; il turno da 15 s è già nel regolamento. Sul FAIL di `table` del tuo giro di P84: non si può dire se è lo stesso fallimento raro di P91, che non era stato identificato; se ricapita, il runner stampa i dettagli

### Documenti: D43, D45 e D46 decise (04/10/2026)

- **Branch**: docs/d43-d45-d46-decise
- **File**: modificati `DECISIONI.md` (Gioco: tre decisioni nuove; rimandi nelle decisioni del 29/09 sulla CPU e del 01/10 su "Cala le carte"), `DA-DECIDERE.md` (tolte D43, D45 e D46), `docs/REGOLE-GIOCO.md` (sezioni nuove "Calare le carte" e "Carte del compagno a mazzo finito (2v2)", punto 6 dello svolgimento della mano), `SCALETTA.md` (P68, P73, P84, P92, P93 non aspettano più una domanda: tracker, schede, tabella 9.1, 9.2, "Da dove si parte"), `CLAUDE.md` (riga "Stato"), questo file
- **Controlli**: nessuno (soli documenti); ultimo giro completo **1647 PASS** in 9 suite (P91). `tests/api/test_pagina_home.py` legge tre frasi del regolamento: sono rimaste uguali
- **Decisioni registrate**: **D43**, **D45** e **D46**, proposte da Christian e approvate da Giuseppe a voce il 04/10/2026 (erano insieme), con il testo delle proposte di oggi
- **Domande**: nessuna nuova; restano D1, D21, D31
- **Cosa devono fare gli altri**: **Giuseppe**: il regolamento di "Cala le carte" e delle carte del compagno è **già scritto** in `docs/REGOLE-GIOCO.md` (in P84 e P92 restano contratto ed esempi della vista); ordine: P68 (strategia nuova e `cpu: true`), P84, poi P92; il contratto di `cpu:start` e i nomi dei campi e degli eventi nuovi si approvano con Christian

### Documenti: proposta D46 (carte del compagno e consiglio), punti P92 e P93 (04/10/2026)

- **Branch**: docs/d46-carte-compagno
- **File**: modificati `DA-DECIDERE.md` (D46 nuova), `SCALETTA.md` (P92 e P93 nel tracker, nelle schede della sezione 4, nella tabella di 9.1, nei controlli di parallelismo e in 9.2; "Da dove si parte"), `CLAUDE.md` (riga "Stato"), questo file. `DECISIONI.md` e `docs/REGOLE-GIOCO.md` non cambiano finché Giuseppe non dà l'ok
- **Controlli**: nessuno (soli documenti); ultimo giro completo **1647 PASS** in 9 suite (P91)
- **Riepiloghi registrati**: nessuno nuovo (`giuseppe.md` fermo a P88, `antonio.md` a P27)
- **Proposta D46** (Christian, sulle raccomandazioni di Claude; testo completo in `DA-DECIDERE.md`): nel **2v2**, da quando ci sono insieme la **briscola fissata** e il **mazzo finito** (in qualunque ordine), ognuno vede le carte del **proprio compagno**, scoperte **fino a fine mano**; senza briscola mai. Il ventaglio del compagno si gira da solo, un po' più grande, con una scritta di 2–3 s. Cliccando una carta del compagno gli si **consiglia** quale lanciare: in qualunque momento, uno alla volta, solo al compagno, senza salvataggio, solo la carta. La mossa automatica ignora il consiglio; la CPU nel 2v2 seguirà la stessa regola. Scartato da Christian: un pulsante "Guarda le carte"
- **Punti nuovi**: **P92** (Giuseppe: regola, carte del compagno nella vista solo quando permesso, evento del consiglio, contratto e regolamento) e **P93** (Christian: il tavolo, dopo P92)
- **Domande nuove**: **D46** (aspetta l'ok di Giuseppe)
- **Cosa devono fare gli altri**: **Giuseppe**: leggi D46 in `DA-DECIDERE.md` e scrivi nel tuo riepilogo ok o obiezioni, insieme a quelli su D43 e D45; P92 è meglio dopo P84 (stessi file del motore e della vista); nome e forma del campo e dell'evento da fissare con Christian. **Chi è di turno dopo l'ok**: spostare D46 in `DECISIONI.md` e la regola in `docs/REGOLE-GIOCO.md`

### Documenti: proposte di Christian su D43 e D45 (04/10/2026)

- **Branch**: docs/d43-d45-proposte
- **File**: modificati `DA-DECIDERE.md` (D43 e D45: proposte del 04/10), `SCALETTA.md` (sezione 9, "Da dove si parte"), `CLAUDE.md` (riga "Stato"), questo file. `DECISIONI.md` non cambia: le proposte diventano decisioni solo dopo l'ok di Giuseppe
- **Controlli**: nessuno (soli documenti); ultimo giro completo **1647 PASS** in 9 suite (P91)
- **Riepiloghi registrati**: nessuno nuovo (`giuseppe.md` fermo a P88, `antonio.md` a P27)
- **Proposte** (Christian, sulle raccomandazioni di Claude; il testo completo è in `DA-DECIDERE.md`):
  - **D43 (CPU)**: strategia "simulazione", cioè 100–200 distribuzioni possibili delle carte nascoste per ogni mossa e calcolo esatto a mazzo finito, con la memoria delle carte uscite solo per la CPU; solo 1v1; non si salva e non conta; scelta nella carta-modal; nome "CPU", icona robot, `cpu: true` nella vista, attesa tra 1 e 2 s
  - **D45 ("Cala le carte")**: lettura "giocando bene"; pulsante solo a inizio presa, a chi apre; si cala solo con la briscola fissata, o senza briscola con 2 carte o meno a testa; prima si cantano tutti i propri semi; nel 2v2 il server aggiunge 20 punti per ogni seme che il compagno potrebbe cantare; carte scoperte per circa 3 s, poi il riepilogo; la CPU può calare, la mossa automatica no
- **Domande nuove**: nessuna ("2 carte o meno", cioè anche con l'ultima carta, confermato da Christian)
- **Cosa devono fare gli altri**: **Giuseppe**: leggi D43 e D45 in `DA-DECIDERE.md` e scrivi nel tuo riepilogo ok o obiezioni; poi P68 (strategia nuova e `cpu: true`) e P84. **Chi è di turno dopo l'ok**: spostare D43 e D45 in `DECISIONI.md` e la regola di D45 in `docs/REGOLE-GIOCO.md`

### Documenti: registrati P91 e l'annullamento di P9 (03/10/2026)

- **Branch**: docs/p91-e-p9
- **File**: modificati `SCALETTA.md` (P91 spuntato con la nota e la lista definitiva in 9.2; nota in P9; sezione 9 "Da dove si parte"), `DECISIONI.md` (Processo: suite nuova `table`), `CLAUDE.md` (riga "Stato", numero dei controlli e regola della suite `table` in "Testing", due punti delicati nuovi: ridisegni di fine animazione e suite `table`), questo file. `DA-DECIDERE.md` non cambia
- **Controlli**: nessuno (soli documenti); ultimo giro completo **1647 PASS** in 9 suite (P91)
- **Riepiloghi registrati**: `christian.md` P91; `giuseppe.md` e `antonio.md` niente di nuovo
- **Decisioni registrate**: suite nuova `table` per i test lunghi del tavolo nel browser (P91)
- **P9**: la prima parte (README verificato su un clone, 84e37ed) è stata annullata lo stesso giorno su richiesta di Christian (revert 95e9c44): si rifà da capo quando lo dice lui
- **Domande**: nessuna nuova
- **Cosa devono fare gli altri**: **Giuseppe**: le suite ora sono nove (`table` si lancia per ultima, `tests/esegui_tutti.py` non è cambiato); un test lungo nuovo del tavolo nel browser va in `table`; P82, poi D43 e D45 insieme a Christian

### P91 — Suite `frontend` sotto il limite di tempo: nuova suite `table` (03/10/2026)

- **Branch**: fix/p91-suite-frontend (fatto da Claude mentre Christian era via, con il suo permesso per commit, merge e push)
- **File** (lista definitiva per 9.2): creata la cartella `tests/table/` (una **suite nuova**: il runner la trova da solo, `tests/esegui_tutti.py` **non è stato toccato**) con il test nuovo `tests/table/test_timer_in_anticipo.py`; **spostati** in `tests/table/` da `tests/frontend/` `test_momenti_tavolo.py`, `test_frasi_pagina.py`, `test_distribuzione.py`, `test_carte_avversari.py`, `test_lancio_carta.py`, `test_tocchi_tavolo.py` e da `tests/api/` `test_carte_pronte.py`, `test_animazioni_in_fila.py`, `test_punti_mano.py`; modificati `app/static/js/pages/game.js` (`redrawAfter`, sotto), `tests/table/test_frasi_pagina.py` (il fumetto si aspetta), `test_carte_pronte.py` (latenza finta 300 ms invece di 800), `test_punti_mano.py` (solo la nota sulla suite), questo file
- **Misure prima** [T] (03/10, pytest con `--durations`): `frontend` **226 s** e anche `api` **221 s** (con un test fallito), quindi spostare i file da `frontend` ad `api`, come diceva il punto, non bastava: `api` sarebbe andata oltre i 240 s. Circa un terzo del tempo è l'avvio di Chrome (0,5 s per test) e del server (2,5 s per file)
- **Cosa cambia**: (1) suite nuova **`table`** con i test lunghi del tavolo nel browser (animazioni, momenti, frasi, carte pronte, punti della mano); in `api` restano i test della grafica del tavolo (`test_grafica_tavolo.py`, `test_rating_tavolo.py`, `test_frasi_di_lato.py`, `test_tavolo_telefono.py`, `test_presa_affiancata.py`, `test_stile_tavolo.py`, `test_pagina_tavolo.py`); (2) `test_carte_pronte.py` con la rete lenta a 300 ms: i due test lenti passano da 15 s a circa 6 s, e senza lo scaricamento anticipato delle carte (P79) falliscono ancora [T]; (3) **difetto vero** in `game.js` [T]: in Chrome `setTimeout` a volte scatta **in anticipo** (misurato: fino a 0,7 ms, 6 timer su 200); i timer che ridisegnano a fine lancio, pescata, distribuzione e pausa delle frasi trovavano il momento ancora "in corso", e i segni restavano sul tavolo fino alla vista successiva; il **pulsante delle frasi** poteva restare **spento** dopo i 3 secondi. Era la causa di `test_nel_2v2_si_pesca_una_carta_alla_volta` che falliva a caso ("pescate finite"). Ora i quattro timer passano da `redrawAfter(ms)`, che aspetta 20 ms in più (`TIMER_SLACK_MS`, non si vedono); (4) `test_tocchi_rapidi_una_frase_per_pausa` aspetta il fumetto invece di leggerlo subito dopo il clic
- **Controlli**: giro completo **1647 PASS** in **9 suite**, tutto PASS, 631 s (runner 13, engine 673, db 89, api 341 in 164 s, services 38, sockets 275, frontend 132 in 110 s, e2e 12, table 74 in 165 s; 4 nuovi), file protetti intatti. Giri delle tre suite toccate: (1) `frontend` 115 s, `api` 152 s, `table` 162 s, tutto PASS; (2) `frontend` 121 s, `api` 173 s, `table` 163 s con **1 FAIL** (test non identificato: l'output era tagliato), poi `table` da sola 5 giri su 5 PASS (160–176 s); (3) giro completo qui sopra: **3 giri su 3** con `frontend` sotto i 170 s e `api` sotto i 200 s (il "Fatto quando" di P91). `test_timer_in_anticipo.py` (4 test nuovi: fa scattare ogni timer della pagina 10 ms prima) passa 3 giri su 3 con la correzione e **fallisce 3 su 3 senza** [T]. `ruff check .` pulito
- **Decisioni prese** (Claude, da confermare da Christian): **suite nuova `table`** invece di spostare tutto in `api`; margine di 20 ms sui ridisegni di fine animazione
- **Domande nuove**: nessuna
- **Punti delicati**: (1) un test **nuovo e lungo del tavolo nel browser** va nella suite `table` (non più in `api`); con le suite a 115 / 150–175 / 160–176 s, quella che si avvicina ai 240 s va divisa di nuovo; (2) in `game.js` un ridisegno che deve trovare **finito** un momento misurato con `performance.now()` si programma con `redrawAfter`, mai con `setTimeout(redraw, fine - adesso)`; (3) nei test, `Page.addScriptToEvaluateOnNewDocument` funziona solo dopo `Page.enable` (`tests/browser.py` non lo attiva); (4) resta **un fallimento raro non identificato** nella suite `table` (1 giro su 7): se ricapita, guardare l'output completo del runner, che stampa i dettagli dei test falliti sopra il riepilogo
- **Cosa devono fare gli altri**: **Giuseppe**: le suite ora sono **nove** (c'è `table`, che il runner lancia per ultima); `tests/esegui_tutti.py` non è cambiato. **Chi è di turno sui documenti**: spuntare P91 con la lista definitiva in 9.2; in `CLAUDE.md` cambiare "8 suite", la frase "un test lungo nel browser nuovo va nella suite `api`" (ora `table`) e i nomi dei file spostati nei punti delicati (per esempio `test_momenti_tavolo.py`, `test_frasi_pagina.py`, `test_carte_pronte.py` ora sono in `tests/table/`); aggiungere i punti delicati (2) e (3) qui sopra; la decisione sulla suite `table` in `DECISIONI.md` (Processo)

### Documenti: P34 segnato fatto, P9 rimesso in lista (03/10/2026)

- **Branch**: docs/p34-fatto-p9
- **File**: modificati `SCALETTA.md` (P34 spuntato con la nota; "Da dove si parte" con P9 e senza la prova di P34), `DECISIONI.md` (Processo: P34 fatto), `CLAUDE.md` (riga "Stato"), questo file
- **Controlli**: nessuno (soli documenti); ultimo giro completo 1643 PASS
- **Decisioni registrate**: **P34 fatto** (Christian): la prova su un telefono vero è quella del 29/09 con un amico, da cui sono nati P63–P73 e le correzioni del tavolo
- **Punto rimesso in lista**: **P9** (guida di installazione verificata, `README.md`) era aperto dalla Fase 1 ma "Da dove si parte" non lo nominava più
- **Domande**: nessuna nuova
- **Cosa devono fare gli altri**: **Giuseppe**: per P9 servirà un compagno che segua il `README.md` su un altro PC (il "Fatto quando" del punto)

### Documenti: registrati i lotti del 03/10 (P86, P76, P89, P80, P87, P78 e la correzione di P74) (03/10/2026)

- **Branch**: docs/lotti-03-10
- **File**: modificati `SCALETTA.md` (tracker: spuntati P76, P78, P80, P86, P87, P89, correzione annotata in P74, nota in P91; sezione 9 "Da dove si parte"; sezione 9.2 con le liste definitive del 03/10), `DECISIONI.md` (Interfaccia: sei decisioni del 03/10), `CLAUDE.md` (riga "Stato", numero dei controlli, punti delicati di P74 aggiornato e quattro nuovi: P76, P80, P87, P78), questo file. `DA-DECIDERE.md` non cambia
- **Controlli**: giro completo prima dell'aggiornamento, **1643 PASS** in 8 suite (runner 13, engine 673, db 89, api 358, services 38, sockets 275, frontend 185 in 206 s, e2e 12), file protetti intatti
- **Riepiloghi registrati**: `christian.md` P86, P76, correzione di P74, P89, P80, P87, P78; `giuseppe.md` e `antonio.md` niente di nuovo
- **Decisioni registrate**: mazzo da 88 px (P86); presa a croce e carta che vince sollevata e bordata (P76); pillola del rating, tratteggiata se provvisorio (P89); pannello delle frasi sul bordo destro, che nel 2v2 copre l'avversario di destra (P80); vetro scuro (P87); pescata in fila da 0,5 s, dopo la carta che chiude la presa (P78)
- **Domande**: nessuna nuova
- **Cosa devono fare gli altri**: **Giuseppe**: P82, poi D43 e D45 insieme a Christian; i punti del tavolo di Christian non toccano i tuoi file

### P78 — Animazioni in fila: lanci e pescate una alla volta (03/10/2026)

- **Branch**: feature/p78-animazioni-in-fila
- **File** (dall'elenco probabile di 9.2, tutti di Christian): modificati `app/static/js/pages/game.js`, `app/static/css/components/trick.css`, `tests/frontend/test_carte_avversari.py` (i tempi nuovi della pescata), questo file; creato `tests/api/test_animazioni_in_fila.py`. Non sono serviti `Trick.js`, `Hand.js` e `hand.css`: accettavano già i ritardi positivi ("tocca dopo")
- **Cosa cambia**: (1) **lanci in fila**: una carta arrivata mentre un'altra vola parte quando quella si è posata, e fino ad allora non si vede (il lancio ora parte da trasparente, prima da semitrasparente); finché ci sono carte in volo o in fila le tue carte non si giocano, come prima; (2) **pescata una alla volta**: prima chi ha preso, poi gli altri a turno, ognuno quando il precedente ha finito (0,5 s ciascuno, come prima), a partire da quando si è posata la carta che ha chiuso la presa (questo è il "ritocco in più" del punto). In tutto: 1v1 circa 1,4 s dalla carta che chiude la presa, 2v2 circa 2,4 s. Con "riduci movimento" niente animazioni, come prima. In `game.js` `throwsEnd` è l'ora in cui si posa l'ultima carta in fila; `DRAW_STEP_MS` non c'è più
- **Controlli**: solo i test toccati, tutti PASS: `test_animazioni_in_fila.py` **2** nuovi (due lanci mandati insieme nel 2v2: il secondo aspetta 0,4 s ed è invisibile, poi vola; pescata 2v2 di 4 giocatori a 0,5 s l'uno dall'altro, dopo il lancio della carta che chiude la presa), che **falliscono senza P78** e passano 3 giri su 3; `test_carte_avversari.py` e `test_lancio_carta.py` 15 (aggiornati i due test della pescata 1v1); `test_momenti_tavolo.py`, `test_distribuzione.py`, `test_tocchi_tavolo.py`, `test_frasi_pagina.py`, `test_grafica_tavolo.py`, `test_presa_affiancata.py`, `test_pagina_tavolo.py`, `test_punti_mano.py`. `ruff check` pulito. Suite complete non lanciate (su richiesta di Christian)
- **Decisioni prese** (Christian, 03/10/2026): pescata **0,5 s ciascuna, come oggi** (Claude consigliava 0,4 s; scartato anche 0,3 s); su raccomandazione di Claude, approvata con il punto: la pescata comincia quando si è posata la carta che ha chiuso la presa, e una carta in fila resta invisibile finché non vola
- **Domande nuove**: nessuna
- **Punti delicati**: in `game.js` lanci e pescate usano lo stesso `throwsEnd`: `noticeThrows` va chiamata **prima** di `noticeDraws` (in `noticeMoments` è così). `test_frasi_pagina.py::test_tocchi_rapidi_una_frase_per_pausa` è fallito una volta su cinque, senza legami con P78: legge il fumetto subito dopo un clic del mouse, senza aspettarlo (per P91)
- **Cosa devono fare gli altri**: niente. **Chi è di turno sui documenti**: spuntare P78, lista definitiva in 9.2, la scelta della durata in `DECISIONI.md`

### P87 — "Esci" e punti in vetro scuro (03/10/2026)

- **Branch**: feature/p87-esci-e-punti
- **File** (dall'elenco probabile di 9.2, tutti di Christian): modificati `app/static/css/base/variables.css` (tre colori nuovi: `--glass`, `--glass-hover`, `--glass-edge`), `app/static/css/components/table.css`, `scoreboard.css`, questo file; creato `tests/api/test_stile_tavolo.py`
- **Cosa cambia**: "Esci", il tabellone (da computer) e i punti della mano sono di **vetro scuro**: fondo verde scurissimo semitrasparente, il panno dietro sfocato, bordo sottile chiaro, scritte crema senza rilievo. I tuoi punti della mano sono in **giallo**, come il tuo totale nel tabellone. Posti e misure non cambiano (sul telefono "Esci" resta il tondo da 44 px di P90)
- **Controlli**: solo i test toccati, tutti PASS: `test_stile_tavolo.py` **4** nuovi (1v1 e 2v2 a 360×640 e 1280×720: colori del vetro, sfocatura, bordo, niente rilievo, contrasto almeno 4,5:1 calcolato sul punto più chiaro del panno, tuoi punti di un altro colore, etichette per i lettori di schermo), più `test_grafica_tavolo.py`, `test_tavolo_telefono.py`, `test_punti_mano.py`, `test_frasi_di_lato.py`, `test_rating_tavolo.py`, `test_pagina_tavolo.py`, `test_base.py` (colori solo in `variables.css`), `test_rifinitura.py`, `test_momenti_tavolo.py`. Suite complete non lanciate (su richiesta di Christian)
- **Decisioni prese** (Christian, 03/10/2026, sulla raccomandazione di Claude): stile **vetro scuro** per "Esci", tabellone e punti della mano. Scartati: crema piatto (come oggi ma senza ombra, tabellone a due colonne) e solo testo (niente sfondi, "Esci" come icona in un cerchio)
- **Domande nuove**: nessuna
- **Punti delicati**: a 1024×768, nel 1v1, tra "Esci" e i punti dell'avversario in alto restano circa 1,5 px (lo spazio c'era già da P74 e P89): il bordo del vetro ha tolto 1 px di spazio interno a "Esci" per non cambiarne la misura. Un nome lungo dell'avversario (fino a 20 caratteri) con la pillola del rating potrebbe farli toccare: `test_tavolo_da_computer` usa i nomi degli esempi (Turi), non il più lungo
- **Cosa devono fare gli altri**: niente. **Chi è di turno sui documenti**: spuntare P87, lista definitiva in 9.2, la scelta in `DECISIONI.md`

### P80 — Frasi del tavolo in un pannello a destra, da computer (03/10/2026)

- **Branch**: feature/p80-frasi-di-lato
- **File** (dall'elenco probabile di 9.2, tutti di Christian): modificati `app/static/css/components/table-phrases.css`, questo file; creato `tests/api/test_frasi_di_lato.py`. Non sono serviti `TablePhrases.js`, `Table.js` e `game.js`
- **Cosa cambia**: da 1024 px in su l'elenco delle frasi è un **pannello sul bordo destro** (24 px dal bordo, come il tabellone), largo 300 px (meno a 1024 px), dal tabellone fino sopra la tua riga; le frasi che non ci stanno scorrono dentro il pannello; entra scorrendo da destra. Presa, mazzo, la tua mano, il compagno e l'avversario a sinistra restano visibili e cliccabili; nel **2v2**, mentre è aperto, copre l'**avversario di destra**. Si chiude come prima (una frase, Esc, clic fuori). Sul telefono e sul tablet non cambia niente
- **Controlli**: solo i test toccati, tutti PASS: `test_frasi_di_lato.py` **7** nuovi (1v1 e 2v2 a 1024×768, 1280×720, 1440×900: pannello a destra, sotto il tabellone e sopra la tua riga, alto almeno mezzo schermo, tutte le 19 frasi, niente coperto tranne l'avversario di destra nel 2v2, presa, mazzo, mano e ventaglio in alto cliccabili; una frase chiude il pannello), più `test_grafica_tavolo.py`, `test_rating_tavolo.py`, `test_punti_mano.py`, `test_tavolo_telefono.py`, `test_pagina_tavolo.py`, `test_frasi_pagina.py`, `test_tocchi_tavolo.py`, `test_rifinitura.py`. `test_csp.py` passa per le pagine del tavolo; la sua prova sulla home è fallita solo perché, lanciando i file a mano con `pytest`, il database `cinquecento_test` non era preparato (manca `messaggi`: lo prepara il runner). Suite complete non lanciate (su richiesta di Christian)
- **Decisioni prese** (Christian, 03/10/2026, sulla raccomandazione di Claude): **pannello a tutta altezza sul bordo destro**, che nel 2v2 copre l'avversario di destra mentre è aperto. Scartati: il tavolo che si restringe a sinistra a ogni apertura, e un pannello piccolo tra mazzo e avversario di destra (a 1024 px largo circa 140 px). Il motivo: nel 2v2 a destra, tra il mazzo e l'avversario, restano 146 px a 1024×768, e l'elenco è alto 566 px se largo 280
- **Domande nuove**: nessuna
- **Punti delicati**: l'altezza del pannello si calcola da `.table__mine` (`100%` = altezza della tua riga, più circa 20 px di margine sotto): se cambia il margine in fondo al tavolo o la posizione del tabellone (`--phrases-top`, 96 px), va rimisurato (lo segnala `test_frasi_di_lato`)
- **Cosa devono fare gli altri**: niente. **Chi è di turno sui documenti**: spuntare P80, lista definitiva in 9.2, la scelta in `DECISIONI.md`

### P89 — Rating dei giocatori al tavolo, da computer (03/10/2026)

- **Branch**: feature/p89-rating-tavolo
- **File** (dall'elenco probabile di 9.2, tutti di Christian): modificati `app/static/js/components/Table.js`, `app/static/css/components/table.css`, questo file; creato `tests/api/test_rating_tavolo.py`
- **Cosa cambia**: da 1024 px in su, accanto al nome di ogni giocatore (tu, avversari, compagno) c'è una **pillola con il rating** (campo `rating` della vista, P88); se il rating è **provvisorio** la pillola è **tratteggiata e vuota**, e i lettori di schermo e il passaggio del mouse dicono "provvisorio". Chi ha `rating` null (la CPU) non ha la pillola. Sotto 1024 px non si vede. Il nome ora sta in `.seat__title` insieme alla pillola (`[data-rating]`, `[data-provisional]`)
- **Controlli**: solo i test del tavolo, tutti PASS: `test_rating_tavolo.py` **14** nuovi (pillola accanto al nome con il numero giusto, tratteggiata solo se provvisoria, 1v1 e 2v2 a 1024×768, 1280×720, 1440×900, senza scorrimento; niente pillola con `rating` null; niente a 360, 412 e 768 px), `test_grafica_tavolo.py` (il test da computer misura le etichette con la pillola dentro: niente si sovrappone), più altri 14 file del tavolo e delle pagine, **135 PASS**. `ruff check` dei test pulito. Suite complete non lanciate (su richiesta di Christian)
- **Decisioni prese** (Christian, 03/10/2026, sulle raccomandazioni di Claude): **pillola accanto al nome** (scartata: nella riga sotto il nome); provvisorio = **pillola tratteggiata** (scartati: la scritta "provv." e nessuna distinzione)
- **Domande nuove**: nessuna
- **Punti delicati**: nessuno nuovo
- **Cosa devono fare gli altri**: niente. **Chi è di turno sui documenti**: spuntare P89, lista definitiva in 9.2, le due scelte in `DECISIONI.md`

### Correzione — Da computer la mano non aspetta le immagini delle carte (03/10/2026)

- **Branch**: fix/mano-da-computer (difetto di P74 trovato durante P76; correzione chiesta da Christian, senza un punto della scaletta)
- **File**: modificati `app/static/css/components/table.css` (una regola da 1024 px in su), `tests/api/test_grafica_tavolo.py`, questo file
- **Cosa cambia**: da computer la mano sta in una colonna larga quanto il suo contenuto (P74), e finché le immagini delle carte non arrivavano le carte in mano erano larghe 27–30 px invece di 94: presa e mazzo stavano 45–90 px più in basso e poi saltavano su. Ora la mano da computer è larga sempre 5 carte (`rules.hand_size`) con i loro spazi, e niente si sposta. Telefono e tablet non cambiano
- **Controlli**: test nuovo `test_da_computer_la_mano_non_aspetta_le_immagini` (6 casi: 1v1 e 2v2 a 1024×768, 1280×720, 1440×900, con le immagini delle carte bloccate nel browser): falliva in tutti e 6 i casi prima della correzione, passa dopo. `test_mazzo_finito_resta_il_seme_dov_era_il_mazzo`, che falliva circa una volta su sei, passa 8 giri su 8. Tutti i test del tavolo **123 PASS** (`test_grafica_tavolo`, `test_presa_affiancata`, `test_pagina_tavolo`, `test_punti_mano`, `test_tavolo_telefono`, `test_carte_pronte`, `test_carte_avversari`, `test_lancio_carta`, `test_momenti_tavolo`, `test_distribuzione`, `test_frasi_pagina`, `test_tocchi_tavolo`). Suite complete non lanciate (su richiesta di Christian)
- **Decisioni prese**: nessuna
- **Domande nuove**: nessuna
- **Punti delicati**: da computer la larghezza della mano è `5 × --hand-card-max + 4 × --hand-gap` (`table.css`): se cambia il numero di carte in mano (`rules.hand_size`) va cambiato anche qui. Nei test, per bloccare delle richieste con `Network.setBlockedURLs` serve prima `Network.enable` (`tests/browser.py` non lo attiva): senza, il blocco funziona solo a volte
- **Cosa devono fare gli altri**: niente. **Chi è di turno sui documenti**: registrare il punto delicato qui sopra (P74)

### P76 — Presa con le carte a croce e la carta che vince evidenziata (03/10/2026)

- **Branch**: feature/p76-presa-affiancata
- **File** (lista approvata da Christian per 9.2): modificati `app/static/js/components/Trick.js`, `app/static/css/components/trick.css`, questo file; creato `tests/api/test_presa_affiancata.py`. `Table.js` non è servito (la presa riceve già `trick.winning_seat`)
- **Cosa cambia**: le carte della presa (in corso e appena chiusa, P57) stanno **a croce senza coprirsi**: in alto e in basso una sopra l'altra, nel 2v2 sinistra e destra nelle colonne accanto, ruotate appena. La carta di `trick.winning_seat` (P75) ha il **bordo giallo ed è sollevata e un po' più grande** (`trick__card--winner`, marcatore `data-winning`); il segno si sposta quando il server dice che vince un'altra carta; i lettori di schermo sentono "Sta vincendo: …". La presa chiusa usa la stessa evidenza per chi ha preso. Nel 2v2 sul telefono le carte della presa si misurano sulla colonna centrale (container query, `100cqw`): circa 45 px a 360, 60 dai telefoni larghi; altrove come prima
- **Controlli**: solo i test del tavolo, tutti PASS: `test_presa_affiancata.py` **5** nuovi (carte che non si coprono e almeno 44 px, presa in corso e chiusa, 1v1 e 2v2, a 360×640, 390×844, 768×1024, 1024×768, 1280×720, 1440×900, senza scorrimento; evidenza su `winning_seat`, che si sposta e sparisce con la presa vuota; presa chiusa), `test_grafica_tavolo.py` 16, `test_pagina_tavolo.py`, `test_punti_mano.py`, `test_tavolo_telefono.py`, `test_carte_avversari.py`, `test_lancio_carta.py`, `test_momenti_tavolo.py`. `ruff check` dei test pulito. Suite complete non lanciate (su richiesta di Christian)
- **Decisioni prese** (Christian, 03/10/2026): disposizione **a croce** (scartata la fila nell'ordine di gioco, raccomandata da Claude); evidenza **sollevata + bordo** (raccomandazione di Claude; scartata l'etichetta "Vince")
- **Domande nuove**: nessuna
- **Punti delicati**: nel 2v2 sul telefono `.table__center` è un contenitore (`container-type: inline-size`) e si allarga alla colonna (`justify-self: stretch`): la croce non deve mai uscire dalla colonna centrale, altrimenti copre i giocatori ai lati (la colonna è metà del tavolo, circa 156 px a 360). **Difetto trovato, non corretto qui** (è di P74, `table.css`): da computer la mano ha la colonna larga "auto", quindi finché le immagini delle carte non sono caricate le carte in mano sono larghe 27 px invece di 94 e presa e mazzo stanno 45–90 px più in basso; per questo `test_mazzo_finito_resta_il_seme_dov_era_il_mazzo[1280x720-2v2]` fallisce circa una volta su sei, anche su `dev` senza P76
- **Cosa devono fare gli altri**: niente. **Chi è di turno sui documenti**: spuntare P76, lista definitiva in 9.2, in `DECISIONI.md` croce ed evidenza; il difetto della mano da computer (sopra) se Christian lo fa diventare un punto

### P86 — Mazzo più grande, da computer (03/10/2026)

- **Branch**: feature/p86-mazzo-computer
- **File** (lista approvata da Christian per 9.2): modificati `app/static/css/components/trick.css` (una regola da 1024 px in su), `tests/api/test_grafica_tavolo.py`, questo file
- **Cosa cambia**: da 1024 px in su il mazzo è largo **88 px** (prima 60), un po' più grande delle carte della presa (72–80 px); il seme della briscola sopra il mazzo cresce con lui, e a mazzo finito (P77) resta la stessa misura. Sul telefono resta 56 px, sul tablet 60
- **Controlli**: solo i test del tavolo toccati, tutti PASS: `test_grafica_tavolo.py` **16** (il test da computer controlla gli 88 px a 1024×768, 1280×720 e 1440×900, in 1v1 e 2v2, e che il mazzo non tocchi niente; quello del telefono che resti 56 px), più `test_pagina_tavolo.py`, `test_punti_mano.py`, `test_carte_avversari.py`, `test_distribuzione.py` **39**. `ruff check` del test pulito. Suite complete non lanciate (su richiesta di Christian)
- **Decisioni prese** (Christian, 03/10/2026, sulla raccomandazione di Claude): mazzo da **88 px** da computer (scartati 80 e 96). Misurato prima con 72–96 px a 1024×768, 1280×720, 1440×900 e 1920×1080: a tutte le misure il mazzo non tocca presa, ventagli, avatar né la tua mano, e il tavolo non scorre
- **Domande nuove**: nessuna
- **Punti delicati**: nessuno nuovo
- **Cosa devono fare gli altri**: niente. **Chi è di turno sui documenti**: spuntare P86, lista definitiva in 9.2, in `DECISIONI.md` la misura di 88 px

### Documenti: registrati i lotti dal 01/10 sera al 02/10 e aggiunto P91 (02/10/2026)

- **Branch**: docs/lotti-02-10
- **File**: modificati `SCALETTA.md` (tracker, sezione 4 con P88 approvato e il dettaglio di P91, sezione 9 con "Da dove si parte" e la tabella, sezione 9.2 con le liste definitive di P74, P77, P79, P90 e P83 e la voce di P91), `DECISIONI.md` (Interfaccia: P83 nella decisione P33, scelte di P74 e P90; Processo: contratto di P75 e P88), `CLAUDE.md` (riga "Stato", numero dei controlli, 8 punti delicati nuovi), questo file. `DA-DECIDERE.md` non cambia
- **Controlli**: nessuno (soli documenti). Ultimo giro completo 1571 PASS (Giuseppe, P88); poi `api` 320 e `frontend` 185 PASS (Christian, P74)
- **Riepiloghi registrati**: `giuseppe.md` P75, P83, P88; `christian.md` P79, P81, P90, P77, P74; `antonio.md` niente di nuovo
- **Decisioni registrate**: contratto 3.3 di `trick.winning_seat` (P75) e `rating` (P88) **approvato da Christian**; invito ricevuto annullato quando cade la connessione (P83, aggiunta alla decisione P33); tabellone in alto a destra, avatar a sinistra del ventaglio in alto e carte degli avversari da 72 px (P74); "Esci" solo icona sotto 1024 px (P90)
- **Punto nuovo**: **P91** (Christian), suite `frontend` sotto il limite di tempo (tracker, sezioni 4, 9 e 9.2)
- **Domande**: nessuna nuova
- **Cosa devono fare gli altri**: **Giuseppe**: P82, poi D43 e D45 insieme a Christian; se P91 tocca `tests/esegui_tutti.py`, Christian ti avvisa prima

### P74 — Tavolo da computer: avatar, carte degli avversari, "Esci", tabellone e propri punti (02/10/2026)

- **Branch**: feature/p74-tavolo-computer
- **File** (lista approvata da Christian per 9.2): modificati `app/static/css/components/table.css`, `scoreboard.css`, `table-phrases.css`, `tests/api/test_grafica_tavolo.py`, `tests/api/test_punti_mano.py`, questo file. `Table.js` e `test_carte_avversari.py` non sono serviti
- **Cosa cambia** (solo da 1024 px in su, sul telefono niente):
  - **"Esci"** fisso nell'angolo in alto a sinistra; **tabellone** fisso in quello in alto a destra, un po' più grande e allineato a destra;
  - **carte degli avversari** da 56 a **72 px**;
  - **in alto** (avversario nel 1v1, compagno nel 2v2): punti della mano, avatar e nome **a sinistra del ventaglio**; il suo fumetto scende sotto l'avatar;
  - **ai lati** (2v2): avatar subito dentro il ventaglio, verso il centro; i fumetti escono di fianco all'avatar, verso il centro (sopra quello di sinistra ci sono i punti);
  - **in basso**: il tuo avatar a sinistra della mano, i tuoi punti a destra; "Canta" sopra la mano, "Frasi" sopra a destra (lo sposterà P80); il tuo fumetto si allarga verso sinistra, per non coprire la mano.
- **Controlli**: suite `api` **320 PASS** (149 s), `frontend` **185 PASS** (212 s). 10 controlli nuovi: `test_tavolo_da_computer` (1v1 e 2v2 a 1024×768, 1280×720 e 1440×900, con 5 carte agli avversari e un fumetto per ognuno: angoli, 72 px, avatar accanto ai ventagli, tuoi avatar e punti ai lati della mano, nessuna sovrapposizione fra presa, mazzo, ventagli, avatar, nomi, punti, fumetti, mano e pulsanti, niente scorrimento) e `test_sul_computer_i_tuoi_punti_a_destra_della_mano` (e sul telefono ancora sopra). Il giro completo delle 8 suite non l'ho fatto
- **Decisioni prese** (Christian, 02/10/2026, sulle raccomandazioni di Claude): **tabellone in alto a destra** (scartati: a sinistra a metà altezza, in basso a destra); avatar in alto **a sinistra** del ventaglio (scartato: a destra); carte degli avversari **72 px** (scartato: 80)
- **Domande nuove**: nessuna
- **Punti delicati**: da computer "Esci", tabellone e posti degli avversari sono `position: fixed`, come i ventagli: il posto in alto si allinea a `--top-fan-half` e quelli ai lati a `--side-fan-reach` (in `table.css`, misurati con 5 carte da 72 px). **Se cambia la misura delle carte coperte, vanno rimisurati** (lo segnala `test_tavolo_da_computer`). Da computer `.table__me` è `display: contents`, e i suoi figli stanno nella griglia di `.table__mine`: l'elenco delle frasi si apre rispetto a `.table__mine` (P80 lo rifà)
- **Cosa devono fare gli altri**: niente. **Chi è di turno sui documenti**: spuntare P74; in `DECISIONI.md` le tre scelte qui sopra (posizione del tabellone, lato dell'avatar in alto, 72 px)

### P77 — Briscola solo sul mazzo, anche a mazzo finito (02/10/2026)

- **Branch**: feature/p77-briscola-sul-mazzo
- **File** (tutti nell'elenco "probabili" di 9.2): modificati `app/static/js/components/Trick.js` (`EmptyDeck`), `app/static/js/components/Table.js` (tolto `TrumpBadge`), `app/static/css/components/trick.css` (`.deck__slot`), `app/static/css/components/table.css` (tolte le regole `.trump-badge`), `tests/api/test_grafica_tavolo.py`, `tests/api/test_punti_mano.py`, `tests/api/test_pagina_tavolo.py`, questo file
- **Cosa cambia**: il **tondo con il seme** sopra la mano **non c'è più**; a sinistra della tua riga restano solo i tuoi punti della mano (P72). La briscola si vede **solo sul mazzo**; a **mazzo finito**, dov'era il mazzo resta il seme fino a fine mano (`[data-deck-empty]`, con dentro `[data-trump]`; per i lettori di schermo "Mazzo finito. Briscola: …"). Una carta coperta invisibile (`.deck__slot`) tiene il posto e la misura del mazzo, così il seme non si sposta (anche quando P86 ingrandirà il mazzo). Senza briscola, a mazzo finito non c'è niente, come prima
- **Controlli**: suite `api` **310 PASS** (126 s), `frontend` **185 PASS** (201 s). In `api` 5 controlli nuovi al posto di quello vecchio del mazzo finito ( seme dov'era il mazzo, con la stessa posizione e misura, nel 1v1 e nel 2v2 a 360×640 e 1280×720; niente a mazzo finito senza briscola). Il giro completo delle 8 suite non l'ho fatto
- **Decisioni prese**: nessuna (spec del punto, decisione del 01/10)
- **Domande nuove**: nessuna
- **Punti delicati**: marcatori cambiati: `data-trump-badge` non esiste più; il seme a mazzo finito è `[data-deck-empty] [data-trump]` (`[data-deck-count]` c'è solo con carte nel mazzo). Chi misura il mazzo (P86) deve tenere conto anche di `.deck--empty`
- **Cosa devono fare gli altri**: niente. **Chi è di turno sui documenti**: spuntare P77 e scrivere i file nella nota del tracker

### P90 — Tavolo sul telefono: via il tabellone, "Esci" che non si sovrappone (02/10/2026)

- **Branch**: fix/p90-telefono-tabellone
- **File** (lista approvata da Christian per 9.2): modificati `app/static/css/components/scoreboard.css`, `app/static/css/components/table.css`, `app/static/js/components/Table.js`, `tests/frontend/test_carte_avversari.py` (con l'ok di Christian), questo file; creato `tests/api/test_tavolo_telefono.py`
- **Cosa cambia**: sotto 1024 px il **tabellone non c'è** (`display: none`): il punteggio si legge nel riepilogo di fine mano, e per i lettori di schermo resta lì. **"Esci"** è un tondo da 44 px con la sola icona; la scritta c'è ancora, ma solo per i lettori di schermo (`.table__leave-text`, nascosta come `visually-hidden`). Da computer non cambia niente
- **Causa** [T]: con 5 carte all'avversario in alto, tra "Esci" e il ventaglio restavano 7 px a 360×640, e a 320×568 "Esci" copriva una carta. Con il carattere di sistema più grande succede anche su telefoni più larghi [D]. Il tabellone invece si accavallava al ventaglio in alto
- **Controlli**: suite `api` **306 PASS** (15 nuovi: a 320×568, 360×640, 390×844, 412×915, 768×1024 e 844×390, nel 1v1 e nel 2v2, con 5 carte e nomi lunghi: niente tabellone, "Esci" tondo, niente sopra "Esci", almeno 24 px dal ventaglio; da computer tabellone e scritta; riepilogo con il punteggio a 360×640); suite `frontend` **185 PASS** in 222 s. **Attenzione**: oggi la stessa suite ha messo tra 187 e 222 s (limite 240), e due giri si sono fermati al limite. Conviene un punto nuovo che la alleggerisca (per esempio spostando in `api` qualche file lungo del tavolo) o che alzi `SUITE_TIMEOUT`. `test_carte_avversari.py` controllava "la barra sta sopra il ventaglio" toccando il tabellone a 360×640: ora quel controllo si fa a 1280×720. Il giro completo delle 8 suite non l'ho fatto
- **Decisioni prese** (Christian, 02/10/2026, sulla raccomandazione di Claude): sotto 1024 px "Esci" ha **solo l'icona**. Scartata l'alternativa di far scendere il ventaglio sotto "Esci", che toglieva circa 50 px al centro del tavolo
- **Domande nuove**: nessuna
- **Punti delicati**: ingrandire il carattere della pagina (`font-size` su `html`) non cambia il tavolo, che è misurato in px: per provare il "carattere grande" del telefono serve un margine (qui 24 px), non quel trucco. **P87** ridisegna "Esci": deve tenere il tondo sotto 1024 px (lo controlla `test_tavolo_telefono.py`)
- **Punto nuovo proposto** (Christian, 02/10/2026), da aggiungere al tracker: **P91 (Fase 3, C) — Suite `frontend` sotto il limite di tempo** · piccolo · decisione: no. *Cosa e perché*: la suite dura da 187 a 222 s contro i 240 di `SUITE_TIMEOUT`, e il 02/10 due giri si sono fermati al limite (su `test_frasi_pagina.py` e `test_banner_connessione.py`, che da soli passano). Si spostano in `api` i file lunghi del tavolo che non usano MySQL (per esempio `test_momenti_tavolo.py`, `test_lancio_carta.py`, `test_distribuzione.py`), misurando prima la durata di ciascuno, e si capisce perché a volte un test resta fermo fino al limite. *File*: i test spostati, forse `tests/esegui_tutti.py`. *Fatto quando*: la suite `frontend` sta sotto i 170 s e la suite `api` sotto i 200 s, per 3 giri di fila
- **Cosa devono fare gli altri**: niente. **Chi è di turno sui documenti**: spuntare P90; la lista dei file in 9.2; in `DECISIONI.md` "Esci" con la sola icona sotto 1024 px; aggiungere **P91** (testo qui sopra) al tracker e alla sezione 9 come punto di Christian

### P81 — La tastiera del telefono si chiude a ogni messaggio della chat (02/10/2026)

- **Branch**: fix/p81-tastiera-chat
- **File**: modificati `app/static/js/components/ChatWindow.js`, `app/static/css/components/chat.css` (**fuori elenco**, con l'ok di Christian: una regola), `tests/frontend/test_chat_pannello.py` (2 test nuovi), questo file
- **Causa** [T]: non era la casella spenta (l'ipotesi del punto): durante l'invio si spegne già solo "Invia". Toccando "Invia" il fuoco passava dalla casella al pulsante, e il telefono chiudeva la tastiera; poi `input.focus()` la riapriva. Un secondo tocco mentre il messaggio parte cade sul pulsante spento, e Chrome non manda eventi a un pulsante spento: anche lì la casella perdeva il fuoco
- **Correzione**: il modulo della chat blocca il `mousedown` fuori dalla casella (il pulsante non prende il fuoco e il clic resta). In `chat.css`, `.chat__form button:disabled { pointer-events: none; }`, così un tocco sul pulsante spento arriva al modulo. La regola contro il doppio invio e quella di P33 (senza connessione) non cambiano
- **Controlli**: suite `frontend` **185 PASS** in 188 s (2 nuovi: casella con il fuoco dopo un clic vero su "Invia", anche mentre si aspetta la risposta; doppio clic con un solo messaggio e nessuna perdita del fuoco). Senza la correzione falliscono tutti e due [T]. Un giro prima si era fermato al limite di 240 s su `test_banner_connessione.py` (il file da solo passa 3 volte su 3): è il blocco casuale già visto in P79, che conviene seguire. Il giro completo delle 8 suite non l'ho fatto
- **Decisioni prese**: nessuna (spec del punto)
- **Domande nuove**: nessuna
- **Punti delicati**: un test del browser che manda un messaggio in chat deve azzerare il limite di 1 al secondo (`chat_service.rate_limit.give_back`), altrimenti fallisce a volte, quando parte meno di un secondo dopo il messaggio del test prima (succedeva 4 volte su 6 con il server rallentato). Un clic che deve spostare il fuoco come un tocco vero va fatto con `Input.dispatchMouseEvent`, non con `element.click()`
- **Cosa devono fare gli altri**: niente. **Chi è di turno sui documenti**: spuntare P81; lista dei file con `chat.css`

### P79 — Carte bianche per qualche secondo al tavolo (02/10/2026)

- **Branch**: fix/p79-carte-bianche
- **File**: modificati `app/static/js/components/Card.js` (`preloadCardImages`), `app/static/js/pages/game.js` (la chiama dopo il `load` e mette `data-cards-ready` su `[data-table]`), questo file; creato `tests/api/test_carte_pronte.py` (nella suite `api` e non in `frontend`, perché dura circa 35 s e `frontend` è vicina ai 240 s). Tutti nell'elenco "probabili" di 9.2 tranne il test nuovo, che il punto prevede
- **Causa** [T]: l'immagine di una carta si scaricava solo la prima volta che la carta compariva (pescata, giocata dall'avversario). Con la rete rallentata a 1,5 s per richiesta, 5 s dopo l'apertura del tavolo, 5 carte su 15 erano ancora bianche nel momento in cui comparivano
- **Correzione**: appena la pagina del tavolo ha finito di caricarsi, si scaricano le 40 facce, il dorso e i 4 assi "figura" (briscola e canti). Le immagini restano in memoria, così il browser non le butta via. Il peso è quello di P35: sono gli stessi file, scaricati prima. Partire dopo il `load` evita che ogni apertura della pagina aspetti 45 immagini: prima ogni test del tavolo era più lento di circa il 14% [T]
- **Controlli**: suite `api` 291 PASS, `frontend` 183 PASS (3 nuovi: carte nuove, briscola e canto mai bianchi con la rete lenta, segnale anche senza rete lenta). Il primo giro di `frontend` si è fermato al limite di 240 s con 2 FAIL (`test_frasi_pagina.py`), che da soli passano; al secondo giro era tutto PASS. Il giro completo delle 8 suite non l'ho fatto
- **Decisioni prese**: nessuna (spec del punto)
- **Domande nuove**: nessuna
- **Punti delicati**: le immagini create con `new Image()` fanno aspettare il `load` della pagina, che `Browser.open` dei test attende: uno scaricamento grande all'avvio va fatto dopo il `load`. Nei test la rete lenta si ottiene con `Network.emulateNetworkConditions` (dopo `Network.enable`)
- **Cosa devono fare gli altri**: niente. **Chi è di turno sui documenti**: spuntare P79; lista definitiva dei file in 9.2

### Documenti: seconda lista della prova a mano del 01/10 (01/10/2026)

- **Branch**: docs/cose-da-sistemare-01-10-b
- **File**: modificati `SCALETTA.md` (tracker, sezione 4 in fondo a "Correzioni e richieste dalla prova a mano del 01/10/2026", sezioni 9 e 9.2), `DECISIONI.md` (Interfaccia), `CLAUDE.md` (riga "Stato"), questo file
- **Controlli**: nessuno (soli documenti)
- **Punti nuovi**: Giuseppe **P88** (rating dei giocatori nella vista: oggi non c'è; contratto da approvare insieme); Christian **P86** (mazzo più grande da computer), **P87** ("Esci", tabellone e punti della mano più moderni e minimal: stili proposti nel punto), **P89** (rating di ogni giocatore umano al tavolo da computer, dopo P88), **P90** (sul telefono via il tabellone, il punteggio resta nel riepilogo di fine mano; "Esci" che non si sovrappone)
- **Decisioni registrate**: "Seconda lista del tavolo" in `DECISIONI.md` (cambia D44 solo sul telefono: niente tabellone)
- **Domande**: nessuna nuova
- **Cosa devono fare gli altri**: **Giuseppe**: P88 (prima il nome del campo e "provvisorio" sì o no, da approvare con Christian); meglio subito dopo P75, perché tocca gli stessi esempi della vista (non serve aspettare P84)

### Documenti: punti nuovi dalla prova a mano del 01/10 (01/10/2026)

- **Branch**: docs/cose-da-sistemare-01-10
- **File**: modificati `SCALETTA.md` (obiettivo: consegna spostata; tracker; sezione 4, nuova parte "Correzioni e richieste dalla prova a mano del 01/10/2026"; sezioni 9 e 9.2), `DECISIONI.md` (Progetto, Interfaccia, Gioco), `DA-DECIDERE.md` (D1, D45 nuova), `CLAUDE.md` (Progetto e riga "Stato"), questo file. La lista di partenza è in `cose-da-sistemare.txt` (non tracciato)
- **Controlli**: nessuno (soli documenti); ultimo giro completo 1526 PASS (P68), più gli 8 di P72
- **Punti nuovi**: Giuseppe **P75** (carta che sta vincendo la presa nella vista), **P82** (giocatori online veri senza login: oggi senza login si vede il 24 finto di `home_esempio.json`), **P83** (invito accettato e poi annullato: chi ha accettato resta ad aspettare; visto nel 2v2, da provare anche nel 1v1), **P84** ("Cala le carte": regola, motore e stanza); Christian **P74** (tavolo da computer), **P76** (presa affiancata e carta che vince evidenziata), **P77** (briscola solo sul mazzo), **P78** (animazioni più realistiche), **P79** (carte bianche per qualche secondo), **P80** (frasi del tavolo di lato da computer), **P81** (tastiera della chat sul telefono), **P85** (pulsante "Cala le carte")
- **Decisioni registrate**: consegna spostata (nuova data da fissare); tavolo da computer (da 1024 px in su); presa affiancata con la carta vincente decisa dal server (cambio del contratto 3.3 approvato da Giuseppe e Christian); briscola solo sul mazzo, che resta a mazzo finito (cambia P71); animazioni in fila e pescata una carta alla volta; frasi del tavolo di lato da computer; regola "Cala le carte" (solo a mazzo finito; carte del giocatore o della squadra, compagno compreso, che vincono ogni presa rimasta in qualunque ordine; mai se un avversario può ancora cantare)
- **Domande**: **D45** nuova (dettagli di "Cala le carte": quando si preme, presa iniziata, chi preme nel 2v2, canto della propria squadra, come si mostrano le carte calate); D1 aggiornata
- **Cosa devono fare gli altri**: **Giuseppe**: in "Da dove si parte" prima P83, P82 e P75 (P75 sblocca P76 di Christian), poi D45 insieme e P84; D43 e P68 restano. P82 e P83 possono toccare `home.js`, `InviteDialog.js` o `ModeModal.js`: avvisa Christian prima

### Documenti: registrati i lotti dal 29/09 al 01/10 (01/10/2026)

- **Branch**: docs/registra-30-09-01-10
- **File**: modificati `SCALETTA.md` (tracker, sezioni 3, 4, 5, 9 e 9.2), `DECISIONI.md` (Interfaccia, Gioco, Processo), `DA-DECIDERE.md` (D31, D43; D44 tolta), `CLAUDE.md` (riga "Stato", Testing, punti delicati), `docs/CONTRATTO-SOCKET.md` (3.3: `hand_points`, chiesto da Giuseppe a chi è di turno), questo file
- **Controlli**: nessuno (soli documenti); ultimo giro completo 1526 PASS (P68), più gli 8 di P72 (suite `api` e `frontend` PASS)
- **Registrati**: `giuseppe.md` da P61 a P68 (P61, P59 con il runner a 240 s, P66, P65, P63, P64, P67, P68); `christian.md` da P69 a P72 (P69, P71, i tre lotti di P70, P34, P43, P72); niente di nuovo in `antonio.md`
- **Tracker**: spuntati P43, P59, P61, P63, P64, P65, P66, P67, P69, P70, P71, P72; **non spuntati** P34 (manca la prova su un telefono vero) e P68 (in `dev` a metà: strategia della CPU da rifare); P53 barrato (tolto il 30/09). Liste definitive in 9.2 per P34 (parte nel codice), P43, P59, P61, P64, P65, P66, P68, P69–P72. "Da dove si parte" riscritto
- **Decisioni registrate**: tocchi a fine mano (P69), grafica del tavolo (P71), animazioni (P70), avatar in stile piatto (P43), niente tema scuro (P53), D44 chiusa (punti al tavolo), etichetta dei punti (P72), P64 confermata per ogni mano, dettagli del 2v2 con più amici (P59), runner a 240 s, cambiamenti al contratto approvati (P59, P65, P67)
- **Domande**: D44 chiusa; D43 aggiornata (strategia "giocatore medio" scartata il 01/10, le altre proposte di Giuseppe da discutere, preferenza per `cpu: true`); D31 aggiornata (resta da tagliare, eventualmente, solo la CPU)
- **Punti delicati nuovi in `CLAUDE.md`**: amici e avvisi (P63, P65), 2v2 con più amici (P59), punti della mano (P67, P72), animazioni (P70), tocchi al tavolo (P69, P34), avatar (P43), CPU (P68); aggiornati "Regole del canto" (P64) e "Timer" (P66)
- **Cosa devono fare gli altri**: **Giuseppe**: leggi "Da dove si parte" in `SCALETTA.md`: prima D43 insieme, poi P68 rifatto, poi P38 e P39; il contratto 3.3 ora ha `hand_points`

### P72 — Punti della mano in corso al tavolo (01/10/2026)

- **Branch**: feature/p72-punti-mano
- **File** (lista definitiva per 9.2, confermata da Christian prima di cominciare): creato `tests/api/test_punti_mano.py`; modificati `app/static/js/components/Table.js`, `app/static/js/pages/game.js`, `app/static/css/components/table.css`, questo file. **Non toccati**, anche se nella lista "probabile": `Hand.js`, `Scoreboard.js`, `HandSummary.js`, `hand.css`, `scoreboard.css` (per D44 tabellone e riepilogo restano com'erano). Il test sta nella suite `api` e non in `frontend`, che è già a 194 s su 240 di limite (come `test_grafica_tavolo.py`, P71)
- **Controlli**: suite `api` 288 PASS (8 nuovi), suite `frontend` 180 PASS, `ruff check .` pulito; tutte le suite non lanciate. Senza le modifiche i test nuovi falliscono tutti e 8 [T]
- **Fatto** (D44, campo `hand_points` di P67): (1) i **tuoi punti** (nel 2v2 quelli della tua squadra) nella riga sopra la mano, a sinistra, accanto al seme della briscola; (2) nel **1v1** quelli dell'avversario a sinistra del suo avatar, sotto il suo ventaglio; nel **2v2** quelli della squadra avversaria **una volta sola**, sopra il giocatore a sinistra, accanto al suo ventaglio; (3) etichetta tonda chiara come quella dei canti: **sul telefono solo il numero**, **da 1024 px in su "N punti"**; per i lettori di schermo la frase intera ("I tuoi punti in questa mano: 21", "Punti degli avversari in questa mano: 11"); (4) i numeri cambiano a ogni vista nuova; (5) **a fine mano**, finché si vedono l'ultima presa e il riepilogo, restano i punti della mano appena chiusa (`last_hand`, `hand_total`); chiuso il riepilogo, la mano nuova parte da 0
- **Cosa provano i test**: posto e numero di ogni etichetta nel 1v1 e nel 2v2 (due in tutto, mai a destra o in alto nel 2v2); testo sul telefono, a 768 px e a 1440 px; etichette per i lettori di schermo; numero che cambia con la vista; fine mano (ultima presa, riepilogo, poi 0); a 7 misure dello schermo nessuna etichetta esce dallo schermo o copre ventagli, giocatori, briscola, frasi, presa, mazzo, mano, punteggio ed "Esci", e il tavolo non scorre
- **Decisioni prese** (Christian, 01/10/2026; da registrare in `DECISIONI.md`, Interfaccia): solo il numero sul telefono e "N punti" sul computer; a fine mano restano i punti della mano chiusa fino alla fine del riepilogo (raccomandazione di Claude, applicata). Scelta di Claude: nel 1v1 l'etichetta dell'avversario sta **a sinistra** del suo avatar e non sopra, perché sopra alzava il suo posto e sui portatili bassi (1280×720) la presa lo toccava (lo ha trovato `test_grafica_tavolo.py`) [T]
- **Altre decisioni del 01/10/2026** (di Christian, per chi è di turno sui documenti e per Giuseppe):
  - **D43 resta aperta, e la strategia della CPU di P68 non va bene**: contro la CPU si vince troppo facilmente. Le altre scelte di D43 proposte da Giuseppe (solo 1v1, partita non salvata, avvio dalla carta-modal, nome "CPU" e attese) non sono state discusse: restano proposte. Serve un modo diverso, più forte, di scegliere le mosse (da cercare insieme). In `DA-DECIDERE.md`, D43, va aggiunto che la proposta "giocatore medio" è stata scartata il 01/10/2026 perché troppo facile da battere;
  - **contratto di P67**: **ok di Christian** al campo `hand_points` e alle due frasi del 3.3 proposte da Giuseppe nel riepilogo di P67. Con l'ok di Giuseppe il cambiamento vale (regola del 29/09/2026): chi è di turno aggiorna `docs/CONTRATTO-SOCKET.md`;
  - **contratto di P68** (`cpu:start`, CPU con `user_id` 0): **resta aperto**, insieme a D43;
  - **CPU nella vista**: Christian preferisce un campo esplicito **`cpu: true`** per giocatore, se non complica troppo le cose, invece di riconoscerla da `user_id` 0
- **Domande nuove**: nessuna (D43 resta aperta, con la strategia da rifare)
- **Punti delicati**: i punti a fine mano li sceglie `game.js` (`moments.handPoints`, da `nextSummary || summary`); `Table.js` usa quelli, oppure `hand_points` della vista. Il posto dell'avversario in alto non deve diventare più alto (lo misura `test_grafica_tavolo.py` a 1280×720): per questo nel 1v1 i punti stanno accanto all'avatar e non sopra. Nel 2v2 il fumetto di una frase di chi sta a sinistra esce sopra il suo avatar e copre l'etichetta dei punti finché si vede
- **Cosa devono fare gli altri**: **Giuseppe**: (1) la strategia della CPU è da rifare (D43, sopra): parliamone prima di cambiare `cpu.py`; (2) per la vista della CPU va bene `cpu: true` per giocatore, se per te non complica troppo; (3) il contratto di P67 ha il mio ok. **Chi è di turno sui documenti**: spuntare P72, lista definitiva in 9.2, le decisioni qui sopra

### P43 — Immagini degli avatar (30/09/2026)

- **Branch**: feature/p43-avatar
- **File** (lista definitiva per 9.2, confermata da Christian prima di cominciare): creati `app/static/img/avatars/*.svg` (12, uno per codice di `avatars.py`, 18 KB in tutto), `app/static/js/components/Avatar.js`, `app/templates/partials/avatar.html` (macro per i template), `tests/frontend/test_avatar.py`; modificati `app/templates/partials/navbar.html`, `app/templates/profile/settings.html` (di Antonio, P17), `app/static/js/components/FriendsPanel.js`, `ModeModal.js`, `QueueOverlay.js`, `Table.js`, `app/static/css/components/navbar.css`, `friends-panel.css` (solo il commento), `app/static/css/pages/profile.css`, `app/services/avatars.py` (solo il commento). **Non toccati**, anche se nella lista: `home_esempio.json` e `table.css` (non serviva, vedi sotto)
- **Controlli**: suite `api` 280 PASS, suite `frontend` 180 PASS (22 nuovi), `ruff check .` pulito; tutte le suite non lanciate
- **Fatto**: (1) **12 avatar in SVG disegnati da Claude** (D29), stile piatto: un tondo del colore del seme (coppe rosso, denari giallo, spade blu, bastoni verde); i 4 semi con il simbolo al centro; i Re con corona e barba, i Fanti con berretto e piuma, i Cavalli come testa di cavallo con le briglie; nelle figure un piccolo simbolo del seme. Si leggono anche a 24 px [T, foto]. Lo script che li genera sta fuori dal progetto, come quello delle carte (P35); (2) **un solo posto decide immagine o iniziale**: `Avatar(user, className)` in `Avatar.js` per tavolo, pannello amici, carta-modal e schermata di coda (prima ognuno ricalcolava l'iniziale per conto suo); la macro `avatar(username, code, class)` di `partials/avatar.html` per navbar, pannello statistiche e impostazioni. Senza avatar il codice HTML dell'iniziale resta identico a prima; (3) nelle **impostazioni** ogni scelta mostra l'immagine sopra il nome (tondo da 44 px); (4) al tavolo l'avatar di chi è scollegato diventa grigio come prima
- **Cosa provano i test**: un'immagine per ogni codice e nessuna in più; peso sotto 300 KB; ogni SVG valido, 64×64, senza risorse esterne né `--` nei commenti; immagini servite come `image/svg+xml`; con Node, `AVATAR_CODES` di `Avatar.js` uguale all'elenco di `avatars.py` e un codice fuori elenco senza immagine; i quattro componenti usano `Avatar.js`; navbar, statistiche e impostazioni con l'immagine, e con l'iniziale senza avatar; nel browser il tavolo 2v2 a 360×640 e 1440×900 con le immagini caricate che riempiono il tondo, e l'iniziale per il codice sbagliato
- **Decisioni prese**: stile piatto degli avatar (Christian, sulla raccomandazione di Claude). **D29 è chiusa del tutto** (da registrare in `DECISIONI.md`, Interfaccia)
- **Altre decisioni del 30/09/2026** (di Christian, per chi è di turno sui documenti):
  - **P53 tagliato** (tema scuro): deciso da tutti e tre, non si vuole nessun tema scuro. Va barrato nel tracker, in 4, 9 e 9.2 (come P60); in `DECISIONI.md` la decisione del 26/09 "Tema chiaro e scuro automatico" e quella del 27/09 "Tema scuro rimandato" diventano "solo tema chiaro"; in D31 P53 non è più da tagliare, perché è già tolto. Il commento su P53 in cima a `variables.css` resta, fino a un punto che tocca quel file;
  - **D44 chiusa**: (1) il **tabellone** in alto resta: mostra il totale della partita, si aggiorna solo a fine mano e riparte dal totale della mano prima (com'è già oggi, `scores`); (2) il **riepilogo di fine mano** resta com'è; (3) il server manda **i punti della mano in corso di tutte e due le squadre** (carte prese più canti), che a ogni mano ripartono da zero e salgono in tempo reale a ogni presa e canto. Cambia la frase del contratto 3.3 "si nascondono i punti delle carte prese" (P67: ok di Giuseppe e Christian). (4) **Dove si vedono al tavolo** (P72): nel **1v1** i tuoi punti sopra la tua mano, quelli dell'avversario **sotto la sua mano** (il ventaglio in alto); nel **2v2** i punti della tua squadra (tu e il compagno di fronte) sopra la tua mano, quelli della squadra avversaria (i giocatori a destra e a sinistra) **accanto alla mano del giocatore a sinistra**, una volta sola. Cambia la decisione del 29/09 "ogni giocatore vede solo i punti della propria squadra" (`DECISIONI.md`, Interfaccia, "Ritocchi del tavolo"): ora si vedono i punti di tutte e due le squadre;
  - **D43**: la decisione è comune ai tre e dipende da come la CPU sceglie le carte; resta aperta;
  - la prova dal telefono di P34 e P69–P71 la fa Christian (30/09); i punti restano di Christian.
- **Domande nuove**: nessuna
- **Punti delicati**: `AVATAR_CODES` in `Avatar.js` è una copia dell'elenco di `avatars.py`: un codice nuovo va in tutti e due e ha bisogno del suo SVG (lo controlla `test_avatar.py`). Le regole `.avatar--img` e `.avatar__img` stanno in `navbar.css` ma valgono per tutti gli avatar (anche `.mini-avatar` e `.avatar-choice__face`). Gli esempi `amici_esempio.json`, `home_esempio.json` e `vista_2v2.json` usano `cavallo_spade`, che non esiste tra i 12: non li ho toccati, e la pagina mostra l'iniziale. Al tavolo le immagini degli avatar si ricreano a ogni vista: per non farle lampeggiare hanno `decoding="sync"`; se sul telefono lampeggiano lo stesso, si estende il riuso delle immagini di P70 (`reuseCardImages` in `Card.js`). La suite `frontend` ora dura **196 s su 240** di limite: al prossimo test lungo nel browser va controllata
- **Cosa devono fare gli altri**: **Giuseppe**: per P67 vale D44 qui sopra (punti in corso di **tutte e due** le squadre nella vista, da zero a ogni mano; la pagina li mostra per squadra, quindi basta un valore per squadra, come `scores`). Nella suite `frontend`, attenzione al tempo (196 s)

### P34 — Rifinitura mobile e accessibilità (29/09/2026)

- **Branch**: fix/p34-rifinitura
- **File** (lista definitiva per 9.2, confermata da Christian): creato `tests/frontend/test_rifinitura.py`; modificati `app/static/js/components/Table.js`, `FriendsPanel.js`, `TablePhrases.js` (solo il commento), `app/templates/main/index.html`, `app/templates/game/table.html`
- **Controlli**: suite `frontend` 158 PASS (8 nuovi), suite `api` 280 PASS, `ruff check` pulito; tutte le suite non lanciate
- **Come l'ho cercato**: un controllo a mano, fuori dal progetto, di 9 pagine e finestre a 360×640 e 390×844 (home, statistiche, amici, carta-modal, impostazioni, accesso, registrazione, tavolo 1v1 e 2v2): nessuna pagina scorre e niente esce dallo schermo (tranne le carte decorative dello sfondo della home, volute) [T]; accessibilità con **axe-core** 4.10.2 (caricato solo nel browser di prova, **non** nel repository) [T]
- **Fatto**: (1) **titolo principale** (`<h1>`, visibile solo ai lettori di schermo) nella home e al tavolo, che non l'avevano; (2) le **icone dei canti** accanto al nome hanno `role="img"`: prima l'etichetta "Ha cantato 40 a coppe" su uno span senza ruolo non si leggeva; (3) **"indietro" dopo un ricaricamento** con il pannello amici aperto: il browser teneva nella cronologia lo stato vecchio del pannello (`friendsPanel: 'chat'`) e, riaperto il pannello, "indietro" non lo chiudeva; ora all'avvio lo stato vecchio si toglie (il test fallisce senza la correzione [T]); (4) commento di `TablePhrases.js` aggiornato a P71; (5) test: una carta si gioca con la sola tastiera (Tab e Invio)
- **Già a posto**, nessuna modifica: la lista del pannello amici che una risposta vecchia sovrascrive (segnalato da Giuseppe in P65): `FriendsPanel.js` ha già il controllo sull'ultima lettura (`loadSeq` in `load()`) [L]; il difetto della presa sui portatili bassi, sparito con P70 (secondo lotto)
- **Resta per chiudere P34**: il "Fatto quando" chiede la prova **su un telefono vero**, e il **contrasto** delle scritte sopra il panno axe non lo sa misurare (lo sfondo è un'immagine): da guardare a occhio sul telefono. **Non spuntare P34** finché non è fatta la prova dal telefono
- **Decisioni prese**: nessuna
- **Domande nuove**: nessuna
- **Punti delicati**: nei test del browser `Browser.key` di `tests/browser.py` manda il tasto senza carattere: per "premere" un pulsante con Invio serve anche `text` con il carattere a capo (`chr(13)`), come in `test_rifinitura.py`
- **Cosa devono fare gli altri**: **Giuseppe, richiesta di Christian** (29/09/2026, sera: Christian esce): **prova tu dal telefono** P34 e la grafica nuova del tavolo (P69, P70, P71), in una partita vera con due telefoni (o telefono e PC) sulla stessa rete. Cosa guardare, e cosa scrivere nel tuo riepilogo per ogni voce (va / non va, con il telefono usato):
  - **zoom** (P69): al tavolo il doppio tocco e il tocco lungo su una carta non ingrandiscono e non aprono menù; lo zoom con due dita funziona ancora;
  - **fine mano** (P69): durante l'ultima presa e il riepilogo le carte non si giocano; con "Ok" si torna a giocare;
  - **frasi a raffica** (P69, ancora aperto): toccando più volte il pulsante delle frasi partono più frasi di una ogni 3 secondi? I fumetti arrivano davvero anche all'altro telefono?
  - **grafica** (P71): seme della briscola sopra il mazzo e nel tondo a sinistra sopra la mano (dopo il canto del 40); niente "Carte franche" né "mazziere"; mazzo a destra e più grande; carte giocate più grandi; pulsante delle frasi sopra la mano a destra, elenco verso l'alto;
  - **animazioni** (P70): lancio fluido della carta che ruota; ventagli degli avversari dal bordo (in alto dietro la barra, nel 2v2 ai lati); pescata dopo ogni presa (prima chi ha preso); mescolata e distribuzione dopo il riepilogo; niente scatti o carte che ripartono quando arriva un fumetto;
  - **carte bianche** (P70): le carte diventano ancora bianche per un attimo? (la correzione non si poteva provare sul PC);
  - **P34**: tutte le pagine (home, pannelli, impostazioni, accesso, tavolo) si usano bene sul telefono; le scritte sopra il panno si leggono (contrasto); dopo aver ricaricato la pagina con la chat aperta, "indietro" chiude il pannello amici.
  Se qualcosa non va, **non correggere i file del tavolo** (sono di Christian): scrivilo nel riepilogo, lo sistemo io

### P70 (terzo lotto) — Mescolata e distribuzione (29/09/2026)

- **Branch**: fix/p70-distribuzione
- **File**: creato `tests/frontend/test_distribuzione.py`; modificati `app/static/js/pages/game.js`, `app/static/js/components/Hand.js`, `Trick.js`, `Table.js`, `app/static/css/components/trick.css`, `hand.css`
- **Controlli**: **1397 PASS** in 8 suite, tutto PASS (giro completo chiesto da Christian; 6 test nuovi nella suite `frontend`), `ruff check` pulito
- **Fatto**: (1) a ogni mano nuova (non alla prima vista) le carte della mano nuova restano **nascoste** finché si vedono l'ultima presa e il riepilogo; (2) chiuso il riepilogo (da solo dopo 5 s o con "Ok") il mazzo si **mescola**: due mezzi mazzi escono ai lati e rientrano, due volte (0,6 s, `SHUFFLE_MS` = `deck-riffle`, un test li confronta); (3) poi le carte partono **una alla volta**, a giro dal giocatore dopo il mazziere, 0,08 s l'una dall'altra (`DEAL_STEP_MS`), con le animazioni della pescata: nel ventaglio dell'avversario o nella tua mano; in tutto circa 1,8 s nel 1v1 e 2,6 s nel 2v2; (4) fino alla fine un tocco sulle proprie carte non gioca niente; (5) come per il resto di P70, un ridisegno a metà non fa ripartire niente, e con "riduci movimento" non c'è distribuzione. **P70 è finito** (tre lotti)
- **Decisioni prese**: nessuna nuova (distribuzione dopo il riepilogo, decisa da Christian nel primo lotto); scelte di Claude: mescolata di 0,6 s con due mezzi mazzi, 0,08 s tra una carta e l'altra
- **Domande nuove**: nessuna
- **Punti delicati**: la distribuzione aspetta in `game.js` (`dealWaiting`) e parte in `render` quando non ci sono più presa chiusa né riepilogo (`startDeal`); l'ordine delle carte lo calcola `dealOrder` da `dealer_seat` e dalle carte in mano di ognuno. Chi apre la mano nuova perde fino a circa 8,5 s dei suoi 30 (ultima presa, riepilogo, distribuzione): il timer lo conta il server, come deciso
- **Cosa devono fare gli altri**: niente

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
