# Riepiloghi di Antonio

> **Questo file lo scrive solo Antonio** (Studente 2: account, dati, amici). Christian lo legge dopo il `git pull` di `dev` e da qui aggiorna i documenti condivisi (`SCALETTA.md`, `CLAUDE.md`, `DECISIONI.md`, `DA-DECIDERE.md`); Giuseppe lo legge per sapere cosa è cambiato. Nessun altro lo modifica, nemmeno per correggere un errore: si segnala ad Antonio.
>
> **Come si aggiorna** (regola in `CLAUDE.md`, "Consegna"): a fine punto, nel branch del punto (`feature/…`, `fix/…`), Antonio aggiunge il riepilogo **in cima** alla sezione "Riepiloghi", nello stesso commit del punto; così arriva in `dev` con il merge. Il numero del commit non si scrive: lo si trova con `git log -- antonio.md`.
>
> **Cosa legge Antonio**: dopo il `git pull` di `dev`, `christian.md` e `giuseppe.md`, per le modifiche al progetto e le informazioni utili al suo lavoro (per esempio le funzioni da usare senza modificarle, come `create_room(...)` di P24).

## Schema

```markdown
### P<numero> — <titolo> (<data>)

- **Branch**: feature/…
- **File**: creati …; modificati … (se fuori elenco: perché e con l'ok di chi)
- **Controlli**: <N> PASS in tutto (<M> nuovi), `ruff check .` pulito
- **Decisioni prese**: … oppure "nessuna"
- **Domande nuove**: … oppure "nessuna"
- **Punti delicati**: …
- **Note per il contratto o per gli altri**: … oppure "nessuna"
```

## Riepiloghi

<!-- Il più recente in cima. File creato da Christian il 28/09/2026 con lo schema; da qui in poi lo scrive solo Antonio. Il riepilogo di P16 (punto di Antonio fatto da Giuseppe) è in giuseppe.md, quello di P5 (fatto da Christian) in christian.md. -->

### P7 — Log ed errori di base (28/09/2026)

- **Branch**: feature/p7-log-errori
- **File**: modificati `app/logging_config.py`, `app/errors.py` (segnaposto di P4); creati `app/templates/errors/404.html`, `app/templates/errors/500.html`, `tests/api/test_errori.py`. Nessun file fuori elenco
- **Controlli**: 809 PASS in tutto (19 nuovi, nella suite `api`), `ruff check .` pulito
- **Decisioni prese** (scelte di Antonio sulle raccomandazioni di Claude):
  - **pagine di errore senza navbar**: solo il messaggio e "Torna alla home". Non hanno uno script di pagina, e senza quello la navbar non si apre; in più la pagina 500 così dipende il meno possibile dal database. Se anche la pagina 500 non si può mostrare (per esempio il database non risponde e `base.html` cerca l'utente), si risponde con una pagina minima scritta in `errors.py`;
  - **nel file di log niente righe delle singole richieste** del server web, che contengono l'indirizzo IP (un dato personale): restano sul terminale; nel file vanno i messaggi dell'applicazione e solo WARNING ed ERROR del server web;
  - **errori delle richieste JSON** (`/stats/…`, `/friends/…`) nella forma del contratto (1.2): `{"ok": false, "error": {"code": "not_found" | "server_error", "message"}}`; le altre richieste ricevono la pagina HTML.
- **Scelte tecniche**: file `logs/cinquecento.log`, con rotazione a 1 MB e 5 file vecchi; formato `data ora LIVELLO [parte del programma] messaggio`; il livello viene da `LOG_LEVEL` del `.env`. Gli errori imprevisti degli eventi socket, nei gestori che non usano `handler` di `events.py`, vanno nel log con il solo nome dell'evento (mai i dati, che possono contenere testo degli utenti) e rispondono `server_error` solo a chi ha mandato l'evento; se si rompe il controllo di `connect`, la connessione si rifiuta.
- **Domande nuove**: nessuna
- **Punti delicati**:
  - negli errori del database SQLAlchemy scrive i valori della query (email, hash della password) e MySQL il valore doppio (`Duplicate entry 'Mario'`): `SafeFormatter` in `logging_config.py` li nasconde prima di scrivere la riga (c'è un test). Resta valida la regola: **mai** dati personali, password, token o testo della chat nei messaggi di log;
  - i test non scrivono mai in `logs/`: con la configurazione `testing` il file si apre solo se `LOG_DIR` punta altrove (i test usano una cartella temporanea);
  - `create_app()` chiamata più volte (succede nei test) non raddoppia il file di log: il gestore vecchio si toglie e si chiude;
  - la pagina 500 in un test si vede solo con `PROPAGATE_EXCEPTIONS = False`: con `TESTING` Flask rilancia l'errore invece di mostrare la pagina;
  - le pagine di errore usano le classi di `css/pages/auth.css` (riquadro, titolo e sottotitolo centrati), senza modificarlo.
- **Note per il contratto o per gli altri**: nessun cambiamento al contratto. **Christian**: le pagine 404 e 500 sono senza navbar, come deciso; se si vuole la navbar anche lì, serve uno script di pagina (come per `js/pages/auth.js`). **Giuseppe**: i gestori degli eventi che usano già `handler` non cambiano; il gestore generale di `errors.py` vale solo per quelli che non lo usano.
