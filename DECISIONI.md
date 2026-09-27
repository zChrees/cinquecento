# Decisioni prese

> **Non riaprirle senza una richiesta esplicita dell'utente.** Si può segnalare un rischio residuo, ma senza riproporre soluzioni già scartate.
>
> Formato: una riga per decisione, con **data** e **motivo**. Le nuove decisioni si aggiungono in fondo alla sezione giusta.

## Progetto e tempi

- 26/09/2026 — Progetto con **scadenza tra una settimana** (circa 03/10/2026; la data esatta è in `DA-DECIDERE.md`), **3 persone** nel gruppo. Motivo: vincolo del progetto.
- 26/09/2026 — **Prima versione**: registrazione e login, stanze private con codice, matchmaking 1v1 e 2v2, statistiche base del profilo. La classifica e il resto arrivano solo se avanza tempo. Motivo: il minimo utile che sta in una settimana. **Aggiornata il 27/09/2026**: niente più stanze private con codice (vedi sotto).
- 26/09/2026 — **Prima versione allargata**: entrano anche **amici** (richieste di amicizia, lista, chi è online, inviti a 1v1 e 2v2), **chat tra amici**, **classifica**, pagina **Partite** (storico) e pagina **Regole** con mini-tutorial. Motivo: scelta dell'utente. Il rischio sui tempi è segnalato in `SCALETTA.md` (ordine di taglio in D31). **Aggiornata il 27/09/2026**: classifica, pagina Partite e pagina Regole tolte (vedi sotto).
- 26/09/2026 — **Utenti**: per ora amici e compagni, meno di 50 connessi insieme. L'obiettivo futuro è un gioco pubblico, quindi le scelte di oggi non devono impedire di crescere. Motivo: la scala attuale permette un solo processo server.
- 27/09/2026 — **Tolte dalla prima versione**: **classifica**, **stanza privata con codice**, pagina **Partite** (storico) e pagina **Regole**. Per questo non c'è più la bottom navbar. Si gioca solo dalla home: **Partita Veloce** (coda di matchmaking) o **Gioca con un amico** (invito). Motivo: scelta dell'utente, per concentrarsi sulla home e sul gioco.

## Tecnologia

