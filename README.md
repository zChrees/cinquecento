# Cinquecento

Web-app per giocare online a **Cinquecento**, il gioco di carte siciliano simile alla briscola (variante siciliana, detta anche Marianna), con le **carte siciliane**.

- Partite **1v1** e **2v2** a **150, 300 o 500 punti**, dalla home:
  - **Partita Veloce**: la **coda di matchmaking** abbina giocatori di livello simile in base al rating;
  - **Gioca con un amico**: si invita un amico online; nel 1v1 è l'avversario, nel 2v2 il compagno di squadra (gli avversari arrivano dal matchmaking).
- **Account personali**: registrazione, login, scelta di un avatar, cancellazione dell'account, **statistiche**.
- **Amici**: richieste di amicizia, chi è online, **chat** e **inviti** a una 1v1 o 2v2.
- Pensata prima per lo **smartphone** (mobile-first), funziona anche da computer. La home non scorre mai.

### Com'è fatta l'interfaccia

```
┌──────────────────────────────────┐
│ (M)        Cinquecento        [A]│  avatar (statistiche) · nome · amici e chat
├──────────────────────────────────┤  navbar trasparente e sfocata
│        o 24 giocatori online     │
│  Partita Veloce                  │
│  ┌─────────┐    ┌─────────┐      │
│  │   1v1   │    │   2v2   │      │  carte-pulsante: si apre il modal
│  └─────────┘    └─────────┘      │  con i punti (150 / 300 / 500) e "Gioca"
│  Gioca con un amico              │
│  ┌─────────┐    ┌─────────┐      │
│  │   1v1   │    │   2v2   │      │  + la lista degli amici da invitare
│  └─────────┘    └─────────┘      │
└──────────────────────────────────┘
   sullo sfondo: carte siciliane sparse negli spazi vuoti
```

Il riferimento grafico è il prototipo in [docs/prototipo/](docs/prototipo/): si apre con un doppio clic su `index.html`.

> **Stato del progetto:** in preparazione. Il codice non è ancora stato scritto. Le istruzioni di installazione qui sotto descrivono come funzionerà il progetto quando saranno fatti i punti P4–P6 della [scaletta](SCALETTA.md).

## Il gioco in breve

Si gioca con 40 carte siciliane, con 5 carte in mano. All'inizio non c'è briscola: chi ha in mano **Re e Cavallo dello stesso seme** può **cantare 40**, e quel seme diventa briscola. I canti successivi valgono 20 (**cantare 20**). Non c'è obbligo di rispondere al seme. Vince chi, a fine mano, arriva ad almeno il punteggio scelto per la partita: **150, 300 o 500 punti**.

Il regolamento completo è in [docs/REGOLE-GIOCO.md](docs/REGOLE-GIOCO.md).

## Tecnologie

| Parte | Tecnologia | Versione |
|---|---|---|
| Pagine | HTML, CSS, JavaScript "vanilla" (senza framework, con i moduli nativi `import`/`export`) | — |
| Server | Python + Flask | Python **3.14** (3.14.4) |
| Tempo reale | Flask-SocketIO (WebSocket: collegamento sempre aperto tra pagina e server) | versioni fissate in `requirements.txt` |
| Account | Flask-Login, Flask-WTF | idem |
| Database | MySQL, tramite Flask-SQLAlchemy e PyMySQL | MySQL **8.0** |
| Test | pytest, con un runner che li lancia tutti in sicurezza | idem |

Tutti i membri del gruppo usano **le stesse versioni** di Python e MySQL, installate a mano.

## Struttura delle cartelle

Il **motore di gioco** (`app/game/engine/`) è Python puro: non sa niente di Flask, del database o della rete, e si può testare da solo. Il resto è diviso in livelli: gli **ingressi** (`blueprints/` per le pagine, `sockets/` per il tempo reale) ricevono le richieste, i **services** contengono la logica, i **repositories** sono l'unico punto che parla con MySQL.

