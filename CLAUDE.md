# Cinquecento

Web-app per giocare online a Cinquecento (variante siciliana / Marianna) con carte siciliane: partite 1v1 e 2v2, matchmaking basato sul rating, registrazione/login e statistiche dell'account.

## Workflow Git (obbligatorio)

- `main`: non va mai modificato.
- `dev`: ramificato da `main`, remoto su GitHub.
- `christian`: ramificato da `dev`, è il branch di lavoro.
- Per **ogni nuova feature** si crea un nuovo branch da `christian` (es. `feature/game-engine`, `docs/...`, `fix/...`) e si lavora solo lì.
- L'utente testa manualmente. **Commit e merge in `christian` si fanno solo dopo la sua conferma esplicita.** Mai committare, fare merge o push senza conferma.
- Non fare mai merge in `dev` o `main` se non richiesto esplicitamente.

## Stack (vincolato)

Solo HTML, CSS, JavaScript (vanilla, ES modules, nessun framework né bundler), Python + Flask, MySQL.

- Real-time: Flask-SocketIO (un solo processo, modalità `threading` o `gevent`), lock per stanza.
- DB: MySQL (`utf8mb4`, InnoDB) tramite SQLAlchemy + PyMySQL.
- Auth: Flask-Login, password hashate.
- Rating: Glicko-2, separato per 1v1 e 2v2 (il pareggio vale 0.5).
- Server autoritativo: il client invia solo azioni; ogni giocatore riceve solo la propria vista (mai le carte altrui). Il server invia anche le mosse legali.

## Architettura modulare

- Flask app factory + blueprint per dominio (auth, profile, stats, lobby, game).
- Livelli: routes/sockets (sottili) → services → repositories → MySQL.
- `app/game/engine/` è **Python puro**: non importa mai Flask né il DB. Pattern `apply(state, action) -> state`, `legal_actions(state)`. Parametri della variante in `rules.py`.
- Frontend: un entry point JS per pagina (`static/js/pages/`), componenti riutilizzabili in `static/js/components/`, CSS diviso in `base/`, `components/`, `pages/`.

## Terminologia

Non si dice "dichiarare un matrimonio": si dice **"cantare 40"** (primo canto, fissa la briscola) e **"cantare 20"** (canti successivi). Usare questa terminologia nel codice, nei commenti, nella UI e nelle risposte (es. `sing_40`, `sing_20`, `can_sing`).

## Regole del gioco (variante siciliana)

- Mazzo di 40 carte siciliane. Valori (ordine di presa decrescente): Asso 11, Tre 10, Re 4, Cavallo 3, Fante 2, le altre carte 0.
- 1v1 oppure 2v2 (compagni uno di fronte all'altro, si gioca in senso antiorario). Nel 2v2 i punti vanno alla squadra.
- Si danno 5 carte a testa. Dopo ogni presa chi l'ha vinta pesca per primo, poi gli altri in ordine.
- **Non c'è obbligo di rispondere al seme.**
- All'inizio non c'è briscola. Chi ha Re e Cavallo dello stesso seme in mano può **cantare**:
  - il primo canto della mano è **40** e fissa la briscola;
  - i canti successivi sono **20** e non cambiano la briscola.
- Si canta solo nel proprio turno, **prima** di giocare la carta. Non serve aver già vinto una presa. Nello stesso turno si possono cantare più semi, e altri ancora nei turni successivi.
- Il canto va mostrato (sia il 40 che il 20). Serve avere Re e Cavallo in mano: niente coppia fatta col compagno.
- Se il Re o il Cavallo di un seme viene giocato, per quel seme non si può più cantare.
- Presa: se c'è briscola e ne è stata giocata almeno una, vince la briscola più alta. Altrimenti vince la carta più alta del seme giocato per primo ("carte franche"): le carte di altri semi non prendono mai.
- **A mazzo finito non cambia niente**: si continua a giocare le carte in mano con le stesse regole (con briscola se qualcuno ha cantato, altrimenti a carte franche). Si può cantare solo finché si hanno almeno 3 carte in mano: con 2 carte il canto non è più possibile.
- L'ultima presa non dà bonus.
- Il punteggio (carte prese + canti) si somma mano dopo mano. Il superamento dei 500 si controlla **solo a fine mano**. Vince chi supera 500. Se lo superano entrambi vince il punteggio più alto; a parità è **pareggio**.
