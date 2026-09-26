# Cinquecento — istruzioni per Claude Code

> Le voci marcate "(da P#)" si completano quando il punto della scaletta indicato è fatto.

## Prima di lavorare

1. Leggi **`DECISIONI.md`**: le decisioni già prese, con data e motivo. Non riaprirle senza una richiesta esplicita dell'utente. Si può segnalare un rischio residuo, senza riproporre soluzioni già scartate.
2. **Tracker attivo:** `SCALETTA.md`, l'elenco dei punti da fare (P1, P2, …) in ordine di priorità, da spuntare man mano. Quando più avanti ci sarà una code review, il tracker attivo diventerà il suo file: aggiorna questa riga.
3. Le domande che dipendono da altri (cliente, utenti, hardware, regole esterne) stanno in **`DA-DECIDERE.md`**: aggiornalo quando emerge un punto nuovo.
4. **Archivio:** `docs/archivio/` contiene i tracker chiusi e la cronologia dei lotti. Non si aggiorna più; aprilo quando serve il perché di una scelta passata.
5. Questo file è la guida di processo: niente cronologia dei lotti qui dentro (va nel tracker e poi nell'archivio).

6. Il regolamento del gioco è in **`docs/REGOLE-GIOCO.md`**: è il riferimento unico per il motore di gioco.

**Stato (26/09/2026):** scritti `SCALETTA.md`, `DECISIONI.md`, `DA-DECIDERE.md` e `docs/REGOLE-GIOCO.md` (branch `docs/scaletta`, in attesa di ok). Aggiunti la regola "con 500 esatti si vince" e il punto P52 (prototipo Stitch della home come riferimento). Prossimo passo: P1–P3 (`.gitattributes`, `.gitignore`, riga Stato), poi P52 e P4 (scheletro del progetto).

## File e cartelle da ignorare

Non esplorare, leggere o analizzare questi percorsi salvo richiesta esplicita (in quel caso chiedi conferma prima):

- `node_modules/`, `.git/`, cartelle di build (`dist/`, `build/`, …)
- `.venv/`, `__pycache__/`, `.pytest_cache/`
- `backups/`, `logs/`, `.env`, la cartella della demo (quella con il file `PRODUZIONE`), i database MySQL `cinquecento` e `cinquecento_dev`
- file temporanei o generati automaticamente

Eccezioni: `tests/` (Claude la usa e la aggiorna liberamente); `app/static/dev/*.json`, `.env.example` e `migrations/*.sql`, che i test possono leggere o toccare ma che il runner ripristina sempre identici (controllo con hash); il database `cinquecento_test`, che i test possono svuotare.

Non fare scansioni dell'intero repository quando non servono: cerca prima nei file della funzionalità su cui si lavora. File principali (da P4): `run.py`, `config.py`, `app/__init__.py`, `app/game/engine/`, `app/realtime/`, `app/sockets/`, `app/blueprints/`, `app/services/`, `app/repositories/`, `app/static/js/pages/`, `tests/esegui_tutti.py`.

## Progetto

Web-app per giocare online a **Cinquecento**, variante siciliana (Marianna), con le carte siciliane. Si gioca 1v1 o 2v2, da stanza privata con codice o dalla coda di matchmaking basata sul rating (Glicko-2). Ogni utente ha un account (registrazione, login, avatar da un set predefinito), statistiche, classifica e storico delle partite; ha amici (richieste, chi è online, chat, inviti a partita). Interfaccia: navbar in alto (avatar e menu · logo "500" · amici) e bottom navbar (Classifica · Privata · Gioca · Partite · Regole). Per ora è per amici e compagni (meno di 50 persone connesse insieme); in futuro deve poter diventare pubblico. Progetto di gruppo (3 persone), con scadenza intorno al 03/10/2026. Regole in `docs/REGOLE-GIOCO.md`; terminologia: si dice **"cantare 40"** e **"cantare 20"**, mai "dichiarare un matrimonio".

- Stack: HTML, CSS, JavaScript vanilla (ES modules, nessun framework né bundler); **Python 3.14** (3.14.4) con Flask, Flask-SocketIO (modalità `threading`, un solo processo), Flask-Login, Flask-WTF, Flask-SQLAlchemy; **MySQL 8.0** con PyMySQL. Tutto installato a mano, alle stesse versioni per tutti.
- Dove gira: sviluppo su PC Windows (`localhost`); demo su un PC del gruppo, raggiungibile dalla rete locale. VPS in un secondo momento.
- Parti principali: `app/game/engine/` motore di gioco in Python puro (niente Flask né DB); `app/realtime/` stanze attive, timer e matchmaking (in memoria); `app/sockets/` e `app/blueprints/` ingressi sottili; `app/services/` logica; `app/repositories/` unico accesso a MySQL; `app/static/js/` con un entry point per pagina in `pages/` e i componenti in `components/`.
- Dati e segreti: account e partite su MySQL; segreti solo in `.env` (modello in `.env.example`), mai nel repository; backup in `backups/` (ignorato da git).

## Processo di lavoro

- Lavora **a lotti piccoli**: un punto del tracker o un gruppo di punti strettamente legati.
- **Tocca solo i file elencati nel punto** della scaletta: il progetto è diviso tra tre persone, e ogni file fuori elenco è un possibile conflitto git. Se serve un file non elencato, o se il punto dice che l'elenco "non è sicuro", fermati, proponi la lista e aspetta conferma.
- Prima di modificare il codice, controlla nel tracker e in `DECISIONI.md` se esiste già uno spec concordato.
- Se una modifica cambia il comportamento visibile agli utenti, o richiede una scelta di design, **spiega le opzioni (con una raccomandazione) e aspetta conferma**, salvo quando lo spec è già approvato.
- Non aggiungere tabelle, colonne, stato duplicato o strutture non necessarie senza discuterne prima.
- Niente refactoring estranei al lotto corrente: se ne vedi uno utile, proponilo come punto nuovo del tracker.
- Per un bug: prima riproducilo (anche con un test che fallisce), poi correggi, poi controlla le regressioni.
- Separa i fatti dalle ipotesi con la legenda dell'evidenza: **[T]** verificato con una prova · **[L]** letto nel codice · **[D]** dedotto · **[N]** non verificabile.
- Tutto il lavoro e i messaggi rivolti all'utente sono in italiano, chiari anche per chi non è uno sviluppatore esperto: spiega un termine tecnico la prima volta che lo usi.
- Fine riga dei file: **CRLF**, tranne gli script `.sh` che restano **LF** (imposto da `.gitattributes`). Per modifiche con molti caratteri speciali usa Edit o uno script in una cartella temporanea, non comandi della shell pieni di escape.

## Regole git

- Branch permanenti: `main` (rilasci, non si tocca) e `dev` (lavoro e integrazione del gruppo). Portare `dev` in `main` è una decisione dell'utente: non proporla. Il branch `christian` non è più il branch di partenza.
- Per ogni lotto: **branch nuovo da `dev` aggiornato** (es. `feature/p10-carte`, `docs/...`, `fix/...`). Prima di crearlo, controlla che i punti da cui dipende siano già in `dev` (colonna "Attende" della sezione 9 di `SCALETTA.md`).
- Lascia le modifiche **senza commit**: l'utente le prova.
- Solo dopo l'**ok esplicito** dell'utente: commit sul branch (separati se il lotto mescola cose diverse), merge fast-forward in `dev`. Se il fast-forward non è possibile, perché nel frattempo `dev` è andato avanti con i lavori degli altri, fermati e chiedi come procedere.
- Mai tracciare dipendenze, dati reali, segreti, backup, log (controlla `.gitignore` prima del primo commit di un file nuovo).
- Remote `origin` su GitHub (`zChrees/cinquecento`): **push solo su richiesta** dell'utente.

## Convenzioni del codice

Il perché di ciascuna va in `DECISIONI.md`. Adatta l'elenco allo stack; togli quello che non serve.

- **Una sola via per le scritture** sul database (transazioni, coda o funzione unica). I controlli che decidono una scrittura vanno **dentro** la stessa transazione, anche quando riguardano stato in memoria: un controllo fatto prima di mettersi in fila può essere già superato quando la scrittura parte.
- **Azioni ripetibili senza doppioni**: le richieste che creano qualcosa portano una chiave anti-doppione (stessa chiave per lo stesso tentativo); i pulsanti si disattivano finché non arriva la risposta. Prevedi sempre il doppio clic e le due schede aperte.
- **Validazione sul server** di tutto quello che arriva da fuori (tipi, lunghezze, valori ammessi); nessuna correzione silenziosa: un dato non valido si rifiuta con un messaggio chiaro.
- **Pagine web**: testo degli utenti mai inserito come HTML (escape o `textContent`); niente `alert` / `confirm` / `prompt` (finestre nella pagina); ogni pulsante con sola icona ha un'etichetta accessibile; nessuna azione parte se la connessione manca.
- **Log**: livelli distinti per evento normale e anomalia; mai dati personali, testo libero degli utenti, token, password o chiavi.
- **Segreti**: mai nel repository, mai stampati, mai rigenerati in silenzio; istruzioni scritte per ripristinarli da una copia.
- **Dipendenze**: `requirements.txt` con versioni esatte (`==`), installazione con `pip install -r requirements.txt` dentro `.venv`; le librerie JS dell'applicazione (es. client Socket.IO) sono file locali a versione fissa; font, icone e librerie CSS possono venire da CDN, caricati solo in `base.html` ed elencati in `docs/prototipo/LEGGIMI.md`.
- **Motore di gioco puro**: `app/game/engine/` non importa mai Flask, SocketIO o il database. Forma `apply(stato, azione) -> nuovo stato` e `legal_actions(stato)`.
- **Server autoritativo**: il client invia solo azioni; ogni giocatore riceve solo la propria vista (mai carte altrui né ordine del mazzo). Le regole stanno solo nel server: il client usa le mosse legali ricevute.
- **Stanze di gioco**: ogni evento di una stanza si elabora sotto il **lock di quella stanza**; timer e mosse passano dalla stessa via.
- **Pagine**: un'unica funzione `render(vista)` per pagina che ridisegna dallo stato ricevuto; componenti come funzioni che restituiscono elementi DOM; attributi `data-*` stabili per i test.
- **Nomi e lingua**: codice in inglese (`sing_40`, `sing_20`, `can_sing`), interfaccia e documenti in italiano.

## Punti delicati

Da riempire man mano: le parti del codice che hanno già avuto bug o che hanno regole non ovvie. Una riga per punto, con il perché.

- Regole del canto (turno, prima della carta, minimo 3 carte a mazzo finito, seme "bruciato" se Re o Cavallo giocati): facili da sbagliare, ogni caso ha un test (P12).
- Viste per giocatore: una sola chiave di troppo mostra le carte avversarie (P15).

## Testing

- Le suite stanno in `tests/` e provano il programma vero dall'esterno quando possibile (server avviato, client simulati), non solo funzioni isolate.
- Comando per tutte le suite (da P6): `python tests/esegui_tutti.py`. Una sola suite: `python tests/esegui_tutti.py engine` (le suite sono le cartelle di `tests/`). Numero di controlli attuale: 0 PASS (aggiornalo a ogni lotto).
- **I test non toccano mai dati reali**: usano solo il database `cinquecento_test` e la porta 5099, e si rifiutano di partire se trovano il file `PRODUZIONE` nella cartella del progetto o un database che non finisce con `_test`. Mai lanciarli nella cartella della demo.
- File che i test devono modificare (configurazioni, dati di esempio): copia fuori dal progetto, ripristino identico verificato con un hash, copia cancellata alla fine.
- Prima di avviare un server di test controlla che la porta sia libera: se è occupata, fermati e chiedi (l'utente può avere il suo server acceso). Ricorda all'utente di chiudere le schede del browser collegate prima di un giro completo.
- Niente attese fisse dove si può aspettare un evento; niente estrazione di codice dalle pagine cercando commenti o posizioni: usa marcatori espliciti e stabili, o moduli importabili.
- Dati di prova dei test (menù, utenti, prodotti…) propri dei test, non quelli di sviluppo che cambieranno.
- Per ogni lotto: riproduci il problema, aggiungi o aggiorna la suite, poi esegui **tutte** le suite.
- Segreti e token si leggono dove servono, ma i loro valori non si stampano mai.

## Consegna

Quando l'utente chiede un lotto:
1. riassumi brevemente cosa farai;
2. se c'è una decisione non ancora approvata, fermati e chiedila;
3. implementa solo il lotto richiesto;
4. testa;
5. indica cosa è stato modificato, cosa è stato verificato, come provarlo a mano e cosa resta da fare;
6. aggiorna il tracker (spunta e breve nota del lotto), `DECISIONI.md` se l'utente ha deciso qualcosa di nuovo (con data e motivo), `DA-DECIDERE.md` se emerge una domanda;
7. **aggiorna la riga "Stato"** in cima a questo file: data, cosa è fatto, prossimo passo. Ogni sessione riparte da lì.

Per modifiche mirate l'utente preferisce diff o snippet piccoli con la posizione precisa; il file completo solo se lo chiede.

## Comandi utili

- Installazione (da P4): `py -3.14 -m venv .venv`, poi `.venv\Scripts\activate` e `pip install -r requirements.txt`; copia `.env.example` in `.env` e compila i valori.
- Database (da P5): `mysql -u root -p < scripts/setup_db.sql` (una volta sola), poi `python scripts/migrate.py`.
- Avvio (da P4): `python run.py` → `http://localhost:5000`.
- Lint: da decidere (D4).
- Test (da P6): `python tests/esegui_tutti.py`.
- Backup e ripristino (da P18): `python scripts/backup.py`, `python scripts/ripristina.py <file> <database>`; il ripristino su un database che non è di test chiede conferma.

Non cancellare o sovrascrivere dati reali. I comandi distruttivi si usano solo su dati di test.