```
cinquecento/
├── README.md                  questo file
├── CLAUDE.md                  istruzioni di lavoro per Claude Code
├── SCALETTA.md                elenco dei punti da fare (tracker attivo)
├── DECISIONI.md               decisioni già prese, con data e motivo
├── DA-DECIDERE.md             domande ancora aperte
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
│   ├── DEMO.md                lista di controllo per il giorno della demo
│   ├── prototipo/             prototipo approvato della home (P52), riferimento grafico
│   └── archivio/              tracker chiusi (non più aggiornati)
│
├── migrations/
│   └── 001_init.sql           creazione delle tabelle
│
├── scripts/
│   ├── setup_db.sql           crea database e utente MySQL (una volta sola)
│   ├── migrate.py             applica le migrazioni mancanti
│   ├── backup.py              backup del database
│   └── ripristina.py          ripristino di un backup
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
│   │   ├── state.py           stato della partita
│   │   ├── actions.py         azioni possibili (gioca carta, canta)
│   │   ├── game.py            applica un'azione allo stato; fine mano e fine partita
│   │   ├── views.py           vista di un solo giocatore e mosse legali
│   │   └── auto_move.py       mossa automatica a tempo scaduto
│   │
│   ├── realtime/              PARTITE E PRESENZA IN CORSO (in memoria)
│   │   ├── events.py          nomi degli eventi socket
│   │   ├── room.py            una stanza: giocatori, timer, lock, riconnessione
│   │   ├── room_manager.py    elenco delle stanze attive, creazione delle stanze
│   │   ├── matchmaking.py     code 1v1 e 2v2, per punteggio
│   │   ├── presence.py        chi è online
│   │   └── invites.py         inviti a partita tra amici
│   │
│   ├── sockets/               ingressi in tempo reale (sottili)
│   │   ├── __init__.py        registra i gestori degli eventi
│   │   ├── connection_events.py   collegamento, scollegamento, controllo del login
│   │   ├── home_events.py     dati della home (utenti online, rientro in partita)
│   │   ├── lobby_events.py    entrata e uscita dalle code
│   │   ├── game_events.py     gioca carta, canta, riconnessione
│   │   ├── friends_events.py  amici online, inviti
│   │   └── chat_events.py     messaggi della chat
│   │
│   ├── blueprints/            ingressi delle pagine (sottili), uno per argomento
│   │   ├── main/              home
│   │   ├── auth/              registrazione, login, logout
│   │   ├── profile/           impostazioni: avatar e cancellazione dell'account
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
│   │   ├── user_repo.py
│   │   ├── friend_repo.py
│   │   ├── chat_repo.py
│   │   ├── match_repo.py
│   │   ├── rating_repo.py
│   │   └── stats_repo.py
│   │
│   ├── models/                tabelle del database viste da Python
│   │   ├── user.py
│   │   ├── rating.py
│   │   ├── match.py           partite, giocatori della partita, eventi
│   │   ├── friendship.py      richieste di amicizia, amicizie (ed eventuali blocchi)
│   │   └── chat_message.py
│   │
│   ├── templates/             pagine HTML (Jinja2)
│   │   ├── base.html          struttura comune a tutte le pagine
│   │   ├── partials/          navbar, messaggi
│   │   ├── errors/            404, 500
│   │   ├── main/              home (index.html)
│   │   ├── auth/  profile/  game/
│   │
│   └── static/
│       ├── css/
│       │   ├── base/          reset, variabili (colori, spazi), tipografia, layout
│       │   ├── components/    un file per componente (carta, navbar, chat…)
│       │   └── pages/         un file per pagina
│       ├── js/
│       │   ├── core/          layout comune (navbar, pannelli statistiche e amici), socket, nomi degli eventi
│       │   ├── components/    un file per componente (Card.js, FriendsPanel.js, ChatWindow.js…)
│       │   ├── pages/         un file per pagina (è l'unico script caricato dalla pagina)
│       │   ├── utils/         funzioni di utilità per il DOM
│       │   └── vendor/        librerie esterne a versione fissa (client Socket.IO)
│       ├── dev/               dati di esempio e pagina di prova delle carte (solo sviluppo)
│       └── img/
│           ├── cards/         immagini delle 40 carte, con la loro licenza
│           ├── cards-bg/      carte siciliane dello sfondo della home (CC BY-SA 3.0)
│           ├── avatars/       set di avatar predefiniti
│           └── logo.*         logo "Cinquecento"
│
└── tests/
    ├── esegui_tutti.py        runner: lancia tutte le suite in sicurezza
    ├── conftest.py            impostazioni comuni dei test
    ├── runner/                test del runner stesso
    ├── engine/                test del motore di gioco
    ├── db/                    test di migrazioni e backup
    ├── api/                   test delle pagine e degli account (via HTTP)
    ├── services/              test di salvataggio partite e rating
    ├── sockets/               test del tempo reale con client simulati
    ├── frontend/              controlli sul codice delle pagine
    └── e2e/                   partite complete dall'inizio alla fine
```

