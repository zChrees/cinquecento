# Messa online di Cinquecento

Piano del 24/10/2026 (Christian, con Claude) per portare il sito su internet: prima solo per gli amici, poi aperto al pubblico. Chiude D21: **un VPS** (un computer Linux in affitto), gestito da **Christian**.

Ogni punto si fa come sempre: un branch da `dev` per lotto, solo i file elencati, test dei file toccati, riepilogo nel proprio file, ok esplicito per commit, merge e push (D2). Lo stato dei punti si tiene in `REVIEW.md` (chi è di turno sui documenti), non qui.

## 1. Da dove partiamo

- Il sito è un **solo processo** Python (Flask + Flask-SocketIO in modalità `threading`) con **MySQL 8.0** accanto. Le partite in corso stanno **in memoria**: un riavvio del server le perde (sezione 8 di `docs/archivio/MIGRAZIONE-FRONTEND-2026-10.md`).
- Oggi gira il **server di sviluppo** di Werkzeug (`ALLOW_UNSAFE_WERKZEUG`, R12), senza HTTPS, con il cookie di sessione non `Secure` (R8).
- Il frontend è una SPA React compilata da Vite in `app/static/dist/`, che non è nel repository (D54): sul server va compilata con Node 24.
- `main`, il branch di produzione, è ancora "Cinquecento v1.0.3" con il JavaScript vecchio.
- Meno di 50 persone collegate insieme: un processo basta. Redis serve solo con più processi (più avanti, se servirà).

## 2. Chi fa cosa

| Persona | Parte | In questo piano |
|---|---|---|
| **Christian** | interfaccia, documenti, server | configurazione di produzione, il VPS, HTTPS, backup, aggiornamenti, privacy |
| **Giuseppe** | motore e tempo reale | server di produzione (gunicorn), salvataggio che riprova, spegnimento ordinato, prova di carico |
| **Antonio** | account, dati, amici | recupero della password, sessioni, limiti degli amici. **Finché Antonio non torna, li fa Giuseppe** (regola del 28/09) |

## 3. Le fasi

| Fase | Cosa | Quando è finita |
|---|---|---|
| **0** | Pulizia generale del codice | niente codice morto, commenti che descrivono il presente |
| **1** | Codice pronto per la produzione | il sito parte con `APP_ENV=production` e gunicorn su Linux |
| **2** | Il server | il sito risponde in HTTPS sul dominio, con backup e aggiornamenti scritti |
| **3** | Online per gli amici | prova in tre, poi gli amici giocano davvero |
| **4** | Prima del pubblico | recupero della password, privacy, sicurezza, carico |

## 4. I punti

Colonna "Attende": i punti che devono essere già in `dev` su GitHub prima di cominciare.

### Fase 0 — Pulizia generale (prima di tutto il resto)

Niente cambia per chi gioca: si toglie solo quello che non serve più e si riscrivono i commenti che raccontano la storia ("dal lotto 9c…", "prima era…") perché descrivano com'è il codice oggi. La storia resta in git, in `DECISIONI.md` e in `docs/archivio/`.

