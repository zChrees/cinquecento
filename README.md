# Cinquecento

Web-app per giocare online a **Cinquecento**, il gioco di carte siciliano simile alla briscola (variante siciliana, detta anche Marianna), con le **carte siciliane**. Progetto di gruppo di Giuseppe, Antonio e Christian.

## Cosa si può fare

- **Partite 1v1 e 2v2** a **150, 300 o 500 punti**, dalla home:
  - **Partita Veloce**: la **coda di matchmaking** abbina giocatori di livello simile, in base al rating;
  - **Gioca con un amico**: si invita un amico online; nel 1v1 è l'avversario, nel 2v2 il compagno di squadra (gli avversari arrivano dal matchmaking). Nel 2v2 si possono invitare più amici;
  - **contro la CPU**, dalla Partita Veloce: nel 1v1 contro una CPU, nel 2v2 con una CPU compagna contro due CPU. Le partite contro la CPU non si salvano e non contano per il rating.
- **Al tavolo**: 15 secondi per mossa (allo scadere il server gioca la carta che costa meno), le **frasi pronte** da mandare agli altri giocatori, in italiano e in siciliano ("Amunì!", "Baciamo le mani"…), animazioni e **suoni** delle carte. Chi perde la connessione può rientrare nella partita.
- **Account personali**: registrazione, login con nome utente o email, scelta di un avatar, suoni accesi o spenti, cancellazione dell'account.
- **Statistiche e rating**: partite vinte, perse e pareggiate, percentuale di vittorie e rating **Glicko-2** separato per 1v1 e 2v2 (provvisorio nelle prime 10 partite).
- **Amici**: richieste di amicizia, blocchi, chi è online, **chat** a testo libero e **inviti** a una partita.
- Pensata prima per lo **smartphone** (mobile-first), funziona anche da computer. La home non scorre mai.

### Com'è fatta l'interfaccia

C'è una sola pagina principale, la home; il tavolo di gioco si apre quando comincia una partita.

```
┌──────────────────────────────────┐
│ (M)        Cinquecento        [A]│  avatar (statistiche) · nome · amici e chat
├──────────────────────────────────┤  navbar trasparente, scritte sul panno
│        o 24 giocatori online     │
│  Partita Veloce                  │
│  ┌─────────┐    ┌─────────┐      │
│  │   1v1   │    │   2v2   │      │  carte-pulsante: toccata, vola al centro, si gira
│  └─────────┘    └─────────┘      │  e diventa il modal con i punti (150 / 300 / 500)
│  Gioca con un amico              │  e, nella Partita Veloce, giocatori o CPU
│  ┌─────────┐    ┌─────────┐      │
│  │   1v1   │    │   2v2   │      │  + la lista degli amici da invitare
│  └─────────┘    └─────────┘      │
└──────────────────────────────────┘
   sullo sfondo: panno verde con una cascata di carte siciliane
```

Il riferimento grafico è il prototipo in [docs/prototipo/](docs/prototipo/): si apre con un doppio clic su `index.html`.

## Il gioco in breve

Si gioca con 40 carte siciliane, con 5 carte in mano. All'inizio non c'è briscola: chi ha in mano **Re e Cavallo dello stesso seme** può **cantare 40**, e quel seme diventa briscola. I canti successivi valgono 20 (**cantare 20**). Non c'è obbligo di rispondere al seme. A mazzo finito chi è sicuro di prendere tutte le prese rimaste può **calare le carte**; nel 2v2, da quando ci sono insieme la briscola e il mazzo finito, si vedono le carte del compagno e gli si può consigliare quale giocare. Vince chi, a fine mano, arriva ad almeno il punteggio scelto per la partita: **150, 300 o 500 punti**.

Il regolamento completo è in [docs/REGOLE-GIOCO.md](docs/REGOLE-GIOCO.md).

## Tecnologie

| Parte | Tecnologia | Versione |
|---|---|---|
| Pagine | HTML, CSS, JavaScript "vanilla" (senza framework, con i moduli nativi `import`/`export`) | — |
| Server | Python + Flask | Python **3.14** (3.14.4) |
| Tempo reale | Flask-SocketIO (WebSocket: collegamento sempre aperto tra pagina e server) | versioni fissate in `requirements.txt` |
| Account | Flask-Login, Flask-WTF | idem |
| Database | MySQL, tramite Flask-SQLAlchemy e PyMySQL | MySQL **8.0** |
| Test | pytest, con un runner che lancia tutte le suite in sicurezza | versioni fissate in `requirements-dev.txt` |

