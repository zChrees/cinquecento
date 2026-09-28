D4# Cinquecento — istruzioni per Claude Code

> Le voci marcate "(da P#)" si completano quando il punto della scaletta indicato è fatto.

## Prima di lavorare

1. Leggi **`DECISIONI.md`**: le decisioni già prese, con data e motivo. Non riaprirle senza una richiesta esplicita dell'utente. Si può segnalare un rischio residuo, senza riproporre soluzioni già scartate.
2. **Tracker attivo:** `SCALETTA.md`, l'elenco dei punti da fare (P1, P2, …) in ordine di priorità, da spuntare man mano. Quando più avanti ci sarà una code review, il tracker attivo diventerà il suo file: aggiorna questa riga.
3. Le domande che dipendono da altri (cliente, utenti, hardware, regole esterne) stanno in **`DA-DECIDERE.md`**: aggiornalo quando emerge un punto nuovo.
4. **Archivio:** `docs/archivio/` contiene i tracker chiusi e la cronologia dei lotti. Non si aggiorna più; aprilo quando serve il perché di una scelta passata.
5. Questo file è la guida di processo: niente cronologia dei lotti qui dentro (va nel tracker e poi nell'archivio).
   **Riepiloghi**: ognuno ha il suo file, con il più recente in cima, e **lo scrive solo lui**: **`christian.md`** (punti fatti e aggiornamenti dei documenti), **`giuseppe.md`** e **`antonio.md`**. Gli altri due file non si modificano mai, nemmeno per correggere un errore: si segnala a chi li scrive. Dopo il `git pull` di `dev`, a seconda di chi è l'utente, leggi gli altri due:
   - **Christian** legge `giuseppe.md` e `antonio.md`, per le informazioni utili al progetto, e dai loro riepiloghi aggiorna i documenti condivisi (scaletta, decisioni, domande aperte, riga "Stato");
   - **Giuseppe** legge `christian.md` e `antonio.md`, per le novità utili al progetto e al suo lavoro;
   - **Antonio** legge `christian.md` e `giuseppe.md`, per le modifiche al progetto e le informazioni utili al suo lavoro.

6. Il regolamento del gioco è in **`docs/REGOLE-GIOCO.md`**: è il riferimento unico per il motore di gioco.
7. **Chi lavora**: il progetto è diviso tra **Giuseppe** (Studente 1: motore e tempo reale), **Antonio** (Studente 2: account, dati, amici) e **Christian** (Studente 3: interfaccia e documenti); i punti di ciascuno e l'ordine sono nella sezione 9 di `SCALETTA.md`. A inizio sessione, se non sai chi è l'utente, chiediglielo. Lavora solo sui punti assegnati a lui: se chiede un punto di un altro, faglielo notare e aspetta conferma.

**Stato (28/09/2026, notte, dopo P22 e P45):** in `dev` ci sono P1–P6, **P7** (log in `logs/cinquecento.log`, pagine 404 e 500 senza navbar), P8 (contratto approvato dai tre), P10–P15 di Giuseppe (tutto il motore), P16 (registrazione, login e logout: punto di Antonio fatto da Giuseppe, che ne rifinisce la grafica), **P17** (impostazioni: avatar e cancellazione dell'account), **P18** (backup e ripristino), P19 (base grafica), P20 (carte segnaposto e mano), P21 (tavolo di gioco; in prova `/game/prova?demo=1v1` o `?demo=2v2`, con il login), **P22** (home con dati finti: carte-pulsante, carta-modal, coda, rientro con `/?demo=rientro`, cascata di carte), P23 (tempo reale, stanze con il lock), **P24** (partita vera sul server: `create_room`, mosse con `version`, `game.js` collegato ai socket, D14), P40 (navbar, pannello statistiche, finestra "Accedi o registrati"), **P45** (amicizie e blocchi, con la presenza degli amici) e P52 (prototipo della home), più le correzioni di `app/checks.py` e `scripts/migrate.py`: in tutto **963 test PASS** in 6 suite (calcolato dai riepiloghi). Chi non l'ha ancora fatto, dopo il pull di P5 lancia **una volta** `setup_db.sql` (comando in "Comandi utili"), copia nel `.env` la password generata e lancia `python scripts/migrate.py`: senza, `run.py` e le suite `db`, `api` e `sockets` non partono. Si lavora in tre in parallelo (D3); i documenti condivisi li aggiorna solo Christian (D22), che scrive i suoi riepiloghi in `christian.md` (Giuseppe in `giuseppe.md`, Antonio in **`antonio.md`**, nuovo; ognuno legge i file degli altri due dopo il pull); commit, merge, rebase e push solo dopo l'ok esplicito (D2). Da concordare: `js/pages/auth.js` per la navbar nelle pagine di accesso; domanda nuova **D40** (font delle icone da 5,4 MB). Prossimo passo: Giuseppe **P25**; Antonio **P26**, poi P27; Christian **P46**, poi P57 ("Da dove si parte", sezione 9 di `SCALETTA.md`).

## File e cartelle da ignorare

Non esplorare, leggere o analizzare questi percorsi salvo richiesta esplicita (in quel caso chiedi conferma prima):

- `node_modules/`, `.git/`, cartelle di build (`dist/`, `build/`, …)
- `.venv/`, `__pycache__/`, `.pytest_cache/`
- `backups/`, `logs/`, `.env`, la cartella della demo (quella con il file `PRODUZIONE`), i database MySQL `cinquecento` e `cinquecento_dev`
- file temporanei o generati automaticamente

Eccezioni: `tests/` (Claude la usa e la aggiorna liberamente); `app/static/dev/*.json`, `.env.example` e `migrations/*.sql`, che i test possono leggere o toccare ma che il runner ripristina sempre identici (controllo con hash); il database `cinquecento_test`, che i test possono svuotare.

Non fare scansioni dell'intero repository quando non servono: cerca prima nei file della funzionalità su cui si lavora. File principali (da P4): `run.py`, `config.py`, `app/__init__.py`, `app/game/engine/`, `app/realtime/`, `app/sockets/`, `app/blueprints/`, `app/services/`, `app/repositories/`, `app/static/js/pages/`, `tests/esegui_tutti.py`.

## Progetto

Web-app per giocare online a **Cinquecento**, variante siciliana (Marianna), con le carte siciliane. Si gioca 1v1 o 2v2, a 150, 300 o 500 punti, dalla home: **Partita Veloce** (coda di matchmaking basata sul rating, Glicko-2) o **Gioca con un amico** (invito: nel 1v1 l'amico è l'avversario, nel 2v2 il compagno). Ogni utente ha un account (registrazione, login, avatar da un set predefinito) e le sue statistiche; ha amici (richieste, chi è online, chat, inviti a partita). Interfaccia: una sola pagina, la home, che non scorre; navbar trasparente in alto (avatar che apre le statistiche · "Cinquecento" · amici), nessuna bottom navbar. Niente classifica, stanza privata con codice, storico delle partite né pagina delle regole (tolte il 27/09/2026). Riferimento grafico: `docs/prototipo/`. Per ora è per amici e compagni (meno di 50 persone connesse insieme); in futuro deve poter diventare pubblico. Progetto di gruppo (3 persone), con scadenza intorno al 03/10/2026. Regole in `docs/REGOLE-GIOCO.md`; terminologia: si dice **"cantare 40"** e **"cantare 20"**, mai "dichiarare un matrimonio".

- Stack: HTML, CSS, JavaScript vanilla (ES modules, nessun framework né bundler); **Python 3.14** (3.14.4) con Flask, Flask-SocketIO (modalità `threading`, un solo processo), Flask-Login, Flask-WTF, Flask-SQLAlchemy; **MySQL 8.0** con PyMySQL. Tutto installato a mano, alle stesse versioni per tutti.
- Dove gira: sviluppo su PC Windows (`localhost`); demo su un PC del gruppo, raggiungibile dalla rete locale. VPS in un secondo momento.
- Parti principali: `app/game/engine/` motore di gioco in Python puro (niente Flask né DB); `app/realtime/` stanze attive, timer e matchmaking (in memoria); `app/sockets/` e `app/blueprints/` ingressi sottili; `app/services/` logica; `app/repositories/` unico accesso a MySQL; `app/static/js/` con un entry point per pagina in `pages/` e i componenti in `components/`.
- Dati e segreti: account e partite su MySQL; segreti solo in `.env` (modello in `.env.example`), mai nel repository; backup in `backups/` (ignorato da git).

## Processo di lavoro

- Lavora **a lotti piccoli**: un punto del tracker o un gruppo di punti strettamente legati.
- **Tocca solo i file elencati nel punto** della scaletta: il progetto è diviso tra tre persone, e ogni file fuori elenco è un possibile conflitto git. Se serve un file non elencato, o se il punto dice che l'elenco "non è sicuro", fermati, proponi la lista e aspetta conferma.
- **Documenti condivisi** (`SCALETTA.md`, `CLAUDE.md`, `DECISIONI.md`, `DA-DECIDERE.md`): li aggiorna **solo Christian**, su un branch `docs/…` creato da `dev` (D22). Nei branch dei punti (`feature/…`, `fix/…`) non si toccano mai, nemmeno per spuntare il punto. A fine punto Giuseppe scrive il riepilogo in `giuseppe.md` e Antonio in `antonio.md` (ciascuno solo il suo; vedi "Consegna"). **Quando si aggiornano solo i documenti non si lanciano i test**, nemmeno dopo un `git pull` o un rebase del branch `docs/…`: il numero di controlli si prende dai riepiloghi (`giuseppe.md`, `antonio.md`) o dall'ultimo giro fatto su un punto.
- Prima di modificare il codice, controlla nel tracker e in `DECISIONI.md` se esiste già uno spec concordato.
- Se una modifica cambia il comportamento visibile agli utenti, o richiede una scelta di design, **spiega le opzioni (con una raccomandazione) e aspetta conferma**, salvo quando lo spec è già approvato.
- Non aggiungere tabelle, colonne, stato duplicato o strutture non necessarie senza discuterne prima.
- Niente refactoring estranei al lotto corrente: se ne vedi uno utile, proponilo come punto nuovo del tracker.
- Per un bug: prima riproducilo (anche con un test che fallisce), poi correggi, poi controlla le regressioni.
- Separa i fatti dalle ipotesi con la legenda dell'evidenza: **[T]** verificato con una prova · **[L]** letto nel codice · **[D]** dedotto · **[N]** non verificabile.
- Tutto il lavoro e i messaggi rivolti all'utente sono in italiano, chiari anche per chi non è uno sviluppatore esperto: spiega un termine tecnico la prima volta che lo usi.
- Fine riga dei file: **CRLF**, tranne gli script `.sh` che restano **LF** (imposto da `.gitattributes`). Per modifiche con molti caratteri speciali usa Edit o uno script in una cartella temporanea, non comandi della shell pieni di escape.

## Regole git

- Branch permanenti: `main` (rilasci, non si tocca) e `dev` (lavoro e integrazione del gruppo). Portare `dev` in `main` è una decisione dell'utente: non proporla. Il vecchio branch `christian` è stato cancellato il 28/09/2026, in locale e su GitHub: su GitHub ci sono solo `main` e `dev`, più i branch dei lotti quando qualcuno li pubblica.
- Per ogni lotto: **branch nuovo da `dev` aggiornato** (es. `feature/p10-carte`, `docs/...`, `fix/...`): prima `git switch dev` e `git pull`, poi il branch. Prima di crearlo, controlla che i punti da cui dipende siano già in `dev` **su GitHub** (colonna "Attende" della sezione 9 di `SCALETTA.md`): se non ci sono, fermati e dillo.
- Mai modifiche o commit direttamente su `dev`, e mai sui branch degli altri due.
- Lascia le modifiche **senza commit**: l'utente le prova.
- **Ogni operazione git che registra o pubblica qualcosa chiede un ok esplicito dell'utente, ogni volta e una per una**: il commit, il merge in `dev`, il rebase, il push. Frasi sul contenuto ("aggiorna", "va bene la b", "sistema tutto") **non** sono un ok: a fine lotto fermati con le modifiche senza commit, riassumi cosa è cambiato e chiedi. Anche quando sei tu ad aver proposto "poi faccio commit e push", aspetta la risposta esplicita (D2, aggiornata il 28/09/2026).
- **Prima di chiedere l'ok al commit**, a fine lotto: `git fetch` e controlla se `dev` su GitHub è andato avanti rispetto al punto da cui è partito il branch (`git log --oneline HEAD..origin/dev`). Se sì, dillo subito all'utente, indicando quali punti sono arrivati e se toccano i file del lotto, e chiedigli insieme, ma una voce per una, l'ok a commit, rebase, merge e push: così il fast-forward non fallisce a metà. `git fetch` non tocca i file e non chiede ok.
- Dopo l'ok al commit: commit sul branch (separati se il lotto mescola cose diverse). Dopo l'ok al merge: `git switch dev`, `git pull` e merge **fast-forward** (`git merge --ff-only <branch>`).
- Se il fast-forward non è possibile, perché nel frattempo un altro ha portato il suo punto in `dev`: spiegalo all'utente e, con il suo ok, torna sul branch del lotto, `git rebase dev`, rilancia **tutte** le suite (non per un branch `docs/…` con soli documenti) e ripeti il merge. Il rebase si fa solo su un branch mai pushato. Se il rebase dà un conflitto, `git rebase --abort`, fermati e spiegalo all'utente: vuol dire che due persone hanno toccato lo stesso file, e va chiarito tra loro.
- Mai `push --force` su `dev` o `main`.
- Mai tracciare dipendenze, dati reali, segreti, backup, log (controlla `.gitignore` prima del primo commit di un file nuovo).
- Remote `origin` su GitHub (`zChrees/cinquecento`): **il push si fa solo dopo l'ok esplicito dell'utente**, mai in automatico (D2). Dopo un merge in `dev` chiedigli se pushare, ricordando che conviene farlo presto: così gli altri due fanno il pull prima del loro prossimo punto. Dopo il push, ricordagli di avvisarli. Non pushare altri branch se non lo chiede.

## Convenzioni del codice

Il perché di ciascuna va in `DECISIONI.md`. Adatta l'elenco allo stack; togli quello che non serve.

- **Una sola via per le scritture** sul database (transazioni, coda o funzione unica). I controlli che decidono una scrittura vanno **dentro** la stessa transazione, anche quando riguardano stato in memoria: un controllo fatto prima di mettersi in fila può essere già superato quando la scrittura parte.
- **Azioni ripetibili senza doppioni**: le richieste che creano qualcosa portano una chiave anti-doppione (stessa chiave per lo stesso tentativo); i pulsanti si disattivano finché non arriva la risposta. Prevedi sempre il doppio clic e le due schede aperte.
- **Validazione sul server** di tutto quello che arriva da fuori (tipi, lunghezze, valori ammessi); nessuna correzione silenziosa: un dato non valido si rifiuta con un messaggio chiaro.
- **Pagine web**: testo degli utenti mai inserito come HTML (escape o `textContent`); niente `alert` / `confirm` / `prompt` (finestre nella pagina); ogni pulsante con sola icona ha un'etichetta accessibile; nessuna azione parte se la connessione manca.
- **Log**: livelli distinti per evento normale e anomalia; mai dati personali, testo libero degli utenti, token, password o chiavi.
- **Segreti**: mai nel repository, mai stampati, mai rigenerati in silenzio; istruzioni scritte per ripristinarli da una copia.
- **Dipendenze**: `requirements.txt` con versioni esatte (`==`), installazione con `pip install -r requirements.txt -r requirements-dev.txt` dentro `.venv` (il secondo file ha pytest e ruff, che servono a test e lint); le librerie JS dell'applicazione (es. client Socket.IO) sono file locali a versione fissa; font, icone e librerie CSS possono venire da CDN, caricati solo in `base.html` ed elencati in `docs/prototipo/LEGGIMI.md`.
- **Motore di gioco puro**: `app/game/engine/` non importa mai Flask, SocketIO o il database. Forma `apply(stato, azione) -> nuovo stato` e `legal_actions(stato)`.
- **Server autoritativo**: il client invia solo azioni; ogni giocatore riceve solo la propria vista (mai carte altrui né ordine del mazzo). Le regole stanno solo nel server: il client usa le mosse legali ricevute.
- **Stanze di gioco**: ogni evento di una stanza si elabora sotto il **lock di quella stanza**; timer e mosse passano dalla stessa via.
- **Pagine**: un'unica funzione `render(vista)` per pagina che ridisegna dallo stato ricevuto; componenti come funzioni che restituiscono elementi DOM; attributi `data-*` stabili per i test.
- **Nomi e lingua**: codice in inglese (`sing_40`, `sing_20`, `can_sing`), interfaccia e documenti in italiano. **Eccezione**: i nomi di tabelle e colonne del database sono in italiano (`utenti`, `partite`: D38).

## Punti delicati

Da riempire man mano: le parti del codice che hanno già avuto bug o che hanno regole non ovvie. Una riga per punto, con il perché.

- Regole del canto (turno, prima della carta, minimo 3 carte a mazzo finito, seme "bruciato" se Re o Cavallo giocati): facili da sbagliare, ogni caso ha un test (P12).
- Viste per giocatore: una sola chiave di troppo mostra le carte avversarie (P15).
- Motore puro (P10): un test impedisce ai file di `app/game/engine/` di importare Flask, il database o `config.py`. Per questo i punteggi 150/300/500 stanno sia in `config.py` sia in `RuleSet`: se cambi l'uno cambia l'altro, li confronta `test_punteggi_uguali_a_config`.
- Codici delle carte nel motore (P10): `"denari-1"`, confrontati in modo esatto; ogni codice diverso si rifiuta con "Carta non valida.". Nel contratto la carta è `{"suit", "rank"}`: la conversione sta in P15 e P24.
- Canti (P12): il 40 è il **primo canto della mano di chiunque**, non di ciascun giocatore; la briscola si ricava dall'elenco dei canti (`Sing(seat, suit, points)`, stessa forma di `sings` nella vista), non si salva a parte. `singable_suits` (per `legal.sing`) e `sing` devono dare sempre la stessa risposta: li confronta una prova su 3.000 situazioni.
- Mano (P13): dopo un canto il turno **resta** a chi ha cantato, che deve ancora giocare la carta. La squadra di un posto è `posto % 2`. Un test controlla che le mosse legali siano esattamente quelle accettate da `apply`.
- `version` della vista (contratto 3.2): il contatore sta nella **stanza** (P24, P25), non nello stato del motore, perché sale anche per scollegamenti e rientri, che il motore non conosce.
- Utente nelle pagine (P19): `base.html` legge `current_user.username` e `current_user.avatar`; il modello Python dell'utente (P16) deve usare questi nomi inglesi, anche se le colonne sono `nome_utente` e `avatar`.
- Partita (P14): il punteggio si controlla solo a fine mano; un canto che porta a N durante la mano non la chiude. Il mazziere non si salva: `dealer_seat = (first_seat - 1) % n`.
- Vista (P15): `player_view` dà solo i campi di gioco; quelli della stanza (`ROOM_FIELDS`, `ROOM_PLAYER_FIELDS`, `ROOM_TURN_FIELDS` in `views.py`) li aggiunge P24/P25. Nella mossa automatica i punti contano prima della briscola.
- Database (P5): niente `ENUM` senza `DEFAULT` (un `ENUM NOT NULL` senza valore prende in silenzio il primo dell'elenco): le colonne a elenco sono `VARCHAR` `utf8mb4_0900_bin` con un `CHECK`. Una migrazione già applicata non si modifica: `migrate.py` registra nome e numero, non il contenuto. I test del database vogliono MySQL in modalità rigorosa (`STRICT_TRANS_TABLES`, il valore predefinito), altrimenti i testi troppo lunghi verrebbero tagliati in silenzio.
- Runner (P6): `tests/conftest.py` ripete i rifiuti (file `PRODUZIONE`, database che non finisce con `_test`) anche per chi lancia `pytest` a mano; un file **nuovo** tra quelli protetti (per esempio una `migrations/002_….sql` comparsa durante i test) si segnala ma non si cancella.
- Accesso (P16): username ed email doppi li rifiuta il vincolo unico di MySQL al commit, non un controllo fatto prima (due registrazioni contemporanee non creano doppioni); `/auth/logout` accetta solo POST con il codice CSRF; dopo il login si torna a `?next=` solo se è un indirizzo di questo sito.
- Carte (P20): il componente accetta solo la forma del contratto (`{"suit", "rank"}`, rank intero da 1 a 10) e rifiuta il resto con "Carta non valida."; `test_carte.py` confronta semi e nomi con il motore eseguendo `Card.js` con Node, e salta quei controlli se Node non è installato.
- Tempo reale (P23): ogni evento di una stanza passa da `room.run(...)`, il lock della stanza (rientrante); un test manda 50 azioni insieme da 5 client e controlla che ne entri una alla volta. La suite `sockets` avvia un server vero sulla porta 5099 e vuole MySQL.
- Stanze (P24): **mai due `create_app()` nello stesso processo con il tempo reale acceso**: `socketio` è un oggetto unico e si ricollega all'ultima app, e il server già avviato smette di ricevere gli eventi giusti (nei test ogni evento rispondeva `('', 400)`). La pagina può ricevere `game:state` prima dell'`ok` di `game:join`: l'ordine lo dà `version`. Un test confronta la vista con le chiavi di `app/static/dev/vista_1v1.json`: se il contratto cambia, lo segnala.
- Tavolo (P21): la pagina non calcola regole, usa `legal.play` e `legal.sing`; l'unica eccezione è l'etichetta "Canta 40 / 20", ricavata da `sings` vuoto o no. `test_pagina_tavolo.py` apre il tavolo in Chrome o Edge senza finestra sulla porta 5099 (saltato se il browser manca): anche questo test vuole la porta libera.
- Navbar e pagine (P40): ogni pagina nuova importa `core/layout.js` e chiama `initLayout()` dal suo script in `js/pages/`, altrimenti navbar e pannelli non funzionano. I colori scritti a mano stanno solo in `variables.css` e le risorse esterne solo in `base.html`: li controlla `tests/frontend/test_base.py`.
- Log (P7): SQLAlchemy e MySQL scrivono negli errori i valori delle query (email, hash, `Duplicate entry 'Mario'`): `SafeFormatter` di `logging_config.py` li nasconde, ma resta la regola di non mettere mai dati personali nei messaggi. I test non scrivono in `logs/` (`LOG_DIR` in una cartella temporanea). La pagina 500 in un test si vede solo con `PROPAGATE_EXCEPTIONS = False`.
- Home (P22): `ModeModal.js` non parla con il server: la pagina gli passa `onPlay`, `onInvite`, `onCancelInvite` e gli risponde con `setInviteStatus(user_id, status)`; P28 e P47 cambiano solo `home.js`. La home non scorre grazie a `--tile-h` in `home.css`: ogni cosa nuova nella home va misurata (`test_pagina_home.py` lo fa in Chrome alle misure di `LEGGIMI.md`). Il test serve al browser i font di Google da una copia in una cartella temporanea fuori dal progetto (`cinquecento-test-font-cache`): la prima volta scarica il font delle icone (5,4 MB, D40), poi non usa più la rete. Senza la copia la suite `api` superava i 120 secondi del runner.
- Impostazioni (P17): i codici degli avatar (`avatars.py`) non si cambiano più, perché restano salvati nel database: P43 aggiunge solo un'immagine per codice. Il controllo "partita in corso" prima di cancellare un account non è nella stessa transazione della cancellazione; quando P28 e P47 aggiungono "in coda" e "invito in sospeso", vanno controllati anche quelli.
- Amicizie (P45): con il livello predefinito di MySQL (REPEATABLE READ) una transazione vede i dati com'erano alla prima lettura, che con il login avviene già quando Flask-Login carica l'utente: un controllo "prima di scrivere" non vedeva la richiesta appena salvata da un'altra scheda. Ogni scrittura di `friend_service.py` lavora in READ COMMITTED (`_write`); vale anche per P48 e per ogni controllo fatto con MySQL prima di una scrittura. Le date si scrivono da Python in UTC.
- Backup (P18): il backup non riuscito non lascia file (si scrive come `.parziale`); il ripristino sostituisce solo le tabelle presenti nel backup. L'utente MySQL del `.env` scrive solo in `cinquecento_dev` e `cinquecento_test`: per il database della demo servirà un `GRANT` (P38).
- Presa (P11): le carte di un seme diverso da quello di uscita e dalla briscola non prendono mai, nemmeno l'Asso; `trick_winner` restituisce la posizione nella presa (0 = chi l'ha aperta), non il giocatore.

## Testing

- Le suite stanno in `tests/` e provano il programma vero dall'esterno quando possibile (server avviato, client simulati), non solo funzioni isolate.
- Comando per tutte le suite (da P6): `python tests/esegui_tutti.py`. Una sola suite: `python tests/esegui_tutti.py engine` (le suite sono le cartelle di `tests/`). Numero di controlli attuale: 963 PASS (lo aggiorna Christian; Giuseppe e Antonio lo scrivono nel riepilogo). Esce con 0 se è tutto PASS, 1 se c'è almeno un FAIL, 2 se si rifiuta di partire.
- **I test non toccano mai dati reali**: usano solo il database `cinquecento_test` e la porta 5099, e si rifiutano di partire se trovano il file `PRODUZIONE` nella cartella del progetto o un database che non finisce con `_test`. Mai lanciarli nella cartella della demo.
- File che i test devono modificare (configurazioni, dati di esempio): copia fuori dal progetto, ripristino identico verificato con un hash, copia cancellata alla fine.
- Prima di avviare un server di test controlla che la porta sia libera: se è occupata, fermati e chiedi (l'utente può avere il suo server acceso). Ricorda all'utente di chiudere le schede del browser collegate prima di un giro completo.
- Niente attese fisse dove si può aspettare un evento; niente estrazione di codice dalle pagine cercando commenti o posizioni: usa marcatori espliciti e stabili, o moduli importabili.
- Dati di prova dei test (menù, utenti, prodotti…) propri dei test, non quelli di sviluppo che cambieranno.
- Per ogni lotto che cambia il codice o i test: riproduci il problema, aggiungi o aggiorna la suite, poi esegui **tutte** le suite. Un lotto di soli documenti non lancia i test (vedi "Processo di lavoro").
- Segreti e token si leggono dove servono, ma i loro valori non si stampano mai.

## Consegna

Quando l'utente chiede un lotto:
1. riassumi brevemente cosa farai;
2. se c'è una decisione non ancora approvata, fermati e chiedila;
3. implementa solo il lotto richiesto;
4. testa;
5. indica cosa è stato modificato, cosa è stato verificato, come provarlo a mano e cosa resta da fare;
6. **se l'utente è Christian**, su un branch `docs/…`: aggiorna il tracker (spunta e breve nota del lotto), `DECISIONI.md` se qualcuno ha deciso qualcosa di nuovo (con data e motivo), `DA-DECIDERE.md` se emerge una domanda;
7. **se l'utente è Christian**, **aggiorna la riga "Stato"** in cima a questo file: data, cosa è fatto, prossimo passo. Ogni sessione riparte da lì; poi aggiungi il riepilogo **in cima** a **`christian.md`**, con lo schema scritto nel file, nello stesso branch e commit;
8. **se l'utente è Giuseppe**, non toccare i documenti condivisi: aggiungi il riepilogo **in cima** alla sezione "Riepiloghi" di **`giuseppe.md`**, con lo schema scritto nel file (punto fatto, branch, file toccati, controlli PASS, decisioni prese, domande nuove, punti delicati scoperti), **nel branch del punto e nello stesso commit**, così arriva in `dev` con il merge e Christian lo legge da lì. `giuseppe.md` lo scrive solo Giuseppe;
9. **se l'utente è Antonio**, non toccare i documenti condivisi: aggiungi il riepilogo **in cima** alla sezione "Riepiloghi" di **`antonio.md`**, con lo schema scritto nel file (le stesse voci di `giuseppe.md`), **nel branch del punto e nello stesso commit**, così arriva in `dev` con il merge e Christian lo legge da lì. `antonio.md` lo scrive solo Antonio.

Per modifiche mirate l'utente preferisce diff o snippet piccoli con la posizione precisa; il file completo solo se lo chiede.

## Comandi utili

- Installazione (da P4): `py -3.14 -m venv .venv`, poi `.venv\Scripts\activate` e `pip install -r requirements.txt -r requirements-dev.txt`; copia `.env.example` in `.env` e compila i valori.
- Database (da P5), una volta sola, in PowerShell dalla cartella del progetto: `& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p --table -e "source scripts/setup_db.sql"` (PowerShell non accetta `<`), poi copia nel `.env` la password generata (`DB_USER=cinquecento`, `DB_PASSWORD='...'`) e lancia `python scripts/migrate.py` (rilanciato non fa niente).
- Avvio (da P4): `python run.py` → `http://localhost:5000`.
- Lint (da P4): `ruff check .` (regole di base, nessun file di configurazione; niente `ruff format`).
- Test (da P6): `python tests/esegui_tutti.py`.
- Backup e ripristino (da P18): `python scripts/backup.py`, `python scripts/ripristina.py <file> <database>`; il ripristino su un database che non finisce con `_test` chiede di scriverne il nome. Servono `mysqldump` e `mysql` (nel PATH o in `C:\Program Files\MySQL\MySQL Server 8.0\bin`), anche per la suite `db`.

Non cancellare o sovrascrivere dati reali. I comandi distruttivi si usano solo su dati di test.