| Punto | Cosa | Chi | File | Attende |
|---|---|---|---|---|
| **C1** | Frontend: commenti di `frontend/src/` senza la storia della migrazione; classi CSS che nessun componente usa più (con uno script che le cerca), tolte | Christian | `frontend/src/`, `app/static/css/` | — |
| **C2** | Sito: commenti di `app/blueprints/`, `app/__init__.py`, `app/errors.py`, `config.py` senza la storia | Christian | quei file | — |
| **C3** | Motore e tempo reale: commenti di `app/game/`, `app/realtime/`, `app/sockets/`, `app/services/`, `app/repositories/` senza la storia; `friend_repo.get_user`, che non usa nessuno, tolto | Giuseppe | quei file | — |
| **C4** | Test: commenti e docstring senza la storia; i file `test_spa_*.py` rinominati senza "spa" (oggi "spa" vuol dire solo "dopo la migrazione"; scelta di Christian del 24/10), controllando chi li importa | Christian e Giuseppe, ognuno le sue suite | `tests/` | C1–C3 |
| **C5** | Documenti: `docs/MIGRAZIONE-FRONTEND.md` e `docs/DEMO.md` in `docs/archivio/`; `scripts/pianifica_backup.ps1` e il suo test tolti (la demo su Windows non c'è più; il backup pianificato lo rifà S5); `README.md` e `docs/prototipo/LEGGIMI.md` riscritti sul frontend React; nel `README.md` una riga che spiega i codici P, D e R dei commenti (rimandano ai documenti interni del gruppo: punti del piano di lavoro, decisioni, revisioni) | Christian (di turno sui documenti) | quei file, `tests/db/test_demo.py` | — |
| **C6** | `CLAUDE.md`: riscrittura dei punti delicati e delle parti "Stack", "Pagine", "Dipendenze" | chi è di turno sui documenti | `CLAUDE.md` | C1–C5 |

### Fase 1 — Codice pronto per la produzione

| Punto | Cosa | Chi | File | Attende |
|---|---|---|---|---|
| **O1** | Configurazione **`production`** al posto di `demo`: senza DEBUG, `SESSION_COOKIE_SECURE` da una variabile del `.env` (**R8**), `ProxyFix` (Flask vede l'indirizzo vero di chi si collega, dietro il proxy), `.env.example` aggiornato | Christian | `config.py`, `app/__init__.py`, `.env.example`, `tests/api/test_avvio.py` | C2 |
| **O2** | **Server vero (R12)**: gunicorn su Linux con un worker e più thread, con il websocket; prima una prova che Flask-SocketIO in modalità `threading` funzioni così (da verificare, non ancora provato); `requirements.txt` con gunicorn solo su Linux; comando di avvio scritto | Giuseppe | `requirements.txt`, `run.py` o un file nuovo `wsgi.py`, test | O1 |
| **O3** | **R6**: il salvataggio di una partita riprova se MySQL non risponde (per esempio durante un suo riavvio), senza bloccare la stanza | Giuseppe | `app/realtime/room.py`, `app/services/match_service.py`, test | — |
| **O4** | **Spegnimento ordinato**: prima di un aggiornamento il server smette di creare partite nuove (avviso nella home) e aspetta che finiscano quelle in corso, con un tempo massimo | Giuseppe (server), Christian (avviso nella home) | `app/realtime/`, `app/sockets/`, `frontend/src/pages/HomePage.tsx` | O2 |
| **O5** | `GET /api/health`: risponde "ok" se il server e MySQL rispondono (lo usa il controllo esterno di S7) | Christian | `app/blueprints/main/routes.py`, test | O1 |

### Fase 2 — Il server (Christian)

| Punto | Cosa | Attende |
|---|---|---|
| **S1** | VPS con Ubuntu LTS in un centro dati europeo; utente senza i permessi di root per tutti i giorni, accesso SSH solo con le chiavi, firewall (solo le porte 22, 80 e 443), aggiornamenti di sicurezza automatici | — |
| **S2** | **Nome di dominio** (D55): serve per il certificato HTTPS gratuito di Let's Encrypt | — |
| **S3** | Programmi: Python 3.14 (va installato a parte, Ubuntu ne ha uno più vecchio), MySQL 8.0, Node 24 per il build, Caddy (il proxy, che fa anche l'HTTPS da solo) | S1 |
| **S4** | `main` aggiornato al codice di oggi (`frontend/` sì, `app/static/js/` e i template tolti no), con l'elenco dei file e l'ok per ognuno, come sempre | C1–C6, O1–O3 |
| **S5** | Installazione: utente di servizio, cartella del sito, `.env` di produzione con una `SECRET_KEY` nuova, `setup_db.sql`, `migrate.py`, `npm ci` e `npm run build`, il servizio di systemd (riavvio automatico), Caddy davanti con il websocket. Tutto scritto in un documento nuovo, `docs/SERVER.md` | S2, S3, S4 |
| **S6** | Backup su Linux: `backup.py` ogni giorno con un timer di systemd e una **copia fuori dal server** (R14); prova di ripristino su `cinquecento_test` | S5 |
| **S7** | Aggiornare il sito: uno script `deploy.sh` (fine riga LF) che fa pull di `main`, build, migrazioni e riavvio, usando O4; controllo esterno che il sito risponda (O5), spazio su disco, log | S5, O4, O5 |

### Fase 3 — Online per gli amici

| Punto | Cosa | Chi | Attende |
|---|---|---|---|
| **A1** | Giro completo delle suite su `dev` prima di aggiornare `main` | Christian | fasi 0–1 |
| **A2** | Prova in tre sul server vero, da casa e dal telefono (la lista di `prova-a-mano.md`), più un aggiornamento e un ripristino di prova | tutti | fase 2 |
| **A3** | Si apre agli amici: si raccolgono i problemi come punti nuovi di `REVIEW.md` | tutti | A2 |

### Fase 4 — Prima di aprire al pubblico

| Punto | Cosa | Chi | Attende |
|---|---|---|---|
| **P1** | **Recupero della password** con un'email: servizio di invio (da scegliere, D56), codice monouso con scadenza (tabella nuova, migrazione `002_…`), pagine React "Password dimenticata" e "Nuova password" | Antonio (ora Giuseppe); pagine: Christian | A3 |
| **P2** | **R9**: le sessioni si possono chiudere (per esempio dopo il cambio della password); serve una colonna nuova | Antonio (ora Giuseppe) | P1 |
| **P3** | **R11**: limite sulle richieste HTTP degli amici, come quello degli eventi in tempo reale | Antonio (ora Giuseppe) | — |
| **P4** | **Privacy**: informativa (quali dati, perché, per quanto, come cancellarli), pagina React `/privacy`, link nella registrazione; solo cookie tecnici, quindi niente banner (da ricontrollare quando si scrive) | Christian | A3 |
| **P5** | Rischi residui R5 e R10, e **R16** (piccole copie nel codice): da rivedere con il sito pubblico | Giuseppe (R5, R16), Antonio (R10, ora Giuseppe) | A3 |
| **P6** | **Prova di carico**: molti client simulati (per esempio 50 collegati e 10 partite insieme) sul server vero; si misura memoria e tempi | Giuseppe | A3 |

## 5. Decisioni e domande

- **Deciso (24/10, Christian)**: VPS; prima solo per gli amici, poi pubblico; il server lo gestisce Christian; il budget non è un problema.
- **D55 — nome di dominio** (in `DA-DECIDERE.md`): quale comprare. Serve prima di S5.
- **D56 — servizio per mandare le email** (solo per la fase 4).
- La fase 0 si fa prima delle altre (Christian, 24/10); in C4 i test si rinominano.
- Questo file non va in `main` (come `docs/archivio/`).
- I codici P, D e R nei commenti **restano**; il `README.md` spiega cosa sono (C5; scelta di Christian del 24/10, opzione c).