Tutti i membri del gruppo usano **le stesse versioni** di Python e MySQL, installate a mano.

Il server è **autoritativo**: le regole stanno solo lì, la pagina manda soltanto le mosse e ogni giocatore riceve solo la propria vista della partita (mai le carte degli altri né l'ordine del mazzo).

## Struttura delle cartelle

Il **motore di gioco** (`app/game/engine/`) è Python puro: non sa niente di Flask, del database o della rete, e si può testare da solo. Il resto è diviso in livelli: gli **ingressi** (`blueprints/` per le pagine, `sockets/` per il tempo reale) ricevono le richieste, i **services** contengono la logica, i **repositories** sono l'unico punto che parla con MySQL.

```
cinquecento/
├── README.md                  questo file
├── .gitattributes             fine riga dei file, gestiti da git
├── .gitignore                 file che git non deve tracciare
├── .env.example               modello della configurazione (senza segreti)
├── requirements.txt           librerie Python del programma, a versione fissa
├── requirements-dev.txt       librerie usate solo per sviluppo e test
├── run.py                     avvio del server
├── config.py                  configurazioni: sviluppo, test, demo
│
├── docs/
│   ├── REGOLE-GIOCO.md        regolamento del gioco (riferimento unico)
│   ├── CONTRATTO-SOCKET.md    eventi scambiati tra pagine e server, formato della "vista"
│   ├── DEMO.md                installazione della demo, backup e giorno della demo
│   └── prototipo/             prototipo approvato della home, riferimento grafico
│
├── migrations/
│   └── 001_init.sql           creazione delle tabelle
│
├── scripts/
│   ├── setup_db.sql           crea database e utente MySQL (una volta sola)
│   ├── migrate.py             applica le migrazioni mancanti
│   ├── backup.py              backup del database
│   ├── ripristina.py          ripristino di un backup
│   └── pianifica_backup.ps1   backup automatico giornaliero (demo)
│
├── app/
│   ├── __init__.py            create_app(): monta tutte le parti dell'applicazione
│   ├── extensions.py          oggetti condivisi (database, login, socket)
│   ├── checks.py              controllo delle versioni di Python e MySQL all'avvio
│   ├── logging_config.py      configurazione dei log
│   ├── errors.py              pagine e messaggi di errore
│   │
│   ├── game/engine/           MOTORE DI GIOCO (Python puro)
│   │   ├── cards.py           carte, semi, valori, forza
│   │   ├── deck.py            mazzo e mescolata
│   │   ├── rules.py           parametri della variante (5 carte, 150/300/500 punti, 40/20…)
│   │   ├── errors.py          errori delle mosse non valide
│   │   ├── trick.py           chi vince la presa
│   │   ├── singing.py         cantare 40 e 20
│   │   ├── lay_down.py        calare le carte
│   │   ├── state.py           stato della mano e della partita
│   │   ├── actions.py         azioni possibili (gioca carta, canta, cala)
│   │   ├── game.py            applica un'azione allo stato; fine mano e fine partita
│   │   ├── views.py           vista di un solo giocatore e mosse legali
│   │   ├── auto_move.py       mossa automatica a tempo scaduto
│   │   └── cpu.py             mosse della CPU
│   │
│   ├── realtime/              PARTITE E PRESENZA IN CORSO (in memoria)
│   │   ├── events.py          nomi degli eventi socket
│   │   ├── room.py            una stanza: giocatori, timer, lock, riconnessione, CPU
│   │   ├── room_manager.py    elenco delle stanze attive, creazione delle stanze
│   │   ├── matchmaking.py     code 1v1 e 2v2, per punteggio
│   │   ├── presence.py        chi è online
│   │   ├── invites.py         inviti a partita tra amici
│   │   └── table_phrases.py   elenco delle frasi pronte del tavolo
│   │
│   ├── sockets/               ingressi in tempo reale (sottili)
│   │   ├── __init__.py        registra i gestori degli eventi
│   │   ├── connection_events.py   collegamento, scollegamento, controllo del login
│   │   ├── home_events.py     dati della home (utenti online, rientro in partita)
│   │   ├── lobby_events.py    code e partite contro la CPU
│   │   ├── game_events.py     gioca carta, canta, cala, consiglio, frasi del tavolo
│   │   ├── friends_events.py  amici online, inviti
│   │   └── chat_events.py     messaggi della chat
│   │
│   ├── blueprints/            ingressi delle pagine (sottili), uno per argomento
│   │   ├── main/              home
│   │   ├── auth/              registrazione, login, logout
│   │   ├── profile/           impostazioni: avatar, suoni e cancellazione dell'account
│   │   ├── game/              tavolo di gioco
│   │   ├── stats/             dati del pannello statistiche
│   │   └── friends/           richieste di amicizia e lista amici
│   │
│   ├── services/              logica applicativa
│   │   ├── auth_service.py
│   │   ├── avatars.py         elenco degli avatar ammessi
│   │   ├── friend_service.py
│   │   ├── chat_service.py
│   │   ├── match_service.py   salvataggio delle partite
│   │   ├── glicko2.py         calcolo del rating (algoritmo)
│   │   ├── rating_service.py  aggiornamento del rating dopo una partita
│   │   └── stats_service.py
│   │
│   ├── repositories/          unico accesso a MySQL
│   │   ├── user_repo.py  friend_repo.py  chat_repo.py
│   │   └── match_repo.py  rating_repo.py  stats_repo.py
│   │
│   ├── models/                tabelle del database viste da Python
│   │   ├── user.py
│   │   ├── rating.py
│   │   ├── match.py           partite, giocatori della partita, mosse
│   │   ├── friendship.py      richieste di amicizia, amicizie e blocchi
│   │   └── chat_message.py
│   │
│   ├── templates/             pagine HTML (Jinja2)
│   │   ├── base.html          struttura comune a tutte le pagine
│   │   ├── partials/          navbar, avatar, messaggi, avviso "Gira il telefono"
│   │   ├── errors/            404, 500
│   │   └── main/  auth/  profile/  game/
│   │
│   └── static/
│       ├── css/
│       │   ├── base/          reset, variabili (colori, spazi), tipografia, layout
│       │   ├── components/    un file per componente (carta, navbar, chat…)
│       │   └── pages/         un file per pagina
│       ├── js/
│       │   ├── core/          layout comune (navbar, pannelli), socket, suoni, nomi degli eventi
│       │   ├── components/    un file per componente (Card.js, Table.js, FriendsPanel.js…)
│       │   ├── pages/         un file per pagina (è l'unico script caricato dalla pagina)
│       │   ├── utils/         funzioni di utilità per il DOM
│       │   └── vendor/        librerie esterne a versione fissa (client Socket.IO)
│       ├── dev/               dati di esempio e pagina di prova delle carte (solo sviluppo e test)
│       ├── fonts/             font delle icone (solo le icone usate, elenco in icone.txt)
│       ├── sounds/            suoni del tavolo e del menu, con la loro licenza
│       └── img/
│           ├── cards/         immagini delle 40 carte, con la loro licenza
│           ├── cards-bg/      sfondo, dorso, logo e carte-pulsante, con la loro licenza
│           ├── avatars/       set di avatar predefiniti
│           └── favicon.*      icona della scheda del browser
│
└── tests/
    ├── esegui_tutti.py        runner: lancia tutte le suite in sicurezza
    ├── conftest.py            impostazioni comuni dei test
    ├── browser.py             aiuti per i test che aprono le pagine in Chrome o Edge
    ├── runner/                test del runner stesso
    ├── engine/                test del motore di gioco
    ├── db/                    test di migrazioni e backup
    ├── api/                   test delle pagine e degli account (via HTTP)
    ├── services/              test di salvataggio partite e rating
    ├── sockets/               test del tempo reale con client simulati
    ├── frontend/              prove nel browser: home, accesso, amici, chat, impostazioni
    ├── e2e/                   partite complete dall'inizio alla fine, con il server vero
    ├── forza/                 prove di forza della CPU contro un giocatore "medio"
    └── table/  table2/  table3/   il tavolo di gioco nel browser: momenti, animazioni, grafica
```

Nel branch `dev`, dove lavora il gruppo, ci sono anche i documenti di lavoro (scaletta, decisioni, domande aperte, riepiloghi): vedi "Come lavoriamo".

## Installazione (Windows)

Questi passi servono per installare il progetto sul proprio PC e farlo girare in `localhost`. L'installazione della **demo**, con dati veri e raggiungibile dagli altri, ha una guida a parte: [docs/DEMO.md](docs/DEMO.md).

**Cosa serve prima**
- **Python 3.14.4**, **MySQL Server 8.0** e **Git**, installati a mano (passi 1–3).
- Per i test: **Google Chrome** o **Microsoft Edge** (i test che aprono le pagine nel browser li usano senza finestra; se mancano, quei test si saltano) e, facoltativo, **Node.js** (un test confronta i nomi delle carte delle pagine con quelli del motore eseguendo `Card.js`; senza Node quel controllo si salta).
- **Internet** la prima volta che lanci i test: i font di Google si scaricano una volta sola, in una cartella temporanea.

I comandi qui sotto sono per **PowerShell**, lanciati dalla cartella del progetto.

1. **Installa Python 3.14.4** da [python.org](https://www.python.org/downloads/). Durante l'installazione spunta "Add python.exe to PATH". Controlla con `py -3.14 --version`, che deve rispondere `Python 3.14.4`.
2. **Installa MySQL Server 8.0** da [dev.mysql.com](https://dev.mysql.com/downloads/installer/) e annota la password dell'utente `root`. Lascia la cartella proposta (`C:\Program Files\MySQL\MySQL Server 8.0`): il comando del passo 6, i backup e i test cercano lì i programmi di MySQL.
3. **Scarica il progetto** ed entra nella cartella:
   ```
   git clone https://github.com/zChrees/cinquecento.git
   cd cinquecento
   ```
   Così scarichi `main`, la versione di produzione. Per lavorare al progetto con il gruppo scarica invece `dev`: `git clone -b dev https://github.com/zChrees/cinquecento.git`.
4. **Crea l'ambiente virtuale** (una cartella `.venv` con le librerie del progetto, separate dal resto del PC) e installa le librerie:
   ```
   py -3.14 -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt -r requirements-dev.txt
   ```
   Se PowerShell rifiuta `activate` ("l'esecuzione di script è disabilitata"), lancia una volta `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` e riprova. Con l'ambiente attivo, all'inizio della riga compare `(.venv)`: da qui in poi tutti i comandi si lanciano così, anche dopo aver chiuso e riaperto il terminale (basta rifare `.venv\Scripts\activate`).
5. **Configura**: copia il modello e genera la chiave segreta:
   ```
   copy .env.example .env
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
   Apri `.env` con un editor di testo e incolla dopo `SECRET_KEY=` la riga stampata dal secondo comando. Gli altri valori vanno bene così; la password del database arriva al passo 6. Il file `.env` contiene segreti: non va mai su git (è già in `.gitignore`), e conviene tenerne una copia fuori dal progetto.
6. **Prepara il database** (una volta sola). Il comando chiede la password di `root`:
   ```
   & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p --table -e "source scripts/setup_db.sql"
   ```
   Crea i database `cinquecento_dev` e `cinquecento_test` e l'utente MySQL `cinquecento`, e mostra **una sola volta** la sua password nella colonna `generated password`. Copiala nel `.env`, tra apici singoli:
   ```
   DB_USER=cinquecento
   DB_PASSWORD='la-password-mostrata'
   ```
   Se l'hai persa, in cima a `scripts/setup_db.sql` c'è il comando per generarne una nuova. Poi crea le tabelle (rilanciato, non fa niente):
   ```
   python scripts/migrate.py
   ```
7. **Avvia**: `python run.py`, poi apri `http://localhost:5000` e registra un account. All'avvio il programma controlla di avere Python 3.14 e MySQL 8.0, e se qualcosa manca lo scrive e si ferma: per esempio "errore MySQL 1045" vuol dire che `DB_USER` o `DB_PASSWORD` nel `.env` non sono giusti. Per spegnerlo: Ctrl+C nel terminale.
8. **Controlla con i test** che sia tutto a posto (sezione qui sotto): devono risultare tutti PASS.

## Test

```
python tests/esegui_tutti.py            tutte le suite
python tests/esegui_tutti.py engine     una sola suite (il nome è la cartella in tests/)
ruff check .                            controllo del codice (deve dire "All checks passed!")
```

Le suite sono le cartelle di `tests/`: `runner`, `engine`, `db`, `api`, `services`, `sockets`, `frontend`, `e2e`, e poi `forza`, `table`, `table2` e `table3`. I test provano il programma vero dall'esterno quando possono: avviano il server, simulano più giocatori collegati insieme e aprono le pagine nel browser. Il giro completo dura circa un quarto d'ora; ogni suite ha al massimo 240 secondi. Alla fine il runner stampa una riga per suite (PASS o FAIL, con il numero di controlli) ed esce con 0 se è tutto PASS, 1 se c'è almeno un FAIL e 2 se si rifiuta di partire.

Prima di lanciarli:
- chiudi le schede del browser aperte sul sito: una scheda collegata può disturbare i test del tempo reale;
- la porta **5099** deve essere libera: se il runner dice che è occupata, chiudi il programma che la usa (per esempio un server di test rimasto acceso);
- lascia il PC libero da programmi pesanti (per esempio un gioco aperto): i test del tavolo misurano tempi e animazioni, e con il PC carico qualcuno può fallire.

I test usano **solo** il database `cinquecento_test` e la porta 5099. Si rifiutano di partire se nella cartella c'è il file `PRODUZIONE`, che segnala un'installazione con dati veri, o se il database dei test non finisce con `_test`.

## Come lavoriamo

Il progetto è diviso tra **Giuseppe** (motore di gioco e tempo reale), **Antonio** (account, dati, amici) e **Christian** (interfaccia e documenti); il lavoro è stato fatto con l'aiuto di Claude Code.

- Branch permanenti: `main` (produzione: la versione per la demo e la presentazione, con i soli file del sito) e `dev` (lavoro e integrazione del gruppo).
- Il lavoro è diviso in **punti** (P1, P2, …), elencati nella scaletta. Per ogni punto si crea un **branch nuovo da `dev` aggiornato**, si modificano **solo i file indicati nel punto**, si testa e, **solo dopo l'ok** di chi lavora, si fanno commit, merge fast-forward in `dev` e push.
- Finito un punto, ognuno scrive il riepilogo nel proprio file (`christian.md`, `giuseppe.md`, `antonio.md`); i documenti condivisi li aggiorna, a fine giornata, chi il gruppo sceglie.

I documenti di lavoro stanno solo nel branch `dev`:
- [SCALETTA.md](https://github.com/zChrees/cinquecento/blob/dev/SCALETTA.md): cosa fare, in che ordine, quali file tocca ogni punto, chi lo fa;
- [DECISIONI.md](https://github.com/zChrees/cinquecento/blob/dev/DECISIONI.md): cosa è già stato deciso e perché;
- [DA-DECIDERE.md](https://github.com/zChrees/cinquecento/blob/dev/DA-DECIDERE.md): domande aperte;
- [CLAUDE.md](https://github.com/zChrees/cinquecento/blob/dev/CLAUDE.md): regole di lavoro complete (git, test, convenzioni del codice).

## Documenti

- [docs/REGOLE-GIOCO.md](docs/REGOLE-GIOCO.md): regolamento del gioco
- [docs/CONTRATTO-SOCKET.md](docs/CONTRATTO-SOCKET.md): eventi tra pagine e server, formato dei dati
- [docs/DEMO.md](docs/DEMO.md): installazione della demo, backup e giorno della demo
- [docs/prototipo/LEGGIMI.md](docs/prototipo/LEGGIMI.md): prototipo della home, risorse esterne e font

## Crediti

- **Immagini delle carte**: Matsoftware, [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/deed.it), da Wikimedia Commons (dettagli in `app/static/img/cards/LICENZA.md` e `app/static/img/cards-bg/LICENZA.md`).
- **Suoni**: Kenney (pacchetti Casino Audio, Interface Sounds, Music Jingles e Digital Audio), CC0 (dettagli in `app/static/sounds/LICENZA.md`).