La tabella "file → punto della scaletta" (chi crea e chi modifica ogni file) è in [SCALETTA.md](SCALETTA.md), nella sezione "Mappa dei file".

## Installazione (Windows)

> Disponibile dopo i punti P4 (scheletro), P5 (database) e P6 (test) della scaletta.

1. **Installa Python 3.14.4** da [python.org](https://www.python.org/downloads/). Durante l'installazione spunta "Add python.exe to PATH". Controlla con `py -3.14 --version`.
2. **Installa MySQL Server 8.0** da [dev.mysql.com](https://dev.mysql.com/downloads/installer/) e annota la password dell'utente `root`.
3. **Scarica il progetto** e entra nella cartella:
   ```
   git clone https://github.com/zChrees/cinquecento.git
   cd cinquecento
   ```
4. **Crea l'ambiente virtuale** (una cartella `.venv` con le librerie del progetto, separate dal resto del PC) e installa le librerie:
   ```
   py -3.14 -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt -r requirements-dev.txt
   ```
5. **Configura**: copia `.env.example` in `.env` e compila i valori (password del database, chiave segreta). Il file `.env` non va mai caricato su git.
6. **Prepara il database** (una volta sola), poi applica le tabelle:
   ```
   mysql -u root -p < scripts/setup_db.sql
   python scripts/migrate.py
   ```
7. **Avvia**: `python run.py`, poi apri `http://localhost:5000`.

## Test

```
python tests/esegui_tutti.py            tutte le suite
python tests/esegui_tutti.py engine     una sola suite (il nome è la cartella in tests/)
```

I test usano **solo** il database `cinquecento_test` e la porta 5099. Si rifiutano di partire se nella cartella c'è il file `PRODUZIONE`, che segnala un'installazione con dati veri.

## Come lavoriamo

- Branch permanenti: `main` (non si tocca) e `dev` (lavoro del gruppo).
- Per ogni punto della scaletta si crea un **branch nuovo da `dev` aggiornato**. Lì si modifica e si testa, e **solo dopo l'ok** si fa il commit e il merge in `dev`.
- Si modificano **solo i file indicati nel punto**. La divisione dei punti tra i tre studenti, e l'ordine in cui farli per non creare conflitti, sono nella sezione 9 di [SCALETTA.md](SCALETTA.md).
- Il regolamento, le decisioni prese e le domande aperte stanno nei documenti elencati sopra: prima di cambiare qualcosa, controlla lì.

## Documenti

- [SCALETTA.md](SCALETTA.md): cosa fare, in che ordine, quali file tocca ogni punto
- [DECISIONI.md](DECISIONI.md): cosa è già stato deciso e perché
- [DA-DECIDERE.md](DA-DECIDERE.md): domande aperte
- [docs/REGOLE-GIOCO.md](docs/REGOLE-GIOCO.md): regolamento
