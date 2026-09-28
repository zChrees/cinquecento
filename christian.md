# Riepiloghi di Christian

> **Questo file lo scrive solo Christian** (Studente 3: interfaccia e documenti). Giuseppe e Antonio lo leggono dopo il `git pull` di `dev`, per sapere cosa è cambiato: punti fatti, decisioni nuove e cosa devono fare loro. Nessun altro lo modifica, nemmeno per correggere un errore: si segnala a Christian.
>
> **Come si aggiorna** (regola in `CLAUDE.md`, "Consegna"): a fine punto, e dopo ogni aggiornamento dei documenti condivisi, Christian aggiunge il riepilogo **in cima** alla sezione "Riepiloghi", nello stesso branch e commit; così arriva in `dev` con il merge. È il gemello di `giuseppe.md`.

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
  - `Hand(carte, { playable, onPlay })` mette le carte in fila dritta e rende giocabili solo quelle di `legal.cards`; `HiddenHand(n)` mostra n carte coperte (per `cards_in_hand` degli avversari);
  - la pagina di prova `http://localhost:5000/static/dev/carte.html` mostra le 40 carte, il dorso, una mano da 5 e 3 carte coperte.
- **Decisioni prese**: faccia con valore e Asso del seme, mano in fila dritta, pagina di prova con i font di Google; D39 chiusa (crediti anche nella finestra di accesso).
- **Domande nuove**: nessuna
- **Punti delicati**: queste carte si vedono **in gioco** finché P35 non porta quelle vere; P35 cambia solo la faccia (`Card.js`, `card.css`).
- **Proposta importante per le carte vere (P35, D19)**: le immagini che usiamo già (Cavallo, Re, Asso e Tre) sono ritagli delle scansioni di **Matsoftware** su Wikimedia Commons, un foglio per seme, con licenza **CC BY-SA 3.0**. Probabilmente ogni foglio contiene tutte le 10 carte del seme: si potrebbero ritagliare da lì **tutte le 40 carte**, con la riga dei crediti che c'è già. **Non è ancora verificato**: va controllato all'inizio di P35 aprendo le quattro scansioni. Se avete immagini vostre da proporre, ditelo (D19).
- **Cosa devono fare gli altri**:
  - **Giuseppe** (P24): la mano del tavolo si costruisce con `Hand(view.hand, { playable: view.legal.cards, onPlay })`; la carta toccata arriva come `{suit, rank}`, già nella forma del campo `card` di `game:play_card`;
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
