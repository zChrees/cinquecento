# Decisioni prese

> **Non riaprirle senza una richiesta esplicita dell'utente.** Si può segnalare un rischio residuo, ma senza riproporre soluzioni già scartate.
>
> Formato: una riga per decisione, con **data** e **motivo**. Le nuove decisioni si aggiungono in fondo alla sezione giusta.

## Progetto e tempi

- 26/09/2026 — Progetto con **scadenza tra una settimana** (circa 03/10/2026; la data esatta è in `DA-DECIDERE.md`), **3 persone** nel gruppo. Motivo: vincolo del progetto.
- 26/09/2026 — **Prima versione**: registrazione e login, stanze private con codice, matchmaking 1v1 e 2v2, statistiche base del profilo. La classifica e il resto arrivano solo se avanza tempo. Motivo: il minimo utile che sta in una settimana.
- 26/09/2026 — **Prima versione allargata**: entrano anche **amici** (richieste di amicizia, lista, chi è online, inviti a 1v1 e 2v2), **chat tra amici**, **classifica**, pagina **Partite** (storico) e pagina **Regole** con mini-tutorial. Motivo: scelta dell'utente. Il rischio sui tempi è segnalato in `SCALETTA.md` (ordine di taglio in D31).
- 26/09/2026 — **Utenti**: per ora amici e compagni, meno di 50 connessi insieme. L'obiettivo futuro è un gioco pubblico, quindi le scelte di oggi non devono impedire di crescere. Motivo: la scala attuale permette un solo processo server.

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
- 26/09/2026 — **Home**: due pulsanti grandi **1v1** e **2v2**, il proprio rating, il **numero di utenti online** e l'avviso **"rientra in partita"** quando c'è una partita in corso. Motivo: idea dell'utente e consigli 5 e 7 accettati.
- 26/09/2026 — **Navbar in alto**: a sinistra l'**avatar**, che apre un menu *Statistiche · Impostazioni · Esci* (per chi non ha fatto il login: *Accedi · Registrati*); al centro il **logo "500"**, che riporta alla home, in una versione leggibile a 40 px di altezza; a destra gli **amici**, con un contatore delle notifiche. Motivo: idea dell'utente e consigli 3 e 6 accettati.
- 26/09/2026 — **Bottom navbar**, in quest'ordine: **🏆 Classifica · 🔑 Privata · 🏠 Gioca · 📜 Partite · 📖 Regole**, con icona ed etichetta. È nascosta durante la partita; su computer resta in basso, centrata. Motivo: proposta accettata dall'utente, con Gioca e Classifica scambiati di posto.
- 26/09/2026 — Chi non ha fatto il login e tocca 1v1 o 2v2 vede una **finestra "Accedi o registrati per giocare"**, non un errore. Motivo: consiglio 1 accettato.
- 26/09/2026 — **Avatar da un set predefinito**, niente caricamento di foto. Chi non ne ha scelto uno vede le iniziali. Motivo: consiglio 2 accettato (spazio per i file, controllo dei contenuti, privacy).
- 26/09/2026 — **Attesa in coda a tutto schermo**, con il tempo trascorso, l'intervallo di rating che si allarga e il pulsante "Annulla". Motivo: consiglio 4 accettato.
- 26/09/2026 — **La grafica della home viene dal prototipo fatto con Stitch** (un solo file HTML con CSS e JS dentro, navbar e bottom navbar comprese). Entra nel repository così com'è, in `docs/prototipo/`, **solo come riferimento** (P52), e si riscrive in file modulari: navbar e bottom navbar in file separati inclusi da `base.html` (P40), colori e font come variabili CSS (P19), `index.html` con il solo markup della home, senza CSS e JS scritti dentro (P22). Motivo: il gruppo ha già la pagina pronta; riscriverla a pezzi mantiene la struttura modulare ed evita conflitti tra i tre.
- 26/09/2026 — **Font, icone e librerie CSS possono essere caricati da internet (CDN)**, come fa il prototipo Stitch, e si caricano solo da `base.html`. Il client Socket.IO resta un file locale a versione fissa (P23). La demo resta in rete locale. Motivo: tutti i dispositivi della demo hanno internet (scelta dell'utente).

## Gioco

- 26/09/2026 — **Variante siciliana / Marianna**, con le regole in `docs/REGOLE-GIOCO.md`. Motivo: scelta dell'utente.
- 26/09/2026 — Si canta **solo nel proprio turno, prima di giocare la carta**. Non serve aver vinto una presa. Si possono cantare più semi, nello stesso turno o in turni diversi. Motivo: regola dell'utente.
- 26/09/2026 — Il 40 e il 20 **si mostrano**. Se il Re o il Cavallo di un seme viene giocato, quel seme non si canta più. Motivo: regola dell'utente.
- 26/09/2026 — **A mazzo finito non cambia niente**: si continua con briscola se qualcuno ha cantato, altrimenti a carte franche. Si canta solo con **almeno 3 carte in mano**. Motivo: regola dell'utente.
- 26/09/2026 — Nel 2v2 si canta solo con Re e Cavallo **nella propria mano**, e i punti vanno alla squadra. Motivo: regola dell'utente.
- 26/09/2026 — **L'ultima presa non dà bonus.** Il raggiungimento dei 500 si controlla **solo a fine mano**. Se entrambi arrivano a 500 vince il punteggio più alto, e a parità è pareggio. Motivo: regola dell'utente.
- 26/09/2026 — Chi vince la presa pesca per primo, poi gli altri in ordine di turno. Motivo: approvato con il primo CLAUDE.md.
- 26/09/2026 — **30 secondi per turno**, poi il server gioca una carta automatica. **60 secondi per riconnettersi**, poi la partita è persa per abbandono, con effetto sul rating. Motivo: scelta dell'utente (16a).
- 26/09/2026 — Le **partite private** con codice **non contano per il rating**. Motivo: evitare che il rating si gonfi giocando tra amici.
- 26/09/2026 — Le **partite nate da un invito** tra amici sono stanze private: **non contano per il rating**. Motivo: stessa ragione delle partite private. [D] Conseguenza diretta della decisione precedente: se la volete diversa, ditelo.
- 26/09/2026 — **Con 500 esatti si vince**: la soglia è "almeno 500", non "più di 500". Motivo: chiarimento dell'utente (il testo precedente diceva "supera 500", che era ambiguo).

## Processo

- 26/09/2026 — ~~Branch di partenza `christian`, merge in `christian`~~ (1a). **Sostituita** dalla decisione successiva.
- 26/09/2026 — Branch permanenti: `main` (non si tocca) e `dev`. Per ogni punto si crea un **branch nuovo da `dev`**, si modifica e si testa, e **solo dopo l'ok** si fa il commit e il **merge fast-forward in `dev`** (3a). Motivo: scelta dell'utente, così i tre studenti partono tutti dalla stessa base.
- 26/09/2026 — **Ogni punto tocca solo i file elencati** nella scaletta. I punti che toccano gli stessi file vanno allo stesso studente, oppure si fanno in sequenza, dopo il merge in `dev` del precedente (sezione 9 di `SCALETTA.md`). Motivo: evitare conflitti git tra tre persone.
- 26/09/2026 — **Push solo su richiesta** dell'utente. Il remote è `origin` su GitHub. Motivo: scelta dell'utente (4a).
- 26/09/2026 — Fine riga **CRLF** per tutti i file, tranne gli script `.sh` che restano **LF**. Imposto da `.gitattributes`. Motivo: scelta dell'utente (5b).
- 26/09/2026 — Regolamento del gioco in **`docs/REGOLE-GIOCO.md`**. Motivo: scelta dell'utente (2a).
- 26/09/2026 — **Runner dei test in Python** (`tests/esegui_tutti.py`) con pytest, database `cinquecento_test`, porta di test 5099. Il file `PRODUZIONE` segnala un'installazione vera. Motivo: scelta dell'utente (20a).
- 26/09/2026 — **Messa in servizio**: per la consegna il gioco gira **in locale o in rete LAN** su un PC del gruppo. VPS o hosting gestito più avanti. Motivo: zero costi e demo garantita entro la scadenza (10c).