- 26/09/2026 — Stack vincolato: **HTML, CSS, JavaScript vanilla** (ES modules, nessun framework né bundler), **Python + Flask**, **MySQL**. Motivo: vincolo imposto al progetto.
- 26/09/2026 — **Estensioni Flask ammesse**: Flask-SocketIO, Flask-Login, Flask-SQLAlchemy, Flask-WTF, e PyMySQL come driver MySQL. Motivo: fanno risparmiare molto lavoro e restano nell'ecosistema Flask.
- 26/09/2026 — **Python 3.14** (quella già installata sul PC di Christian, la 3.14.4), **installata a mano** da tutti alla stessa versione. Niente `uv`. Motivo: scelta dell'utente, per semplicità.
- 26/09/2026 — **MySQL 8.0**, installato a mano da tutti. Niente Docker. Motivo: è già installato e non si aggiungono strumenti nuovi.
- 26/09/2026 — Flask-SocketIO in **modalità `threading`**, **un solo processo**, un lock per ogni stanza di gioco. Motivo: con meno di 50 utenti basta un processo, e `gevent` potrebbe non supportare ancora bene Python 3.14.
- 26/09/2026 — **Server autoritativo**: il client invia solo azioni, e ogni giocatore riceve solo la propria vista (mai le carte altrui), comprese le mosse legali. Motivo: evitare trucchi e fughe di informazioni.
- 26/09/2026 — **Motore di gioco in Python puro** (`app/game/engine/`), senza Flask né database. Motivo: si può testare da solo, e si riusa per la mossa automatica e per i bot.
- 26/09/2026 — **Rating Glicko-2**, separato per 1v1 e 2v2. Il pareggio vale 0.5. Motivo: gestisce l'incertezza dei giocatori nuovi e si adatta alle squadre meglio dell'Elo.
- 26/09/2026 — **Architettura modulare**: app factory + blueprint per dominio. Livelli routes/sockets → services → repositories → MySQL. JS con un entry point per pagina. CSS diviso in base, componenti e pagine. Motivo: richiesta esplicita dell'utente.
- 26/09/2026 — Nomi nel **codice in inglese**, testi dell'**interfaccia e documenti in italiano**. Motivo: approvato con il primo CLAUDE.md (esempi `sing_40`, `sing_20`).
- 27/09/2026 — **Lint con `ruff`** (0.16.9, solo in `requirements-dev.txt`): `ruff check .` con le regole di base, **senza file di configurazione** e **senza `ruff format`**, che riscriverebbe i file di tutti e creerebbe conflitti. Motivo: scelta dell'utente sulla raccomandazione di Claude (chiude D4).
- 27/09/2026 — **Due librerie in più** oltre alle estensioni ammesse: **python-dotenv** (legge il file `.env`; è quella che Flask stesso usa) e **cryptography** (serve a PyMySQL per il login di MySQL 8.0, `caching_sha2_password`). Motivo: scelta dell'utente sulla raccomandazione di Claude.
- 27/09/2026 — **SQLAlchemy 2.0** (2.0.54), non la 2.1: Flask-SQLAlchemy 3.1.1 è scritta per la 2.0 e la 2.1 era appena uscita. Tutte le librerie, anche quelle indirette, sono fissate con `==` in `requirements*.txt`. Motivo: scelta dell'utente sulla raccomandazione di Claude.
- 27/09/2026 — **Controllo di MySQL all'avvio in `run.py`**, non in `create_app()`: si collega al server senza scegliere un database e accetta solo la 8.0; così i test che non usano il database non richiedono MySQL. Il controllo di Python (solo 3.14) sta invece in `create_app()`. Il server è Werkzeug in tutte le configurazioni (`ALLOW_UNSAFE_WERKZEUG`), anche nei test, che lo avviano fuori da un terminale. Motivo: scelta dell'utente sulla raccomandazione di Claude.

## Dati

- 26/09/2026 — **Niente partite da ospite**: si gioca solo con un account. Motivo: rating e statistiche richiedono un utente.
- 26/09/2026 — **L'utente può cancellare il proprio account** e si conservano solo i dati indispensabili. Motivo: si salvano email, quindi serve rispettare la privacy.
- 26/09/2026 — **Backup giornaliero con `mysqldump`**, con una prova di ripristino. Motivo: non perdere account e storico.
- 26/09/2026 — **Database separati** per sviluppo, test e installazione demo. Motivo: i test non devono mai toccare dati reali.

## Sicurezza

- 26/09/2026 — Account con **username, email e password**. **Niente verifica dell'email né recupero password** nella prima versione (arriveranno se avanza tempo). Motivo: richiedono un servizio di invio email.
- 26/09/2026 — Password salvate solo come **hash** (un'impronta da cui non si risale alla password). Segreti solo nel file `.env`, mai nel repository. Motivo: sicurezza di base.

## Interfaccia

- 26/09/2026 — **Mobile-first**: le pagine si progettano prima per lo smartphone e poi si adattano al computer. Motivo: richiesta dell'utente.
- 26/09/2026 — **Carte**: si parte con carte **disegnate in CSS come segnaposto**, poi si prova un **set con licenza libera**. L'utente ha già delle immagini proprie da valutare. Motivo: non bloccare lo sviluppo in attesa della grafica.
- 26/09/2026 — Terminologia **"cantare 40" / "cantare 20"**, mai "dichiarare un matrimonio". Motivo: richiesta dell'utente.
- 26/09/2026 — ~~Home~~: due pulsanti grandi **1v1** e **2v2**, il proprio rating, il **numero di utenti online** e l'avviso **"rientra in partita"** quando c'è una partita in corso. Motivo: idea dell'utente e consigli 5 e 7 accettati. **Sostituita** il 27/09/2026 dalla decisione "Home dal prototipo approvato" più in basso.
- 26/09/2026 — ~~Navbar in alto~~: a sinistra l'**avatar**, che apre un menu *Statistiche · Impostazioni · Esci* (per chi non ha fatto il login: *Accedi · Registrati*); al centro il **logo "500"**, che riporta alla home, in una versione leggibile a 40 px di altezza; a destra gli **amici**, con un contatore delle notifiche. Motivo: idea dell'utente e consigli 3 e 6 accettati. **Sostituita** il 27/09/2026 dalla decisione "Navbar" più in basso.
- 26/09/2026 — ~~Bottom navbar~~, in quest'ordine: **🏆 Classifica · 🔑 Privata · 🏠 Gioca · 📜 Partite · 📖 Regole**, con icona ed etichetta. È nascosta durante la partita; su computer resta in basso, centrata. Motivo: proposta accettata dall'utente, con Gioca e Classifica scambiati di posto. **Tolta** il 27/09/2026: le sezioni che conteneva non ci sono più.
- 26/09/2026 — Chi non ha fatto il login e tocca 1v1 o 2v2 vede una **finestra "Accedi o registrati per giocare"**, non un errore. Motivo: consiglio 1 accettato.
- 26/09/2026 — **Avatar da un set predefinito**, niente caricamento di foto. Chi non ne ha scelto uno vede le iniziali. Motivo: consiglio 2 accettato (spazio per i file, controllo dei contenuti, privacy).
- 26/09/2026 — **Attesa in coda a tutto schermo**, con il tempo trascorso, l'intervallo di rating che si allarga e il pulsante "Annulla". Motivo: consiglio 4 accettato.
- 26/09/2026 — ~~La grafica della home viene dal prototipo fatto con Stitch~~. **Sostituita** dalla decisione "prototipo statico scritto da Claude" più in basso. Resta valido il resto: prototipo solo come riferimento in `docs/prototipo/`, navbar e bottom navbar in file separati inclusi da `base.html` (P40), colori e font come variabili CSS (P19), `index.html` con il solo markup della home, senza CSS e JS scritti dentro (P22).
- 26/09/2026 — **Font, icone e librerie CSS possono essere caricati da internet (CDN)**, come fa il prototipo Stitch, e si caricano solo da `base.html`. Il client Socket.IO resta un file locale a versione fissa (P23). La demo resta in rete locale. Motivo: tutti i dispositivi della demo hanno internet (scelta dell'utente).
- 26/09/2026 — **Niente Stitch: il prototipo statico della home lo scrive Claude** (P52), in `docs/prototipo/` (`home.html`, `prototipo.css`, `prototipo.js`, `LEGGIMI.md`). Si apre senza server, è già diviso nelle parti che diventano file separati e usa variabili CSS; P19, P40 e P22 lo spostano nei file modulari. Motivo: scelta dell'utente, che vuole cominciare dai file HTML.
- 26/09/2026 — **Stile siciliano**: colori caldi (giallo e rosso della Trinacria, richiami alle maioliche). Se nel prototipo non convince, si passa al tavolo classico (verde panno, oro e crema). Motivo: scelta dell'utente ("vediamo come viene"). **Aggiornata il 27/09/2026**: scelta la palette **"Carretto siciliano"** (rosso, verde, giallo e azzurro su fondo crema), vedi `docs/prototipo/`.
- 26/09/2026 — **Tema chiaro e scuro automatico**, secondo l'impostazione del dispositivo. Motivo: scelta dell'utente. **Aggiornata il 27/09/2026**: il tema scuro è **rimandato alla fine** (P53, Fase 4); fino ad allora c'è solo il tema chiaro.
- 26/09/2026 — **Colori, font e logo li sceglie Claude**. I valori esatti si fissano nel prototipo di P52 (variabili CSS) e i font si elencano in `docs/prototipo/LEGGIMI.md`. Il logo "500" è un testo stilizzato nel prototipo e diventa un SVG disegnato da Claude in P42. Motivo: scelta dell'utente (chiude D30).
- 26/09/2026 — **Niente emoji nell'interfaccia**: icone da una libreria caricata da CDN (Material Symbols), uguali su tutti i dispositivi. Le emoji scritte nei documenti indicano solo il soggetto dell'icona. Motivo: scelta dell'utente; le emoji cambiano aspetto da un dispositivo all'altro.
- 26/09/2026 — ~~Contenuto della home~~: saluto "Ciao, *username*"; pulsanti 1v1 e 2v2 con icona, **sottotitolo** e **il rating della modalità scritto sul pulsante**; numero di utenti online; avviso di rientro. **Senza login**: "Accedi per avere un rating" al posto del rating, pulsanti visibili che aprono la finestra di accesso, link "Nuovo? Leggi le regole". **Decorazioni** con i semi siciliani, discrete. Motivo: scelta dell'utente. **Sostituita** il 27/09/2026 dalla decisione "Home dal prototipo approvato" più in basso.
- 26/09/2026 — **Su computer la home ha un layout diverso** da quello del telefono, che occupa lo spazio in orizzontale. La bottom navbar resta in basso e centrata (decisione precedente). Motivo: scelta dell'utente. **Aggiornata il 27/09/2026**: la bottom navbar non c'è più.
- 26/09/2026 — ~~Il prototipo mostra tutti gli stati~~ (con e senza login, menu del profilo, finestra "Accedi o registrati", schermata di coda, avviso di rientro), con una barra per passare dall'uno all'altro presente solo nel prototipo. Motivo: scelta dell'utente; sono le parti che servono a P22 e P40. **Sostituita** il 27/09/2026: il prototipo approvato mostra i suoi stati con i parametri `?apri=` (vedi `docs/prototipo/LEGGIMI.md`).
- 27/09/2026 — **Prototipo della home approvato**: `docs/prototipo/index.html`, con `prototipo.css`, `prototipo.js` e `LEGGIMI.md` (P52). È il riferimento grafico di P19, P40 e P22. Font **Fredoka** per titoli e numeri, **Nunito** per il testo, icone **Material Symbols Rounded**, tutti da Google Fonts. Motivo: scelta dell'utente dopo varie prove.
- 27/09/2026 — **Home dal prototipo approvato**: "giocatori online" al centro; due sezioni, **Partita Veloce** e **Gioca con un amico**, ciascuna con due **carte-pulsante 1v1 e 2v2** a forma di carta siciliana (rosso, verde, giallo, blu; icona, modalità e sottotitolo in bianco). Su telefono le sezioni stanno una sotto l'altra, da 900 px affiancate. Motivo: scelta dell'utente.
- 27/09/2026 — **La home non scorre mai**, né su telefono né su computer: le carte-pulsante si rimpiccioliscono sugli schermi bassi. Su telefono in orizzontale le quattro carte stanno su una sola fila. Motivo: richiesta dell'utente.
- 27/09/2026 — **Modal della modalità**: toccando una carta-pulsante si apre un modal con la scelta dei **punti per vincere (150, 300, 500)** e il pulsante **Gioca**. In "Gioca con un amico" c'è anche la lista degli **amici online** da invitare, e **Gioca si attiva solo dopo che l'amico ha accettato**. Nel 1v1 l'amico è l'avversario; nel 2v2 è il compagno di squadra e gli avversari arrivano dal matchmaking. Si invita un amico alla volta. Motivo: prompt dell'utente; la parte su 1v1 e 2v2 è l'interpretazione di Claude, approvata con il prototipo.
- 27/09/2026 — **Navbar**: trasparente e sfocata (effetto vetro), senza striscia colorata. A sinistra l'**avatar**, che apre il **pannello statistiche** (partite, vinte, perse, percentuale, rating 1v1 e 2v2) con i link **Impostazioni** ed **Esci**; al centro il nome del gioco con il seme di denari; a destra gli **amici** con il contatore, che apre il **pannello amici** (ricerca e richieste, amici online e offline, chat). Su computer accanto ad avatar e icona compaiono le scritte. Il nome mostrato è **Cinquecento** (decisione successiva). Motivo: prompt dell'utente.
- 27/09/2026 — **Sfondo della home con carte siciliane vere**: coppie **Cavallo + Re** dei quattro semi, più **Assi** e **Tre**. Uno script le mette negli spazi vuoti senza sovrapposizioni (solo Cavallo e Re di una coppia si sovrappongono) e mai dietro titoli e "giocatori online"; dietro le carte-pulsante solo se lo sfondo resta troppo vuoto (sotto il 45% dello spazio libero coperto) e sempre visibili almeno per un terzo. Motivo: richiesta dell'utente.
- 27/09/2026 — **Immagini delle carte dello sfondo** da Wikimedia Commons, scansioni di **Matsoftware** con licenza **CC BY-SA 3.0**: vanno citati autore e licenza in modo visibile nel sito, con una riga in fondo al pannello statistiche (decisione successiva). Il seme di denari accanto al nome è di pubblico dominio (Florixc). Motivo: licenza delle immagini.
- 27/09/2026 — **Nome mostrato: "Cinquecento"**, nella navbar, nel titolo della scheda del browser e nel logo (P42). Nel prototipo la navbar diceva "Briscola": corretto. Motivo: scelta dell'utente, è il gioco che si gioca davvero (chiude D34).
- 27/09/2026 — **Crediti delle immagini**: una riga piccola in fondo al pannello statistiche, sotto Impostazioni ed Esci: "Carte dello sfondo: Matsoftware, CC BY-SA 3.0, da Wikimedia Commons", con il collegamento alla licenza. Motivo: la licenza CC BY-SA 3.0 lo richiede; scelta dell'utente (chiude D37).
- 27/09/2026 — **Tema scuro rimandato alla fine** della scaletta (punto P53, Fase 4). Fino ad allora le pagine hanno solo il tema chiaro del prototipo. Motivo: scelta dell'utente, per concentrarsi sulle funzioni.

## Gioco

- 26/09/2026 — **Variante siciliana / Marianna**, con le regole in `docs/REGOLE-GIOCO.md`. Motivo: scelta dell'utente.
- 26/09/2026 — Si canta **solo nel proprio turno, prima di giocare la carta**. Non serve aver vinto una presa. Si possono cantare più semi, nello stesso turno o in turni diversi. Motivo: regola dell'utente.
- 26/09/2026 — Il 40 e il 20 **si mostrano**. Se il Re o il Cavallo di un seme viene giocato, quel seme non si canta più. Motivo: regola dell'utente.
- 26/09/2026 — **A mazzo finito non cambia niente**: si continua con briscola se qualcuno ha cantato, altrimenti a carte franche. Si canta solo con **almeno 3 carte in mano**. Motivo: regola dell'utente.
- 26/09/2026 — Nel 2v2 si canta solo con Re e Cavallo **nella propria mano**, e i punti vanno alla squadra. Motivo: regola dell'utente.
- 26/09/2026 — **L'ultima presa non dà bonus.** Il raggiungimento dei 500 si controlla **solo a fine mano**. Se entrambi arrivano a 500 vince il punteggio più alto, e a parità è pareggio. Motivo: regola dell'utente. **Aggiornata il 27/09/2026**: la soglia non è più sempre 500, ma il punteggio scelto per la partita (150, 300 o 500).
- 26/09/2026 — Chi vince la presa pesca per primo, poi gli altri in ordine di turno. Motivo: approvato con il primo CLAUDE.md.
- 26/09/2026 — **30 secondi per turno**, poi il server gioca una carta automatica. **60 secondi per riconnettersi**, poi la partita è persa per abbandono, con effetto sul rating. Motivo: scelta dell'utente (16a).
- 26/09/2026 — Le ~~partite private~~ con codice **non contano per il rating**. Motivo: evitare che il rating si gonfi giocando tra amici. **Sostituita** il 27/09/2026: le stanze private con codice non esistono più.
- 26/09/2026 — Le **partite nate da un invito** tra amici sono stanze private: **non contano per il rating**. Motivo: stessa ragione delle partite private. [D] Conseguenza diretta della decisione precedente: se la volete diversa, ditelo. **Aggiornata il 27/09/2026**: vale per il **1v1 contro un amico**; per il 2v2 con un amico come compagno vedi la domanda D36. **Aggiornata ancora il 27/09/2026**: il 2v2 con un amico come compagno **conta** per il rating (decisione in fondo alla sezione).
- 26/09/2026 — **Con 500 esatti si vince**: la soglia è "almeno 500", non "più di 500". Motivo: chiarimento dell'utente (il testo precedente diceva "supera 500", che era ambiguo). **Aggiornata il 27/09/2026**: vale per qualunque punteggio scelto (con 150 esatti si vince una partita a 150).
- 27/09/2026 — **Punteggio per vincere scelto a inizio partita: 150, 300 o 500**, nel modal della modalità. Il resto del regolamento non cambia. Code e rating: decisione successiva. Motivo: prompt dell'utente.
- 27/09/2026 — **Code separate per modalità e punteggio**: chi sceglie 150 incontra solo chi ha scelto 150. Il **rating conta allo stesso modo** per tutti i punteggi. Motivo: scelta dell'utente (chiude D35).
- 27/09/2026 — **Il 2v2 con un amico come compagno conta per il rating**: gli avversari arrivano dalla coda. Il **1v1 contro un amico non conta**. Motivo: scelta dell'utente (chiude D36).

## Processo

- 26/09/2026 — ~~Branch di partenza `christian`, merge in `christian`~~ (1a). **Sostituita** dalla decisione successiva.
- 26/09/2026 — Branch permanenti: `main` (non si tocca) e `dev`. Per ogni punto si crea un **branch nuovo da `dev`**, si modifica e si testa, e **solo dopo l'ok** si fa il commit e il **merge fast-forward in `dev`** (3a). Motivo: scelta dell'utente, così i tre studenti partono tutti dalla stessa base.
- 26/09/2026 — **Ogni punto tocca solo i file elencati** nella scaletta. I punti che toccano gli stessi file vanno allo stesso studente, oppure si fanno in sequenza, dopo il merge in `dev` del precedente (sezione 9 di `SCALETTA.md`). Motivo: evitare conflitti git tra tre persone.
- 26/09/2026 — **Push solo su richiesta** dell'utente. Il remote è `origin` su GitHub. Motivo: scelta dell'utente (4a).
- 26/09/2026 — Fine riga **CRLF** per tutti i file, tranne gli script `.sh` che restano **LF**. Imposto da `.gitattributes`. Motivo: scelta dell'utente (5b).
- 26/09/2026 — Regolamento del gioco in **`docs/REGOLE-GIOCO.md`**. Motivo: scelta dell'utente (2a).
- 26/09/2026 — **Runner dei test in Python** (`tests/esegui_tutti.py`) con pytest, database `cinquecento_test`, porta di test 5099. Il file `PRODUZIONE` segnala un'installazione vera. Motivo: scelta dell'utente (20a).
- 26/09/2026 — **Messa in servizio**: per la consegna il gioco gira **in locale o in rete LAN** su un PC del gruppo. VPS o hosting gestito più avanti. Motivo: zero costi e demo garantita entro la scadenza (10c).
