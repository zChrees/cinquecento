# Riepiloghi di Giuseppe

> **Questo file lo scrive solo Giuseppe** (Studente 1: motore e tempo reale). Lo leggono Christian e Antonio dopo il `git pull` di `dev`, per le novità utili al progetto e al loro lavoro; chi è di turno sui documenti condivisi (`SCALETTA.md`, `CLAUDE.md`, `DECISIONI.md`, `DA-DECIDERE.md`, scelto dal gruppo a fine giornata) li aggiorna da qui. Nessun altro lo modifica, nemmeno per correggere un errore: si segnala a Giuseppe.
>
> **Come si aggiorna** (regola in `CLAUDE.md`, "Consegna"): a fine punto, nel branch del punto (`feature/…`, `fix/…`), Giuseppe aggiunge il riepilogo **in cima** alla sezione "Riepiloghi", nello stesso commit del punto; così arriva in `dev` con il merge. Quando è di turno sui documenti, il riepilogo dell'aggiornamento va qui, nel branch `docs/…`. Il numero del commit non si scrive: lo si trova con `git log -- giuseppe.md`.

## Schema

```markdown
### P<numero> — <titolo> (<data>)

- **Branch**: feature/… (docs/… per un aggiornamento dei documenti condivisi)
- **File**: creati …; modificati … (se fuori elenco: perché e con l'ok di chi)
- **Controlli**: <N> PASS in tutto (<M> nuovi), `ruff check .` pulito
- **Decisioni prese**: … oppure "nessuna"
- **Domande nuove**: … oppure "nessuna"
- **Punti delicati**: …
- **Note per il contratto o per gli altri**: … oppure "nessuna"
```

## Riepiloghi

<!-- Il più recente in cima. I riepiloghi di P10–P13 li ha copiati Christian il 28/09/2026 dai messaggi di Giuseppe, senza cambiarli. -->

### Documenti: registrati P58, P31 e P32 (29/09/2026)

- **Branch**: docs/registra-p58-p31-p32
- **File**: modificati `SCALETTA.md` (tracker, sezione 3, "Da dove si parte", 9.2 di P32), `DECISIONI.md` (Sicurezza; Processo), `CLAUDE.md` (riga "Stato", punti delicati, numero dei controlli), questo file. `DA-DECIDERE.md` non cambia
- **Controlli**: nessuno (soli documenti); 1301 PASS e 2 FAIL su 1303 dall'ultimo giro di Giuseppe (P32)
- **Registrati**: di Giuseppe P58, P31 (con le tre correzioni) e P32. Di Christian e di Antonio niente di nuovo dopo l'ultimo aggiornamento (fermi a P42 e P27)
- **Decisioni registrate**: le quattro di P32 (limite di frequenza, CSP, "Esci" che scollega tutte le schede, cancellazione dell'account con coda e inviti) in Sicurezza; il server della suite `e2e` come processo a parte (P31) in Processo
- **Domande nuove**: nessuna
- **Punti delicati**: aggiunti in `CLAUDE.md` quelli di P31 (suite `e2e`, ore arrotondate da MySQL, `room.notify`) e di P32 (CSP, decoratore `handler`, `disconnect_user`); quello di P17 su coda e inviti ora dice che è risolto
- **Note per gli altri**: **Christian**: in "Da dove si parte" il tuo ordine resta quello del mio aggiornamento di ieri, con P58 già in `dev` (puoi adattare `game.js`) e le novità di P32 da tenere presenti in P33 (schede scollegate dopo "Esci", `too_fast` su ogni evento, CSP)

### P32 — Sicurezza di base (29/09/2026)

- **Branch**: feature/p32-sicurezza
- **File** (lista definitiva, da scrivere in 9.2 di `SCALETTA.md` da chi è di turno; confermata da Giuseppe prima di cominciare): modificati `config.py` (due chiavi: `EVENT_BURST`, `EVENT_RATE_PER_SECOND`), `app/__init__.py` (intestazioni di sicurezza), `app/realtime/events.py` (decoratore `handler`), `app/realtime/presence.py` (`tabs_of`, `disconnect_user`), `app/blueprints/auth/routes.py` (logout), `app/services/auth_service.py` (cancellazione dell'account, P17 di Antonio, con il suo permesso); creati `tests/api/test_sicurezza.py`, `tests/sockets/test_validazione_eventi.py` (i due di 9.2) e `tests/frontend/test_csp.py`; modificati, miei, `tests/sockets/conftest.py` (limite degli eventi alzato per la suite), `tests/sockets/test_connessione.py` (un test chiamava il decoratore fuori da una connessione), `tests/e2e/helpers.py` (`call_patiently`). **Non toccati**, anche se tra i probabili di 9.2: i gestori degli eventi (validavano già tutto: nessun `server_error` con nessun dato sbagliato, vedi sotto), `auth/forms.py`, `friends/routes.py`, i template di accesso
- **Controlli**: **1301 PASS e 2 FAIL** su 1303, in 8 suite (46 nuovi: 21 `api`, 21 `sockets`, 4 `frontend`), `ruff check .` pulito. I 2 FAIL sono quelli noti di `tests/frontend/test_pannello_amici.py` (P48, di Christian). La suite `e2e` ora dura circa 20 secondi (prima 12): con il limite vero le partite aspettano quando il server risponde `too_fast`
- **Cosa c'era già** [L], controllato all'inizio: CSRF su moduli e JSON (Flask-WTF su tutta l'app), cookie di sessione `HttpOnly` e `SameSite=Lax`, validazione di tipi e valori in tutti i gestori, errori imprevisti trasformati in `server_error` senza far cadere la stanza, niente `innerHTML` nel JS né `|safe` nei template, username solo con lettere, numeri e `_`, messaggio con tag mostrato come testo nella chat vera (già provato da `test_chat_vera.py`), nessun cookie "ricordami"
- **Decisioni prese** (scelte di Giuseppe sulle raccomandazioni di Claude, tutte opzione "a"):
  1. **limite di frequenza per scheda** su tutti gli eventi in tempo reale: fino a 20 eventi di fila, poi 10 al secondo (`EVENT_BURST`, `EVENT_RATE_PER_SECOND` in `config.py`); oltre, `too_fast` con `retry_after` in secondi interi (almeno 1). Vale per ogni scheda (connessione), non per utente: le altre schede non ne risentono. Si aggiunge ai limiti che c'erano (chat, frasi, login);
  2. **intestazioni di sicurezza con CSP** su ogni risposta: `Content-Security-Policy` (script e connessioni solo dal sito, stili anche da Google Fonts, font anche da `fonts.gstatic.com`, immagini dal sito e `data:`, niente oggetti né cornici, moduli solo verso il sito), `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: same-origin`;
  3. **cancellazione dell'account in coda o con un invito aperto**: non si rifiuta; prima di cancellare si chiudono le schede dell'utente, esce dalla coda e i suoi inviti si annullano (l'amico riceve `invite:update` `"cancelled"`). Con una partita in corso resta rifiutata (P17);
  4. **"Esci" scollega tutte le schede dell'utente** dal tempo reale (esce anche dalla coda e annulla gli inviti; al tavolo parte il minuto per rientrare, come una disconnessione). Il client Socket.IO non si ricollega da solo dopo uno scollegamento deciso dal server.
- **In più**: un evento da una scheda di un account che non esiste più (l'utente risulta anonimo) riceve `not_logged_in` invece di `server_error` (controllo nel decoratore comune).
- **Cosa provano i test**: intestazioni su pagine, file statici, 404 e JSON; CSP senza `unsafe-inline` né `unsafe-eval`; nessuno `<script>` senza `src` né `onclick=` nelle pagine; moduli (accesso, registrazione, Esci, cancellazione, avatar) e richieste JSON degli amici senza CSRF → 400; cookie di sessione; username con HTML rifiutato e mai rimandato senza escape; **ogni evento** (15) con 18 dati sbagliati diversi (non un oggetto, tipi sbagliati, numero di 31 cifre, testo di 100.000 caratteri) → errore del contratto, **mai `server_error`** [T]; connessione Socket.IO con `Origin` di un altro sito rifiutata, dallo stesso sito accettata (con il trasporto polling: col websocket il client aggiunge già un suo `Origin` e una seconda copia fa fallire per un altro motivo); limite di frequenza; "Esci" con due schede; cancellazione in coda e con un invito; account sparito; nel browser, home (con il websocket), tavolo di prova e registrazione **senza nessuna violazione della CSP**, e una violazione fatta apposta che si vede (così la lista vuota è credibile)
- **Domande nuove**: nessuna
- **Punti delicati** (per `CLAUDE.md`, da chi è di turno):
  - **CSP**: niente script né stili scritti dentro i template, niente attributi come `onclick=` o `style="..."` nell'HTML, e nel JS niente `setAttribute("style", …)` (va `element.style.x = …`, che è ammesso); una risorsa esterna nuova va aggiunta sia in `base.html` sia in `CSP_DIRECTIVES` di `app/__init__.py`. `tests/frontend/test_csp.py` apre le pagine e segnala ogni risorsa bloccata: una pagina nuova va aggiunta a `PAGES`;
  - **limite degli eventi**: la suite `sockets` lo alza nella fixture `server` (gioca alla massima velocità); la suite `e2e` usa quello vero e nelle partite aspetta `retry_after` (`Tab.call_patiently`); un test che manda molti eventi di fila dalla stessa scheda deve tenerne conto. Il limitatore sta in memoria per scheda e dimentica le schede ferme da più di un minuto;
  - **`disconnect_user`** va chiamata **mentre l'utente ha ancora il login** (prima di `logout_user` e prima di cancellare l'account): la pulizia allo scollegamento (`on_disconnect`) la fa solo per un utente riconosciuto;
  - un gestore di evento scritto senza `@handler` non ha né il controllo del login né il limite.
- **Note per il contratto o per gli altri**: nessun cambiamento al contratto (`too_fast` con `retry_after` e `not_logged_in` c'erano già). **Christian** (P33): dopo "Esci" le altre schede dello stesso utente vedono la connessione chiusa dal server e non si ricollegano: l'avviso di P33 dovrebbe dire di ricaricare la pagina; con clic velocissimi ogni evento può rispondere `too_fast` (il messaggio del contratto è "Troppo veloce: aspetta un momento."); se aggiungi una pagina o una risorsa esterna, vedi il punto delicato sulla CSP. **Chi è di turno sui documenti**: spuntare P32, scrivere in 9.2 la lista definitiva qui sopra, registrare le quattro decisioni in `DECISIONI.md` (Sicurezza) e i punti delicati in `CLAUDE.md`; il punto delicato "Impostazioni (P17)" su coda e inviti ora è risolto

### P31 — Test end-to-end, e tre correzioni trovate dai test (29/09/2026)

- **Branch**: feature/p31-e2e (due commit: prima le correzioni, poi i test)
- **File**: creati `tests/e2e/conftest.py`, `test_partita_1v1.py`, `test_partita_2v2.py`, `test_amici_inviti_chat.py`, `test_casi_limite.py` (i cinque dell'elenco) e, in più, `tests/e2e/helpers.py` (utenti, schede e aiuti per le partite, importati come `tests.e2e.helpers`, come `tests/browser.py`: importarli da `conftest.py` avrebbe caricato due volte il file). **Correzioni** (commit a parte, con l'ok di Giuseppe; la nota di P31 dice che sono punti nuovi): `app/realtime/room.py`, `app/repositories/chat_repo.py`, `app/repositories/friend_repo.py` (di Antonio, con il suo permesso)
- **Controlli**: **1255 PASS e 2 FAIL** su 1257, in 8 suite (12 nuovi nella suite nuova `e2e`, 5 giri di fila senza errori, circa 12 secondi), `ruff check .` pulito. I 2 FAIL sono quelli noti di `tests/frontend/test_pannello_amici.py` (P48, di Christian)
- **Decisioni prese** (scelta di Giuseppe sulla raccomandazione di Claude): **il server della suite `e2e` è un processo a parte**, avviato come lo avvia un utente (`python run.py` con `APP_ENV=testing`: porta 5099, `cinquecento_test`), e i test passano **solo dagli ingressi veri**: registrazione e login dai moduli con il CSRF, amici con le rotte HTTP e l'intestazione `X-CSRFToken`, coda, inviti, chat e partite con Socket.IO, statistiche con `GET /stats/me`. Non vedono la memoria del server; i tempi restano quelli veri (30 s di turno, 60 s per rientrare), quindi scadenze e abbandono per tempo restano provati dalla suite `sockets`
- **Cosa provano**:
  - partite intere dalla coda, 1v1 e 2v2 fino a 150, con utenti appena registrati: a ogni vista **nessuno vede carte in mano agli altri** (confrontando le viste dei giocatori tra loro; `last_hand` a parte, vedi P58), la home propone il rientro durante la partita e non più dopo, le statistiche contano la partita e il rating sale a chi vince;
  - amicizia (richiesta, avvisi, accettazione), presenza online / offline / in partita, chat (testo con `<script>` salvato così com'è, stesso `request_id` senza doppioni, 1 messaggio al secondo, non letti), blocco che chiude la chat;
  - invito 1v1 con partita intera che non conta per il rating; invito 2v2 con la coppia in coda e due singoli, poi abbandono: perde la squadra, il rating scende solo a chi è uscito (D13, P30);
  - casi limite: doppio clic (una sola carta), fuori turno e dati sbagliati (la partita continua), stesso utente in due schede al tavolo (D14) e in coda (`busy`, stesso `request_id`, "Annulla" vale per tutte e due), disconnessione e rientro con la stessa mano, collegamento senza login rifiutato
- **Bug trovati e corretti** [T] (ognuno riprodotto da un test `e2e` prima della correzione):
  1. **amici "in partita" per sempre** (P47): a fine partita gli amici non ricevevano `friends:presence` "online". `room.notify` faceva `tuple(user_ids)` dentro il ciclo e `_save()` gli passa un generatore: lo leggeva solo il primo ascoltatore (la home), il secondo (gli amici) riceveva un elenco vuoto. Ora la tupla si fa prima del ciclo;
  2. **ora dei messaggi di chat diversa di un millesimo** (P48) tra la risposta di `chat:send` e `chat:history`: Python tronca i millesimi, MySQL li arrotonda salvando in `DATETIME(3)`. Ora `chat_repo.utc_now()` restituisce l'ora già ai millesimi;
  3. **ora delle richieste di amicizia diversa fino a un secondo** (P45) tra la risposta di `POST /friends/requests` e `GET /friends/`: la colonna è `DATETIME` senza decimali e MySQL arrotonda (le 09.554 diventavano le 10.000). Ora `friend_repo.utc_now()` restituisce l'ora già al secondo (vale anche per risposte e blocchi)
- **Domande nuove**: nessuna
- **Punti delicati**:
  - con MySQL un'ora con più decimali della colonna **si arrotonda**, non si tronca: chi salva un'ora e la rimanda subito alla pagina deve prima tagliarla alla precisione della colonna (come fanno ora `chat_repo` e `friend_repo`);
  - in `helpers.py`, `Tab.wait_for` trova il **primo** evento adatto mai arrivato: per aspettare qualcosa che succede dopo un certo punto si usa `since=tab.mark()` (esempio: "home senza rientro a fine partita" trovava lo stato iniziale, di prima della partita; e prima che tutti siano seduti un giocatore risulta scollegato senza conto alla rovescia, com'è giusto per P25);
  - ogni test registra utenti nuovi (`Utente01`, `Utente02`, …): code, rating e amicizie di un test non toccano gli altri; se un test lascia un utente in coda, la chiusura delle schede lo fa uscire;
  - nella chat il limite di 1 al secondo si controlla prima del blocco: subito dopo un messaggio, `chat:send` verso chi ti ha bloccato risponde `too_fast`, non `blocked` (comportamento di P48, lasciato com'è)
- **Note per il contratto o per gli altri**: nessun cambiamento al contratto. **Chi è di turno sui documenti**: spuntare P31 e registrare le tre correzioni; la suite `e2e` c'era già nell'elenco del runner (`SUITES`); il numero di controlli è 1257; punto delicato sulle ore arrotondate da MySQL per `CLAUDE.md`. **Christian**: la suite `e2e` usa anche la porta 5099, come le altre: chiudi il server prima di un giro completo

### P58 — Ultima presa della mano nella vista (28/09/2026)

- **Branch**: feature/p58-ultima-presa-mano
- **File**: modificati `app/game/engine/state.py` (campo `last_trick` in `HandResult`), `game.py` (`hand_result` lo riempie), `views.py` (`last_hand.last_trick`, funzione `_last_trick` usata anche per `last_trick`), `docs/CONTRATTO-SOCKET.md` (3.3, riga di `last_hand`), `app/static/dev/vista_1v1.json` (esempio e `_nota`; `vista_2v2.json` ha `last_hand` null e non cambia), `tests/engine/test_partita.py`, `tests/engine/test_viste.py`. Nessun file fuori elenco
- **Controlli**: **1243 PASS e 2 FAIL** su 1245, in 7 suite (10 nuovi nella suite `engine`), `ruff check .` pulito. I 2 FAIL sono quelli già noti di `tests/frontend/test_pannello_amici.py` (P48, di Christian)
- **Decisioni prese**: nessuna nuova (la modifica al contratto era approvata dai tre). Forma: `last_hand.last_trick` = `{"winner_seat", "cards": [{"seat", "card"}]}`, identica a `last_trick`; c'è sempre quando `last_hand` non è null
- **Domande nuove**: nessuna
- **Punti delicati**:
  - `HandResult.last_trick` è obbligatorio: una mano finita ha sempre almeno una presa chiusa, quindi `hand_result` non controlla più se `last_trick` è `None`;
  - il test "la vista non mostra mai carte nascoste" ora controlla `last_hand` **a parte**: il mazzo si rimescola a ogni mano, quindi una carta dell'ultima presa della mano prima può essere adesso in mano a un altro. Non è una fuga (carta già giocata e vista da tutti), e il test controlla che in `last_hand` ci siano esattamente le carte di quella presa e nient'altro;
  - test nuovo: in partite intere a caso (5 semi, 1v1 e 2v2) la presa di `last_hand` è quella in corso più la carta che ha chiuso la mano, la vince chi dice `trick_winner` con la briscola di quella mano, e la mano nuova parte con `last_trick` a `null`.
- **Note per il contratto o per gli altri**:
  - **Christian**: ora `game.js` può mostrare le carte dell'ultima presa prima del riepilogo: quando `hand_number` sale, le carte sono in `next.last_hand.last_trick` (stessa forma di `last_trick`, quindi `data-last-trick` può riusare lo stesso disegno); a fine partita `last_trick` della mano finita c'è già, ed è uguale a `last_hand.last_trick`. `test_momenti_tavolo.py` costruisce `last_hand` senza `last_trick`: finché la pagina non lo legge non si rompe;
  - **chi è di turno sui documenti**: spuntare P58.

### Documenti: registrati P28–P30, P35, P42, P44, P47, P48, P56, P57 e metà di P38 (28/09/2026)

- **Branch**: docs/registra-p28-p57
- **File**: modificati `SCALETTA.md` (tracker, sezione 4 con P58–P60, sezione 3, sezione 9 e 9.2), `DECISIONI.md` (Dati, Interfaccia, Gioco, Processo), `DA-DECIDERE.md`, `CLAUDE.md` (riga "Stato", punti delicati, numero dei controlli), questo file
- **Controlli**: nessuno (soli documenti); 1233 PASS e 2 FAIL su 1235 dall'ultimo giro di Giuseppe (P38)
- **Registrati**: di Christian, P57, P30 (con la correzione del test della home di P28), P56, la correzione del test della home di P44, P35, la correzione dei test della home di P47, P42; di Giuseppe, P28, P29 (con la correzione di `tests/browser.py`), P44, P47, P48 e la parte di P38 nel repository (**P38 non spuntato**). Di Antonio niente di nuovo dopo P27
- **Decisioni prese**:
  - **P38 e P39 passano a Giuseppe**, perché Antonio non può lavorare al progetto per un bel po' (scelta di Giuseppe, di turno); Antonio resta nella sezione 9 con i punti che ha fatto;
  - **punti nuovi**: **P58** (ultima presa della mano nella vista, Giuseppe: approvata dai tre), **P59** (2v2 con più amici invitati, Giuseppe: approvata dai tre, file in 9.2), **P60** (togliere le viste finte `?demo=` prima della consegna, Christian, prima di P36: proposta di Christian, accettata da Giuseppe);
  - registrate in `DECISIONI.md` le decisioni dei riepiloghi: D17 e D19 chiuse; coda con accettazione reciproca; invito ricevuto, inviti che dopo "Accetta" non scadono; chat con chi ti ha bloccato; momenti del tavolo; frasi nella pagina; carte vere; logo e icona; statistiche del compagno di chi abbandona; backup pianificato; 2v2 con più amici (cambia D27, vale da P59); le decisioni vecchie che cambiano hanno la nota "Aggiornata"
- **Domande nuove** (in `DA-DECIDERE.md`): **D41** `cannot_write` in `chat:history` (contratto 5.4, da approvare in tre); **D42** conversazioni con gli ex amici; **D20** completata con "da quale branch si installa la demo"
- **Punti delicati**: aggiunti in `CLAUDE.md` quelli di coda, presenza, inviti, chat, momenti del tavolo, frasi nella pagina, statistiche, carte e icona, demo, browser dei test. **Trovato leggendo il codice** [L]: la cancellazione dell'account (`auth_service.py`) controlla solo la partita in corso, non la coda né un invito aperto (il punto delicato di P17 lo chiedeva a P28 e P47): aggiunto ai file probabili di P32
- **Note per gli altri**:
  - **Christian**: i due test di `tests/frontend/test_pannello_amici.py` che non passano dopo P48 (riepilogo di P48 qui sotto) sono il tuo primo passo in "Da dove si parte". Il contratto 5.3 per il 2v2 con più amici lo aggiorna chi fa P59 (io), con i dettagli concordati all'inizio del punto; `cannot_write` (5.4) aspetta D41
  - **Antonio**: P38 e P39 sono passati a me; se torni prima della fine, dimmelo
- **Da revisionare, Christian** (scelte fatte da me mentre ero di turno, che toccano anche te: se qualcosa non va, scrivilo nel tuo riepilogo e lo correggo, o lo corregge chi è di turno):
  - `SCALETTA.md`, tracker: le note dei tuoi punti P30, P35, P42, P56, P57 (commit, test, file fuori elenco) le ho ricavate dai tuoi riepiloghi;
  - `SCALETTA.md`, sezione 4: **P60** è scritto da me sulla tua proposta di P57 (cosa fare, "Fatto quando", dipendenze P21, P22, P56, P57, prima di P36; P36 ora dipende anche da P60); in 9.2 i file di P60 sono una mia ipotesi (`game.js`, `home.js`, i quattro test che usano `?demo=`; forse `blueprints/game/routes.py`, `main/routes.py`, `app/static/dev/`): all'inizio del punto scrivi tu la lista definitiva;
  - `SCALETTA.md`, sezione 3: le righe di `ModeModal.js` (ora "P22 → P59": P28 e P47 non l'hanno toccato), `game.js` (P21 → P24 → P25 → P57 → P56 → P60), `base.html` (P19 → P40 → P46 → P42 → P33), e le righe nuove di `core/events.js`, `friend_service.py`, `tests/browser.py`;
  - `SCALETTA.md`, sezione 9: nel tuo elenco ho aggiunto P60; in "Da dove si parte" il tuo ordine è: i 2 test del pannello amici, `game.js` per P58, P33, P34, P43, P53, P60, P36 (è una proposta mia: cambialo se preferisci); due controlli di parallelismo nuovi: P31/P32 con P33, P59 con P33 e P60 (P59 può toccare `ModeModal.js`, che è tuo);
  - `DECISIONI.md`, Interfaccia: le decisioni tue di P57, P56, P35 e P42 sono riscritte dai tuoi riepiloghi, con "Motivo: scelte di Christian"; la decisione di P30 (compagno di chi abbandona) è in Dati; ho aggiunto "Aggiornata" alle decisioni di P22 ("Home con dati finti": ora quasi tutto è vero), P46 (chat vera da P48) e "Carte" del 26/09;
  - `DA-DECIDERE.md`: tolta D19 (chiusa da te in P35); **D42** (conversazioni con gli ex amici) dice che, se serve, è un punto nuovo tuo;
  - `CLAUDE.md`: punti delicati nuovi di P57, P56, P30 e P35/P42 ricavati dai tuoi riepiloghi.

### P38 — Installazione demo separata e backup pianificato: la parte nel repository (28/09/2026)

Punto di Antonio, fatto da Giuseppe con il suo permesso. **Fatto a metà, per scelta di Giuseppe**: c'è la parte nel repository (guida e script); l'installazione sul PC della demo aspetta D20. P38 dipendeva da P37 solo per l'ordine (la demo si prepara alla fine): l'unica dipendenza tecnica, P18 (backup), è in `dev`.

- **Branch**: feature/p38-demo
- **File**: creati `docs/DEMO.md`, `scripts/pianifica_backup.ps1` (i due file di 9.2: "sicuro" e "probabile"), `tests/db/test_demo.py`
- **Controlli**: **1233 PASS e 2 FAIL** su 1235, in 7 suite (5 nuovi nella suite `db`), `ruff check .` pulito. I 2 FAIL sono gli stessi di P48 (test di Christian del pannello amici)
- **Decisioni prese** (scelte di Giuseppe):
  - **backup pianificato con uno script** (`scripts/pianifica_backup.ps1`, la scelta che 9.2 lasciava all'inizio del punto): crea l'attività di Windows "Cinquecento - backup della demo", ogni giorno alle 3:00 (`-Ora` per cambiarla), che lancia `python scripts\backup.py` e aggiunge il risultato a `logs\backup.log`; se il PC è spento all'ora giusta parte appena si riaccende; si rifiuta senza il file `PRODUZIONE`; non serve essere amministratore;
  - la guida `docs/DEMO.md` vale anche per **la parte scritta di P39** (rete, firewall solo per le reti private, lista di controllo del giorno della demo); la **prova generale** di P39 (tre telefoni e un PC, un 2v2 completo) si fa l'ultimo giorno, sul codice finale.
- **Domande nuove** (per chi è di turno sui documenti: vanno in `DA-DECIDERE.md`, D20):
  - **quale PC ospita la demo**;
  - **come si collegano gli altri**: stessa rete Wi-Fi (consigliato) o un tunnel come ngrok (il passo 11 di `DEMO.md` vale solo per la stessa rete);
  - **da quale branch si installa la demo**: `dev` finché `main` non viene aggiornato (portare `dev` in `main` lo decide il gruppo).
  In `DEMO.md` ci sono i segnaposti da riempire.
- **Cosa resta di P38** (sul PC della demo, dopo D20): seguire `DEMO.md` dal passo 1 al 9 e i tre controlli [T] del "Fatto quando": il runner si rifiuta nella cartella della demo, il backup pianificato produce un file, il ripristino di prova su `cinquecento_test` funziona. **Il punto non va spuntato finché non sono fatti.**
- **Punti delicati**:
  - `pianifica_backup.ps1` deve restare **solo ASCII**: Windows PowerShell 5.1 legge un `.ps1` senza BOM con la codifica di sistema e le lettere accentate diventerebbero sbagliate (c'è un test); per questo nei commenti ci sono "attivita'" e "piu'";
  - la cartella della demo va **fuori da OneDrive** (un file bloccato dalla sincronizzazione può fermare server o backup) e ha i backup in `backups\`: vanno copiati anche fuori dal PC;
  - l'utente MySQL `cinquecento` scrive solo in `cinquecento_dev` e `cinquecento_test`: per la demo serve il `GRANT` su `cinquecento` (passo 5 di `DEMO.md`, come root).
- **Note per gli altri**: **Christian**: le tre domande di D20 qui sopra, per `DA-DECIDERE.md`; in `SCALETTA.md` P38 è "fatto a metà" (non spuntarlo) e il file probabile di 9.2 (`scripts/pianifica_backup.ps1`) ora è deciso. **Antonio**: P38 è quasi tutto scritto; resta l'installazione sul PC della demo, quando il gruppo decide D20.

### P48 — Chat tra amici (28/09/2026)

Punto di Antonio, fatto da Giuseppe con il suo permesso. Prima di cominciare: nessun branch di P48 su GitHub.

- **Branch**: feature/p48-chat
- **File**: creati `app/services/chat_service.py`, `app/repositories/chat_repo.py`, `tests/sockets/test_chat.py`; modificati `app/sockets/chat_events.py`, `app/static/js/components/ChatWindow.js`. **Fuori elenco, con l'ok di Giuseppe**: `app/static/js/components/FriendsPanel.js` (la chat vera al posto di quella di prova), `app/static/js/core/events.js` (i nomi `CHAT_*`); creato `tests/frontend/test_chat_vera.py`
- **Controlli**: **1228 PASS e 2 FAIL** su 1230, in 7 suite, dopo il rebase su P35, P42 e sulla correzione di Christian dei test della home di P47. 25 nuovi nella suite `sockets` (3 volte senza errori), 3 nella suite `frontend` (3 volte), `ruff check .` pulito. I **2 FAIL attesi** sono test di Christian del pannello amici (vedi "Note per gli altri")
- **Decisioni prese** (scelte di Giuseppe):
  - **chi è stato bloccato lo vede nella chat**: "Bloccato: non potete più scrivervi." e il campo chiuso (vale per tutti e due); fuori dalla chat non riceve nessun avviso (P47);
  - **aggiunta al contratto 5.4, da approvare in tre**: la risposta di `chat:history` ha anche **`cannot_write`**: `null` se si può scrivere, altrimenti `"not_friends"` (amicizia finita) o `"blocked"` (un blocco in una delle due direzioni). Senza, la pagina sapeva solo `can_write: false` e non poteva dire "bloccato". È un campo in più: chi non lo legge non si rompe.
- **Scelte tecniche**:
  - `chat:send`: testo non vuoto né fatto di spazi, al massimo 1000 caratteri, salvato così com'è (`invalid_data` altrimenti); al massimo 1 messaggio al secondo per utente (`too_fast` con `retry_after` in secondi interi; un messaggio rifiutato non conta); `request_id` con `RecentRequests` (lo stesso tentativo non salva e non recapita due volte); a sé stessi → `invalid_data`; utente inesistente → `not_found`;
  - amicizia e blocchi si controllano **nella stessa transazione della scrittura**, dopo aver bloccato le righe dei due utenti, in READ COMMITTED (come `friend_service`, P45): un blocco appena salvato da un'altra scheda si vede;
  - `chat:message` va al destinatario (tutte le schede) e alle **altre** schede di chi scrive; quella che ha scritto lo ha nella risposta;
  - `chat:history`: al massimo 50 messaggi dal più vecchio al più nuovo, `has_more`, `before_id` per i precedenti; con `before_id` null (apertura della chat) segna come letti i messaggi ricevuti; `chat:read` segna quelli arrivati con la chat aperta;
  - pagina: "Messaggi precedenti" in cima alla chat quando `has_more`; un messaggio arrivato con la chat aperta si aggiunge e si segna letto, altrimenti si aggiorna il contatore dei non letti; se `chat:send` risponde `blocked` o `not_friends` la scrittura si chiude con il motivo; un messaggio già mostrato (stesso `id`) non si ripete.
- **Domande nuove**:
  - **conversazioni con ex amici**: il contratto dice che dopo la fine dell'amicizia o un blocco la conversazione "resta visibile", ma il pannello mostra la chat solo dalla lista degli amici: un ex amico non c'è più, quindi la conversazione si vede solo se era già aperta. Se serve, va aggiunto nel pannello un posto per le conversazioni con chi non è più amico (punto nuovo, di Christian).
- **Punti delicati**:
  - il limite di frequenza è in memoria (`chat_service.rate_limit`) e si ricorda l'ultimo messaggio di ogni utente anche tra un test e l'altro: i test che lo provano lo azzerano (`give_back`);
  - **la suite `frontend` non prepara il database**: i test del browser che lo usano lo trovavano pronto solo perché la suite `sockets` gira prima. `test_chat_vera.py` lo svuota e lo ricrea da sé (come `tests/sockets/conftest.py`), così funziona anche lanciato da solo.
- **Note per il contratto o per gli altri**:
  - **tutti**: `cannot_write` in `chat:history` (sopra) va scritto nel contratto 5.4 da chi è di turno, se siete d'accordo;
  - **Antonio**: P48 è fatto. Ti restano P38 e P39 (aspettano P37 di Christian);
  - **Christian**: con la chat vera due tuoi test di `tests/frontend/test_pannello_amici.py` non passano più. `test_chat_di_prova_testo_come_testo` prova la "Chat di prova" con i dati finti, che non c'è più; `test_indietro_ed_esc_chiudono` apre la chat con l'amico finto 44, che non esiste nel database dei test, quindi la chat non si apre (il server risponde "Questo utente non esiste."). Il flusso vero è provato da `tests/sockets/test_chat.py` e nel browser da `tests/frontend/test_chat_vera.py` (con utenti veri nel database dei test: puoi usare lo stesso modo per aprire la chat nel test di "indietro" ed Esc). Il file è tuo: decidi tu se riscriverli o toglierli. Nel template resta `data-chat-demo-url`, che il pannello non usa più: si può togliere quando sistemi i test.

### P47 — Amici online e inviti a partita (28/09/2026)

- **Branch**: feature/p47-inviti
- **File**: creati `app/realtime/invites.py`, `tests/sockets/test_inviti.py`; modificati `app/sockets/friends_events.py`, `app/static/js/components/FriendsPanel.js`. **Non toccato**, anche se nell'elenco: `ModeModal.js` (filtrava già gli amici "online" e annullava l'invito alla chiusura). **Fuori elenco, con l'ok di Giuseppe**: creati `app/static/js/components/InviteDialog.js` (l'invito ricevuto, vedi sotto) e `tests/frontend/test_invito_ricevuto.py`; modificati `app/static/js/pages/home.js`, `app/realtime/room.py` e `app/realtime/room_manager.py` (`start_listeners`), `app/sockets/connection_events.py`, `app/sockets/home_events.py`, `app/static/js/core/events.js` (miei); `app/services/friend_service.py` e `tests/api/test_amicizie.py` (di Antonio, con il suo permesso: vedi sotto)
- **Controlli**: **1195 PASS e 2 FAIL** su 1197, in 7 suite, dopo il rebase su P56 e sulla correzione di Christian del test di P44. 27 nuovi nella suite `sockets` (rilanciata 3 volte senza errori) e 4 nella suite `frontend` (3 volte), `ruff check .` pulito. **2 FAIL attesi** in `tests/api/test_pagina_home.py` (di Christian): vedi "Note per gli altri"
- **Decisioni prese** (scelte di Giuseppe):
  - **l'invito ricevuto si vede solo nella home**, in una finestra nuova (`InviteDialog.js`, con lo stile di `modal.css`, niente CSS nuovo): "*Nome* ti invita a giocare contro di te nel 1v1 / in squadra con te nel 2v2, a N punti", conto alla rovescia, "Rifiuta" e "Accetta"; dopo "Accetta": "Hai accettato: aspettiamo che *Nome* avvii la partita…" (e "Esci" per rifiutare); X ed Esc valgono "Rifiuta"; gli stati finali mostrano il motivo e la finestra si chiude dopo 4 secondi (o con la X);
  - **dopo "Accetta" l'invito non scade più**: resta aperto finché chi ha invitato preme "Gioca", lo annulla, l'invitato rifiuta o uno dei due chiude tutte le schede; l'invitato può rifiutare anche dopo aver accettato;
  - **chi viene bloccato non lo sa**: riceve solo `friends:changed` `"friend_removed"` (la sua lista si aggiorna in silenzio); `"blocked"` va solo alle schede di chi blocca. **Per la chat (P48, Antonio)**: quando chi è stato bloccato apre la chat con chi l'ha bloccato deve vedere che è bloccato e non poter scrivere (scelta di Giuseppe).
  - **un amico alla volta** (D27, contratto 5.3): l'idea di invitare più amici (vedi la domanda nel riepilogo di P28) resta aperta; se il gruppo la approva, si aggiunge dopo.
- **Scelte tecniche**:
  - `invites.py`: inviti in memoria sotto un lock; stati `pending` → `accepted` | `declined` | `expired` | `cancelled`, `accepted` → `started` | `declined` | `cancelled`; scadenza con un timer di `INVITE_SECONDS` (60, `config.py`) solo per `pending`; `invite_id` casuale (`inv_…`); ogni cambio chiama `on_change` (→ `invite:update` a tutti e due);
  - `invite:send`: solo a un amico (`not_friends`), collegato (`offline`), né lui né chi invita in partita, in coda o con un altro invito aperto, mandato o ricevuto (`busy`); `request_id` con `RecentRequests`; se stessi → `invalid_data`;
  - `invite:start` (sotto il lock degli inviti, così un doppio clic non avvia due partite): 1v1 → `create_room(..., rated=False)` e `game:start` a tutti e due; 2v2 → `matchmaker.join_pair` e la risposta è lo stato della coda; poi `started`. Prima di "accepted" → `not_allowed`; solo chi ha invitato (`not_found` per gli altri);
  - `friends:presence` agli amici collegati quando uno entra online, esce (`connection_events`), comincia o finisce una partita (`start_listeners` e `finish_listeners`, in un thread con l'app, perché serve il database); un errore nell'avviso va nel log e non ferma il collegamento;
  - `friends:changed` da `friend_service.py` dopo ogni cambiamento **vero** (le funzioni interne ora dicono se hanno cambiato qualcosa): richiesta → `request_received`; accettata → `request_accepted`; rifiutata o **annullata da chi l'aveva mandata** → `request_declined` (il contratto non ha un motivo per l'annullamento: la pagina ricarica comunque la lista); amicizia tolta → `friend_removed`; blocco come sopra. Togliere l'amicizia o bloccare annulla l'invito aperto tra i due;
  - `friend_service.presence` ora legge "online" da `presence.py` (P44) invece dei canali di Socket.IO: un solo elenco di chi è online;
  - pagina: la lista degli amici da invitare viene da `GET /friends/` e si rilegge con `friends:presence` e `friends:changed` (anche nel pannello amici); se la carta si chiude mentre `invite:send` aspetta la risposta, l'invito si annulla appena arriva.
- **Domande nuove**: nessuna
- **Punti delicati**:
  - `start_listeners` li chiama `create_room` **dopo** aver registrato la stanza (se li chiamasse `Room.start`, "in partita" non la troverebbe ancora); le funzioni ricevono `(user_id, app)`: con `app` None (stanza creata fuori da Flask, nei test) gli avvisi che leggono il database non partono;
  - `invites.lock` è rientrante e resta preso mentre `invite:start` crea la partita o mette la coppia in coda: nessun altro lock prende quello degli inviti, quindi non ci sono blocchi a vicenda;
  - `test_inviti.py` crea le amicizie con `friend_service` dentro l'app dei test e le toglie alla fine.
- **Note per il contratto o per gli altri**: nessun cambiamento al contratto.
  - **Antonio**: ho toccato `friend_service.py` (avvisi `friends:changed`, "online" da `presence.py`, inviti annullati con amicizia tolta o blocco) e una riga di `tests/api/test_amicizie.py` (`test_presenza_degli_amici` sostituiva `_is_connected`, che non c'è più: ora sostituisce `online_users.is_online`). Per **P48**: la decisione sulla chat con chi ti ha bloccato qui sopra.
  - **Christian**: con P47 la home usa gli amici e gli inviti veri, quindi due tuoi test di `tests/api/test_pagina_home.py` provano un comportamento che non c'è più: `test_invito_finto_poi_gioca_e_coda_con_il_compagno` (l'amico finto che accetta dopo 2 secondi) e `test_con_un_amico_1v1_messaggio_di_prova` (il messaggio "Prova: qui comincerebbe la partita…"). Il flusso vero è provato da `tests/sockets/test_inviti.py` (server e client simulati) e l'invito ricevuto da `tests/frontend/test_invito_ricevuto.py` (nel browser). **Proposta**: toglierli, oppure riscriverli sul flusso vero (per esempio facendo arrivare `invite:update` dal server come fa `test_invito_ricevuto.py`). Il file è tuo: decidi tu. Anche `DECISIONI.md` (P22, "Home con dati finti") va aggiornata da chi è di turno: amici e inviti non sono più finti.

### P44 — Home con dati reali (28/09/2026)

- **Branch**: feature/p44-home-reale
- **File**: creati `app/realtime/presence.py`, `app/sockets/home_events.py`, `tests/sockets/test_home_stato.py`; modificati `app/sockets/__init__.py`, `app/sockets/connection_events.py`, `app/static/js/pages/home.js`. **Fuori elenco, miei, con l'ok di Giuseppe**: `app/realtime/room.py` (P24–P26: `finish_listeners`, chiamati a fine partita, vedi sotto) e `app/static/js/core/events.js` (P23: il nome `HOME_STATUS`)
- **Controlli**: 1153 PASS e **1 FAIL** su 1154, in 7 suite (8 nuovi nella suite `sockets`, rilanciata 3 volte di fila senza errori), `ruff check .` pulito. Il FAIL è `tests/api/test_pagina_home.py::test_avviso_di_rientro_solo_se_previsto` (P22, di Christian): vedi "Note per gli altri"
- **Decisioni prese** (scelte di Giuseppe sulle raccomandazioni di Claude):
  - **a fine partita la home lo sa subito**: i giocatori ricevono `home:status` con `resume: null` e l'avviso "rientra" sparisce anche nelle altre schede (contratto 5.1, "a ogni cambiamento");
  - **dati veri sempre nella home** (anche in sviluppo e nei test): `home:status` vero prende il posto di quello finto; resta finto solo con **`?demo=rientro`**, per provare l'avviso senza una partita vera. Senza login la pagina non si collega e restano i dati finti (in sviluppo) o niente (demo vera).
- **Scelte tecniche**:
  - `presence.py`: utente → schede collegate, in memoria sotto un lock; `add` e `remove` dicono se l'utente è appena entrato o uscito; due schede contano una volta;
  - `home:status` a ogni scheda appena collegata; a **tutti** gli utenti collegati quando uno entra online (prima scheda) o esce (ultima scheda); ai giocatori di una partita appena finita (per punteggio o abbandono);
  - `resume` = `{game_id, url, mode, target_score}` da `find_room_of_user`, oppure `null`;
  - la fine partita arriva da `room.py`: `finish_listeners` (lista di funzioni) chiamati una volta sola, insieme al salvataggio, **in un thread a parte, fuori dal lock della stanza**: lo stato della home guarda anche le altre stanze, e farlo sotto il lock di una stanza potrebbe bloccarne due a vicenda. `home_events.register` si aggiunge alla lista una volta sola;
  - l'uscita dalla coda con l'ultima scheda (P28) ora usa `presence` invece di contare le schede nel canale `user:<id>`; in `on_disconnect` la scheda si toglie da `presence` per prima cosa, così un errore dopo non lascia l'utente "online".
- **Domande nuove**: nessuna
- **Punti delicati**:
  - `online_count` viene da `presence`, non dai canali di Socket.IO: ogni scheda collegata deve passare da `connection_events` (è così per tutte le pagine);
  - `friend_service.presence` (P45) conta ancora gli utenti online dai canali `user:<id>`: in P47 lo porto su `presence.is_online`, così c'è un solo elenco;
  - `test_home_stato.py` aspetta che non ci sia nessuna scheda collegata prima di ogni prova (quelle delle prove precedenti si chiudono in modo asincrono).
- **Note per il contratto o per gli altri**: nessun cambiamento al contratto.
  - **Christian**: come con P28, un tuo test aspetta i dati finti. In `test_avviso_di_rientro_solo_se_previsto` (`tests/api/test_pagina_home.py`, riga 391) il numero degli online ora è quello vero, **"1"** (solo l'utente del test è collegato), non "24". Siccome all'apertura la pagina può mostrare per un attimo il "24" finto prima che arrivi quello vero, conviene **aspettare** il numero vero invece di leggerlo subito: per esempio `logged_in.wait_js("document.querySelector('[data-online-count]').textContent === '1'", "numero vero degli online")`. Con questa riga il test passa tutto, compreso l'avviso con `?demo=rientro` (provato con una copia temporanea, poi cancellata). Non ho toccato il tuo file: lo correggi tu, come per P28?
  - **Christian e Antonio, proposta sull'ultima presa di ogni mano** (la domanda di Christian in P57): aggiungere a `last_hand` della vista il campo **`last_trick`**, con la stessa forma di `last_trick` della mano in corso (le carte dell'ultima presa e chi l'ha presa), in `app/game/engine/views.py` e nel contratto 3.3. Serve anche una piccola modifica al motore: oggi il risultato della mano (`HandResult`, in `state.py`) tiene solo i punti, quindi gli si aggiunge l'ultima presa, riempita da `hand_result` quando la mano si chiude (`game.py`). La pagina (P57) mostra quelle carte prima del riepilogo di fine mano. Cambia il contratto, quindi serve l'ok di tutti e tre: se siete d'accordo lo faccio io come lotto piccolo (motore, vista, contratto, test), poi Christian adatta `game.js`.

### P29 — Matchmaking 2v2 (28/09/2026)

Punto di Antonio, fatto da Giuseppe con il suo permesso, subito dopo P28.

- **Branch**: feature/p29-matchmaking-2v2
- **File**: creato `tests/sockets/test_matchmaking_2v2.py`; modificati `app/realtime/matchmaking.py`, `app/sockets/lobby_events.py`, `app/static/js/pages/home.js`. **Correzione del browser dei test** (commit a parte, con l'ok di Giuseppe): modificato `tests/browser.py` (di Christian, P46), creato `tests/frontend/test_avvio_browser.py`. **Fuori elenco, miei**: `tests/sockets/test_matchmaking_1v1.py` (P28: le partite trovate ora sono oggetti `Match`, tolto il controllo "2v2 non attivo") e `tests/sockets/conftest.py` (il fixture `server` restituisce anche `app`, per chiamare `matchmaker.join_pair` dai test)
- **Controlli**: **1146 PASS** in 7 suite, tutto PASS, dopo il rebase su P30 e sulla correzione di Christian del test della home di P28 (23 nuovi nella suite `sockets`, rilanciata 3 volte di fila senza errori, e 5 nella suite `frontend` per la correzione del browser dei test), `ruff check .` pulito
- **Decisioni prese**: **coda 2v2 di singoli** (chiude D17, scelta di Giuseppe sulla raccomandazione di Claude): le squadre si formano in modo che le medie delle due squadre siano il più vicine possibile.
- **Scelte tecniche**:
  - in coda ci sono **voci**: un singolo, oppure una **coppia già formata**, che gioca sempre nella stessa squadra, contro due singoli o contro un'altra coppia; il rating della coppia è la media dei due (vale per l'intervallo di `queue:status`, uguale per i due);
  - la regola "si accettano a vicenda" di P28 vale per **ogni coppia di voci** della partita: con quattro singoli servono tutti e quattro nell'intervallo di ognuno;
  - si serve prima chi aspetta da più tempo; tra le partite possibili si sceglie quella con i rating più vicini (differenza tra il più alto e il più basso), poi quella con le squadre più bilanciate, poi chi aspetta da più tempo; per ogni voce si guardano solo le 8 più vicine di rating (`CANDIDATES`), così il calcolo resta leggero (provato con 40 in coda);
  - posti: squadre e posti dentro la squadra tirati a sorte; i posti 0 e 2 sono una squadra (contratto 3.1); `rated=True` sempre (anche la coppia con l'amico, D36);
  - **`matchmaker.join_pair(app, utente, compagno, target_score, sid=None)`** fa entrare la coppia nella coda 2v2 e restituisce lo stato di `utente`; il compagno riceve `queue:status` con `partner`. Rifiuta con `busy` se uno dei due è già in coda o in partita, con `invalid_data` la coppia con sé stessi. **Non è collegata a nessun evento**: la chiamerà `invite:start` di P47;
  - se esce uno della coppia (Annulla o ultima scheda chiusa) esce tutta la coppia: lui riceve `queue:left` `"cancelled"`, il compagno `"partner_left"`;
  - pagina: "Gioca" nella Partita Veloce 2v2 usa la coda vera; con `"partner_left"` compare "Il tuo compagno è uscito dalla coda."; il 2v2 con un amico resta con i dati finti fino a P47.
- **Domande nuove**: nessuna (quella sul 2v2 con più amici invitati è nel riepilogo di P28)
- **Punti delicati**:
  - la coda tiene un indice utente → voce: i due della coppia puntano alla **stessa** voce; per toglierla si usa sempre `leave` (o `_remove`), mai il `del` di un solo utente;
  - `join_pair` va chiamata dentro Flask (serve per leggere il rating e per avviare il controllo delle code con l'app), come `create_room` (P26);
  - **errore intermittente nella suite `frontend`, corretto** (commit separato nello stesso branch, con l'ok di Giuseppe): circa un giro su cinque dava "1 errori" all'avvio del browser di un test (visto in `test_momenti_tavolo.py`). Causa: `tests/browser.py` leggeva `DevToolsActivePort` mentre Chrome lo stava ancora scrivendo, e su Windows il file bloccato dà `PermissionError`. Non dipendeva da P28 né da P29. Ora `read_devtools_port` considera il file bloccato, vuoto o incompleto come "non ancora pronto" e riprova; test nuovo `tests/frontend/test_avvio_browser.py` (5 controlli); dopo la correzione 10 giri di `frontend` su 10 senza errori.
- **Note per il contratto o per gli altri**: nessun cambiamento al contratto. **Chi fa P47** (io): `invite:start` nel 2v2 chiama `matchmaker.join_pair(current_app._get_current_object(), chi_invita, invitato, target_score, request.sid)` e risponde con lo stato che restituisce; nel 1v1 chiama `create_room(..., rated=False)`. **Christian**: oltre alla correzione del test di P28, ho toccato il tuo `tests/browser.py` (P46) per l'errore intermittente descritto sopra: solo l'attesa della porta di Chrome (`read_devtools_port`), il resto è com'era. **Antonio**: il blocco della suite `api` che avevi visto in P27 potrebbe avere la stessa origine (il browser dei test che non parte), ma non l'ho verificato [N].

### P28 — Matchmaking 1v1 (28/09/2026)

Punto di Antonio, fatto da Giuseppe con il suo permesso (anche per P29, che segue). Prima di cominciare: nessun branch di P28 su GitHub.

- **Branch**: feature/p28-matchmaking
- **File**: creati `app/realtime/matchmaking.py`, `tests/sockets/test_matchmaking_1v1.py`; modificati `app/sockets/lobby_events.py`, `app/static/js/pages/home.js`. **Non toccati**, anche se nell'elenco: `app/sockets/__init__.py` (il controllo delle code parte al primo `queue:join`, `lobby_events` era già registrato) e `ModeModal.js` ("Gioca" arrivava già a `play(...)`). **Fuori elenco, con l'ok di Giuseppe**: `app/repositories/rating_repo.py` (P27, di Antonio: una funzione di sola lettura, `get_value`), `app/sockets/connection_events.py` (P23/P25: stato della coda alla scheda nuova, uscita dalla coda con l'ultima scheda), `app/static/js/core/events.js` (P23: i nomi `QUEUE_*`), `tests/sockets/conftest.py` (il fixture `connect` accetta `before(client)`, per ascoltare gli eventi mandati appena la scheda si collega). Aggiornata anche l'intestazione di questo file con la regola dei documenti a turno, come chiesto da Christian
- **Controlli**: 1092 PASS e **1 FAIL** su 1093, in 7 suite (39 nuovi, nella suite `sockets`, rilanciati 3 volte di fila senza errori), `ruff check .` pulito. Il FAIL è `tests/api/test_pagina_home.py::test_partita_veloce_apre_e_annulla_la_coda` (P22, di Christian): vedi "Note per gli altri"
- **Decisioni prese** (scelte di Giuseppe sulle raccomandazioni di Claude):
  - **abbinamento solo se i due si accettano a vicenda**: la differenza di rating sta nell'intervallo di tutti e due, così nessuno si trova un avversario fuori da "Avversari con rating tra X e Y";
  - **chi chiude tutte le schede esce dalla coda** (`queue:left` con `"cancelled"`), così non viene abbinato a una partita a cui non arriverebbe; una scheda che si collega mentre l'utente è in coda riceve subito `queue:status`;
  - **per P29, coda 2v2 di singoli** (chiude D17): i 4 giocatori si dividono in modo che le medie delle due squadre siano il più vicine possibile.
- **Scelte tecniche**:
  - code in memoria, una per modalità e punteggio, sotto un lock unico; la logica (`MatchQueue`) non dipende da Flask e si prova con un orologio finto;
  - si serve prima chi aspetta da più tempo, con l'avversario di rating più vicino; i posti si tirano a sorte;
  - un thread prova gli abbinamenti ogni secondo e **subito dopo ogni `queue:join`**, e rimanda `queue:status` quando l'intervallo si allarga (ogni 10 secondi fino a ±400, poi `rating_range: null` dopo 2 minuti, D16); l'intervallo non scende sotto 0;
  - la partita si crea con `create_room(..., rated=True)` dentro `app.app_context()`: a fine partita si salva (P26, c'è un test);
  - `queue:join`: `request_id` da 1 a 100 caratteri, `mode` `"1v1"` o `"2v2"`, `target_score` 150, 300 o 500 (intero, non `bool`); lo stesso `request_id` riceve la stessa risposta (`RecentRequests` di P45, importato senza modificarlo); `busy` "Sei già in coda." da un'altra scheda, "Hai già una partita in corso." se è al tavolo; **`mode: "2v2"` risponde `not_allowed` "La coda 2v2 non è ancora attiva."** fino a P29;
  - `queue:status` va anche alle altre schede dello stesso utente; `queue:left` a tutte; `queue:leave` risponde `ok` anche se non era in coda;
  - rating letto a ogni `queue:join` da `rating` della modalità (1500 se manca la riga), convertendo il `Decimal`;
  - pagina: "Gioca" nella Partita Veloce 1v1 usa la coda vera **anche in sviluppo** (con i dati finti restano il 2v2 fino a P29 e gli inviti fino a P47); `game:start` porta al tavolo.
- **Domande nuove**:
  - **2v2 con più amici invitati** (per P29 e P47): Giuseppe vorrebbe "se inviti un solo amico siete in squadra insieme; se ne inviti più di uno, le squadre sono a caso". Oggi però è deciso che **si invita un amico alla volta** (D27, contratto 5.3: un secondo `invite:send` risponde `busy`). Va deciso nel gruppo se cambiarlo; se sì, cambiano il contratto e P47.
- **Punti delicati**:
  - `create_room` dalla coda gira nel thread del controllo, fuori da una richiesta: per questo il thread lavora dentro `app.app_context()`, con l'app presa al primo `queue:join`;
  - la coda non sa quali schede ha l'utente: all'uscita di una scheda `connection_events` conta quelle rimaste nel canale `user:<id>`;
  - un abbinamento la cui `create_room` fallisce (uno dei due è entrato in partita per un'altra via, P47) rimette in coda chi non è in partita, con la sua attesa;
  - i test cambiano `matchmaking.RANGE_STEP_SECONDS` con `monkeypatch` (valori letti al momento dell'uso) e a ogni prova tolgono dalla coda e dalle stanze gli utenti di prova.
- **Note per il contratto o per gli altri**: nessun cambiamento al contratto.
  - **Christian**: il test `test_partita_veloce_apre_e_annulla_la_coda` di `tests/api/test_pagina_home.py` aspetta l'intervallo dei dati finti, "tra 1340 e 1740", ma ora la home entra nella coda vera: l'utente di prova non ha rating (1500), quindi il server manda "tra 1400 e 1600". **Proposta**: nella riga 358 cambiare `"tra 1340 e 1740"` in `"tra 1400 e 1600"`; con questo cambiamento il test passa tutto, compreso Esc che annulla la coda vera (provato con una copia temporanea, poi cancellata). Non l'ho toccato perché il file è tuo: **ci dai l'ok per cambiarlo noi, o lo cambi tu?** In più la schermata di coda si ridisegna a ogni `queue:status` (ogni 10 secondi, per l'intervallo nuovo), quindi le carte che si mescolano ripartono: se vuoi evitarlo, un `setQueueRange(overlay, range)` in `QueueOverlay.js` basterebbe;
  - **Antonio**: `rating_repo.get_value(user_id, mode)` (float o `None`) è di sola lettura, senza blocchi; P29 lo faccio io, sugli stessi file;
  - **tutti**: il `request_id` della home è un codice casuale di 32 cifre esadecimali (`getRandomValues`), uno per clic su "Gioca".

### P55 — Frasi del tavolo in tempo reale (28/09/2026)

- **Branch**: feature/p55-frasi
- **File**: creati `app/realtime/table_phrases.py`, `tests/sockets/test_frasi_tavolo.py`; modificati `app/sockets/game_events.py`, `config.py` (una chiave, `TABLE_PHRASE_MIN_INTERVAL_SECONDS = 3`). **Fuori elenco, con l'ok di Giuseppe**: `app/realtime/room.py` (un solo campo, `phrase_times`, e una riga nella descrizione) e `tests/sockets/test_partita.py` (P24: il fixture `users` registra "Quarto" solo se non c'è, come quello di P25; senza, con il file nuovo che gira prima, 28 test davano errore)
- **Controlli**: 1054 PASS in tutto, in 7 suite (23 nuovi, nella suite `sockets`), `ruff check .` pulito
- **Decisioni prese**: nessuna sul gioco. Scelte tecniche:
  - elenco delle 19 frasi di D24 in `table_phrases.PHRASES` (codice → testo, nell'ordine di D24), unico: la pagina lo riceve con `game:phrases`;
  - `game:join` manda `game:phrases` a chi entra **prima** di `game:state` (contratto 3.2), a ogni ingresso;
  - `game:send_phrase` `{game_id, code}`: sotto il lock della stanza; solo dalla scheda al tavolo (D14), altrimenti `not_allowed`; codice fuori elenco `invalid_data` "Frase non valida."; poi `game:phrase` `{seat, code}` a tutti al tavolo, anche a chi l'ha mandata e agli avversari nel 2v2;
  - limite per giocatore: `too_fast` con `retry_after` in **secondi interi arrotondati per eccesso** (3 subito dopo una frase); un rifiuto non conta per il limite;
  - **le frasi si possono mandare anche a partita finita** ("Bella partita!"), finché la stanza esiste;
  - l'ora dell'ultima frase sta nella stanza (`room.phrase_times`, `time.monotonic`), mai il testo; codice e testo non vanno nel log né nel database (c'è un test).
- **Domande nuove**: nessuna
- **Punti delicati**:
  - il limite si legge da `table_phrases.MIN_INTERVAL_SECONDS` al momento della frase: i test lo riducono con `monkeypatch`, senza cambiare `config.py`;
  - più file della suite `sockets` registrano l'utente "Quarto": ogni fixture deve registrarlo **solo se non c'è**.
- **Note per il contratto o per gli altri**: nessun cambiamento al contratto. **Christian** (P56): l'elenco arriva con `game:phrases` a ogni `game:join` (anche al rientro); `game:phrase` porta `seat` e `code`, il testo si prende dall'elenco; `retry_after` è in secondi interi. Il pulsante resta disattivato 3 secondi dopo l'invio; se arriva comunque `too_fast`, `retry_after` dice quanto aspettare

### Correzione — Test instabile di P25 ed eventi di gioco senza dati (28/09/2026)

- **Branch**: fix/p25-timer-e-dati
- **File**: modificati `app/sockets/game_events.py` (P24), `tests/sockets/test_timer_riconnessione.py` (P25), `tests/sockets/test_partita.py` (P24). Nessun file fuori elenco; `room.py` non toccato
- **Controlli**: 1031 PASS in tutto, in 7 suite (3 nuovi, nella suite `sockets`), `ruff check .` pulito. Il test instabile: prima 1 fallimento su 15 giri, dopo la correzione 0 su 20
- **Decisioni prese**: nessuna
- **Domande nuove**: nessuna
- **Cosa è cambiato**:
  - **test instabile** `test_turno_scaduto_il_server_gioca_la_mossa_automatica`: l'errore era nel test, non nel server. Con il turno da 0,3 s già alla creazione della stanza, le mosse automatiche partivano mentre i client si collegavano (è giusto così: chi non è seduto riceve la mossa automatica, scelta di P25). Se alla prima vista il turno era di chi risponde, la sua carta chiudeva la presa e finiva in `last_trick`, senza comparire mai in `trick`: il test aspettava 5 secondi e falliva (l'ipotesi di Christian era giusta). Ora i giocatori si siedono con un turno di 30 s, poi il test porta il turno a 0,3 s e fa ripartire il timer sotto il lock della stanza (`shorten_turn`);
  - **`on_join`, `on_play_card`, `on_sing`** hanno `data=None`, come `on_leave`: un evento senza dati risponde `invalid_data` invece di `server_error` (correzione proposta da Antonio in P25; test nuovo `test_evento_senza_dati_rifiutato`).
- **Punti delicati**: nei test con il turno corto, le viste arrivate **prima** del timer possono contenere già mosse automatiche; la carta che chiude una presa si vede solo in `last_trick`. Gli altri due test di P25 con il turno corto lo tengono già in conto
- **Note per il contratto o per gli altri**: nessun cambiamento al contratto. **Christian**: il test di P25 che falliva sul tuo PC è corretto; il numero dei controlli è 1031

### P24 — Stanze e partita completa (28/09/2026)

- **Branch**: feature/p24-partita (la parte server è partita prima che P21 fosse in `dev`; `game.js` l'ho toccato solo dopo, con P21 in `dev`)
- **File**: modificati app/realtime/room.py, room_manager.py (P23), app/sockets/game_events.py (P4), app/static/js/pages/game.js (P21); creato tests/sockets/test_partita.py
- **Controlli**: 790 PASS in tutto (29 nuovi, nella suite `sockets`), `ruff check .` pulito. Provato anche una volta in Chrome senza finestra (script fuori dal progetto): il tavolo si disegna dalla partita vera, un clic su una carta arriva al server e l'avversario riceve la vista nuova, D14 mostra "partita aperta in un'altra scheda"
- **Decisioni prese** (tecniche, nessuna sul gioco):
  - `create_room(giocatori, modalità, punteggio, rated=True)` in `room_manager.py`: i giocatori si passano **nell'ordine dei posti** (nel 2v2 i posti 0 e 2 sono una squadra, contratto 3.1), come `User` o `Player`; rifiuta con `RoomError` modalità, numero di giocatori, punteggio non validi, lo stesso utente due volte e chi è già in una partita in corso. Manda `game:start` a ogni giocatore (`url` = `/game/<game_id>`);
  - `find_room_of_user(user_id)`: la stanza della partita **in corso** di quell'utente, o `None`;
  - `version` parte da 1 e sale a ogni mossa e a ogni cambio della scheda al tavolo; `turn.seconds_left` si calcola da quando è cominciato il turno (il timer che gioca da solo è di P25); `connected` = il posto ha una scheda al tavolo; `reconnect_seconds_left` sempre `null` fino a P25;
  - D14: ogni posto ha una sola scheda al tavolo, l'ultima che ha fatto `game:join`; la precedente riceve `game:replaced` e le sue mosse ricevono `not_allowed`, come quelle di chi non ha fatto `game:join`;
  - `game:sang` porta Re (rank 10) e Cavallo (rank 9) del seme, `show_seconds` 3 (D15).
- **Domande nuove**: nessuna
- **Punti delicati**:
  - **mai due `create_app()` nello stesso processo con il tempo reale acceso**: `socketio` è un oggetto unico e si ricollega all'ultima app, così il server già avviato non riceve più gli eventi giusti (successo nei test: ogni evento rispondeva `('', 400)`);
  - ordine dei controlli di una mossa: dati → partita e posto → scheda al tavolo → `version` → motore (`not_your_turn`, `illegal_move`); con `stale_state` la pagina riceve anche la vista attuale;
  - la vista si confronta nei test con le chiavi di `app/static/dev/vista_1v1.json`: se il contratto cambia, quel test lo segnala;
  - le viste di `game:state` partono dentro il gestore, prima della risposta: la pagina può ricevere `game:state` prima dell'`ok` di `game:join` (per l'ordine vale `version`).
- **Note per gli altri**:
  - **Antonio** (P28, P29) e **Giuseppe** (P47): per creare una partita `create_room(...)`; **P44**: `find_room_of_user(...)`. Tutte e due in `app/realtime/room_manager.py`, senza modificarlo;
  - **`game.js`** (P24): in prova (`?demo=`) non si collega al server; in partita fa `game:join` a ogni collegamento (anche dopo una riconnessione), chiama `render(vista)` a ogni `game:state` (ignorando le viste con `version` più vecchia), manda le mosse con la `version` della vista e, finché non arriva la risposta, disegna la vista con `legal` vuoto (carte e "Canta" disattivati); un errore va nella riga di stato (`setStatus`); `game:sang` scrive "X ha cantato 40 a coppe" per 3 secondi; con `game:replaced` il tavolo si ferma con un messaggio;
  - **Christian**: restano da disegnare (P25 o un punto dell'interfaccia) l'ultima presa per un momento, il riepilogo di fine mano e le due carte del canto per 3 secondi: per ora il canto è solo una scritta. "Esci" torna alla home senza `game:leave`: l'abbandono è di P25.

### P23 — Collegamento in tempo reale (28/09/2026)

- **Branch**: feature/p23-realtime
- **File**: creati app/realtime/events.py, room.py, room_manager.py, app/static/js/core/socket.js, events.js, app/static/js/vendor/socket.io.min.js, tests/sockets/conftest.py, test_connessione.py, test_lock_stanza.py; modificato app/sockets/connection_events.py. `app/sockets/__init__.py` era nell'elenco ma non è servito toccarlo.
- **Controlli**: 748 PASS in tutto (12 nuovi, nella suite nuova `sockets`; conteggio dopo P20 di Christian), `ruff check .` pulito
- **Decisioni prese** (tecniche, nessuna sul gioco):
  - client Socket.IO **4.8.1**, versione "ES module" (`socket.io.esm.min.js` di jsDelivr), salvata con il nome dell'elenco, `vendor/socket.io.min.js`: così `core/socket.js` la importa e la pagina resta con un solo script (regola di P19). In cima al file: versione, origine e SHA-256 dell'originale;
  - ogni scheda collegata entra nel canale `user:<id>` (tutte le schede di un utente) e le stanze di gioco usano il canale `room:<game_id>`; `game_id` è un codice casuale di 12 caratteri (`secrets.token_urlsafe`);
  - D14 ("l'ultima scheda prende il posto", `game:replaced`) scatta con `game:join`, quindi la fa P24;
  - `events.py` ha la forma unica delle risposte (`ok`, `error`, il decoratore `handler` e `EventError` con i soli codici del contratto): un errore imprevisto diventa `server_error` e il dettaglio va solo nel log;
  - `socket.js`: `send()` non manda niente senza connessione e risponde subito con `{ok: false, error: {code: "no_connection", ...}}`; è un codice **solo della pagina**, non del server, quindi non è nella tabella del contratto.
- **Domande nuove**: nessuna
- **Punti delicati**:
  - ogni evento di una stanza passa da `room.run(...)` (lock della stanza, rientrante): il test manda 50 azioni insieme da 5 client e controlla che nel lock ne entri una alla volta; togliendo il lock il contatore arriva a 5 invece di 50 (provato);
  - la suite `sockets` avvia un server vero sulla porta 5099 in un thread e fa il login via HTTP con il codice CSRF; vuole MySQL;
  - il server di sviluppo (Werkzeug) non risponde alla chiusura ordinata del websocket: il client Python la aspetta 3 secondi per connessione (la suite ci metteva 42 s). Nei test l'attesa è accorciata a 0,1 s; il browser non aspetta quella risposta [D].
- **Note per gli altri**: le pagine che usano il tempo reale importano `core/socket.js` (`connect`, `send`, `on`, `onStatus`) e i nomi da `core/events.js`. P24 (Giuseppe) attende P21 di Christian.

### Correzione di migrate.py quando MySQL rifiuta la connessione (28/09/2026)

- **Branch**: fix/migrate-connessione (era "Da assegnare" in `SCALETTA.md`)
- **File**: modificato scripts/migrate.py (`main`); creato tests/db/test_migrate_connessione.py, file nuovo per non toccare `test_migrate.py` di P5
- **Controlli**: 719 PASS in tutto (2 nuovi, in `db`), `ruff check .` pulito
- **Decisioni prese**: nessuna. `engine.raw_connection()` lancia l'errore di PyMySQL così com'è, mentre `main` aspettava solo quello di SQLAlchemy: ora li prende tutti e due e stampa il suo messaggio con il codice di MySQL.
- **Domande nuove**: nessuna
- **Punti delicati**: il test prova password sbagliata (errore 1045, vuole MySQL acceso) e porta senza MySQL (2003), con la configurazione dei test; controlla che non ci sia traceback e che la password non compaia nel messaggio.
- **Note per gli altri**: nessuna

### P16 — Registrazione, login, logout: la logica (28/09/2026)

Punto di Antonio, fatto da Giuseppe con il suo permesso. È la parte di logica; la grafica di `login.html` e `register.html` si rifinisce dopo, sempre da Giuseppe.

- **Branch**: feature/p16-auth (partito prima che P7 fosse in `dev`, con l'ok di Giuseppe: P16 non tocca i file di P7)
- **File**: creati app/blueprints/auth/forms.py, app/services/auth_service.py, app/repositories/user_repo.py, app/templates/auth/login.html, app/templates/auth/register.html (versione di base, con le classi di P19), tests/api/test_auth.py; modificato app/blueprints/auth/routes.py. Nessun file fuori elenco.
- **Controlli**: 717 PASS in tutto (30 nuovi, in `api`), `ruff check .` pulito
- **Decisioni prese** (raccomandazioni di Claude, accettate da Giuseppe):
  - login **solo con lo username** (non con l'email); dopo la registrazione si entra subito e si torna alla home con "Benvenuto, *username*!";
  - **troppi tentativi**: contati **per username, in memoria**; dopo `LOGIN_MAX_ATTEMPTS` (5) errori, per `LOGIN_LOCK_SECONDS` (300) quello username non entra nemmeno con la password giusta ("Troppi tentativi sbagliati: riprova tra qualche minuto."); il conteggio si azzera con un login riuscito, dopo 5 minuti senza errori o al riavvio del server. Nessuna colonna nuova;
  - password e username sbagliati danno lo **stesso messaggio** ("Username o password non corretti."), e con uno username inesistente si calcola comunque un hash, così nemmeno il tempo di risposta dice se l'account esiste;
  - D8 usata com'è in `config.py` (almeno 8 caratteri): resta provvisoria in `DA-DECIDERE.md`.
- **Domande nuove**: nessuna
- **Punti delicati**:
  - username o email già usati li rifiuta il vincolo unico di MySQL al commit (`uq_utenti_nome`, `uq_utenti_email`), non un controllo fatto prima: così due registrazioni contemporanee non creano doppioni. L'email è unica senza distinguere le maiuscole (collation della colonna), lo username le distingue (D7);
  - il vero `user_loader` di Flask-Login si registra in `auth/routes.py` e sostituisce il segnaposto di `extensions.py`;
  - dopo il login si torna alla pagina chiesta (`?next=`) solo se è un indirizzo di questo sito (niente `//altro-sito`);
  - `/auth/logout` accetta solo POST con il codice CSRF, come il modulo "Esci" di P40; i moduli senza codice CSRF sono rifiutati (400);
  - le password sono hash `scrypt` di werkzeug; nei log non finiscono mai password né username (c'è un test).
- **Note per gli altri**:
  - **Christian**: le pagine di accesso e registrazione non hanno ancora uno script di pagina, quindi la navbar lì non si apre (serve `core/layout.js` con `initLayout()`, come dice il riepilogo di P40). Lo aggiungiamo con la grafica delle due pagine; il file (`js/pages/auth.js` o simile) non è nell'elenco di P16, va concordato;
  - **Antonio**: P16 è fatto (resta la grafica); P17 ha `auth_service` e `user_repo` da estendere. La suite `api` ora richiede MySQL (`test_auth.py`);
  - P23 (Giuseppe) può partire: attendeva P16.

### Correzione del controllo di MySQL all'avvio (28/09/2026)

- **Branch**: fix/checks-database
- **File**: modificati app/checks.py (riga 39), tests/api/test_avvio.py (1 test nuovo)
- **Controlli**: 672 PASS in tutto (1 nuovo), `ruff check .` pulito
- **Decisioni prese**: nessuna. È il bug segnalato da Christian nel riepilogo di P5: `url.set(database=None)` non toglie il database, perché `set()` ignora i valori `None`, quindi il controllo di `run.py` si collegava già a `DB_NAME` e, se il database non esisteva, dava il messaggio sbagliato. Ora è `url._replace(database=None)`.
- **Domande nuove**: nessuna
- **Punti delicati**: il test sostituisce `create_engine` con una funzione finta e controlla che riceva l'indirizzo senza database, con utente, password, host, porta e charset invariati; non serve MySQL. Provato anche a mano sul MySQL vero: con un `DB_NAME` inesistente il controllo di versione ora passa, e l'errore sul database arriverà dopo, con il suo messaggio.
- **Note per il contratto o per gli altri**: nessuna

### P6 — Runner dei test (28/09/2026)

- **Branch**: feature/p6-runner
- **File**: creati tests/esegui_tutti.py, tests/conftest.py, tests/runner/test_esegui_tutti.py
- **Controlli**: 671 PASS in tutto (13 nuovi), `ruff check .` pulito; giro completo con `python tests/esegui_tutti.py` in 24 s
- **Decisioni prese**: nessuna sul gioco. Scelte tecniche: tempo massimo 120 s per suite (oggi la più lenta, engine, ci mette 6 s); le suite sono le cartelle di tests/ con almeno un test_*.py, nell'ordine runner, engine, db, api, services, sockets, frontend, e2e, poi le altre in ordine alfabetico; `python tests/esegui_tutti.py engine db` lancia solo quelle. Codici d'uscita: 0 tutto PASS, 1 almeno un FAIL, 2 rifiuto prima di partire. Un file **nuovo** tra quelli protetti (per esempio una `migrations/002_….sql` comparsa durante i test) si segnala ma non si cancella, perché potrebbe essere lavoro vero; quelli modificati o cancellati si ripristinano dopo ogni suite, con controllo dell'hash.
- **Domande nuove**: nessuna
- **Punti delicati**: `tests/conftest.py` ripete i rifiuti (PRODUZIONE, database che non finisce con _test) anche per chi lancia `pytest` a mano, e imposta `APP_ENV=testing` per tutti i test. Una suite che supera il tempo si ferma con tutti i processi che ha avviato (`taskkill /T`), così un server di test rimasto appeso non occupa la porta 5099. Se MySQL non risponde, la pulizia finale del database lo scrive nel riepilogo ma non cambia l'esito.
- **Note per il contratto o per gli altri**: P7 e P18 (Antonio) possono partire. Da ora il comando dei test è `python tests/esegui_tutti.py` (il "Finché P6 non c'è" di CLAUDE.md si può togliere; il numero di controlli diventa 671). Trovato fuori dal punto: `scripts/migrate.py` (P5), se MySQL rifiuta utente o password, esce con un traceback invece del suo messaggio in italiano, perché `engine.raw_connection()` lancia l'errore di PyMySQL e non quello di SQLAlchemy che il `main` aspetta; da correggere su un branch `fix/…` di chi decide Christian.

### P15 — Vista per giocatore, mosse legali, mossa automatica (28/09/2026)

- **Branch**: feature/p15-viste
- **File**: creati app/game/engine/views.py, auto_move.py, tests/engine/test_viste.py, tests/engine/test_mossa_automatica.py
- **Controlli**: 603 PASS in tutto (70 nuovi), `ruff check .` pulito
- **Decisioni prese**: nessuna sul gioco (applicata D12). Scelta tecnica: il motore non conosce la stanza, quindi `player_view(partita, posto)` produce tutti i campi di gioco del contratto (3.3) con i nomi e la forma di `vista_*.json`, e la stanza (P24/P25) aggiunge i suoi: `game_id`, `version`, `rated`; per ogni giocatore `user_id`, `username`, `avatar`, `connected`, `reconnect_seconds_left`; nel turno `seconds_total`, `seconds_left`. Sono elencati in `ROOM_FIELDS`, `ROOM_PLAYER_FIELDS` e `ROOM_TURN_FIELDS` di views.py. Il `result` del motore ha sempre `reason: "score"` e `abandoned_seats: []`: l'abbandono lo scrive la stanza. La mossa automatica è `auto_move(partita, rng)` e restituisce la carta per chi è di turno.
- **Domande nuove**: nessuna
- **Punti delicati**: un test prova tutte le posizioni di 10 partite intere, per ogni posto, e controlla che nella vista ci siano solo le carte in mano a quel posto, la presa in corso e l'ultima presa chiusa. `legal` si confronta con le mosse che `apply_game` accetta davvero (40 carte e 4 semi per ogni posto e posizione). Nella mossa automatica i punti contano prima della briscola: il 2 di briscola si gioca prima dell'Asso di un altro seme.
- **Note per il contratto o per gli altri**: la carta nella vista è `{"suit", "rank"}` (`card_to_dict`). Per le azioni che arrivano dalla pagina (`game:play_card`), la conversione inversa da `{"suit", "rank"}` a carta, con il rifiuto dei valori non validi, la farà P24. `last_hand.hand_number` si ricava da `hand_number` (a partita finita è la mano in corso, altrimenti quella prima).

### P14 — Partita fino al punteggio scelto (28/09/2026)

- **Branch**: feature/p14-partita
- **File**: creati tests/engine/test_partita.py; modificati app/game/engine/state.py (GameState, GameResult), app/game/engine/game.py (new_game, apply_game, game_legal_actions)
- **Controlli**: 533 PASS in tutto (108 nuovi), `ruff check .` pulito
- **Decisioni prese**: nessuna sul gioco (applicata D11). Scelte tecniche: le funzioni della mano (apply, legal_actions) restano com'erano e la partita le usa; a fine mano, se nessuno ha vinto, la mano dopo comincia subito con il mazzo mescolato di nuovo (la pausa per mostrare il riepilogo spetta alla stanza, P24); il mazziere non si salva, si ricava: `dealer_seat = (first_seat - 1) % n`. L'abbandono (`reason: "abandon"` del contratto) resta a P24/P25: P14 fa solo la fine per punteggio.
- **Domande nuove**: nessuna
- **Punti delicati**: il punteggio si controlla solo a fine mano; un canto che porta a N durante la mano non la chiude (c'è un test). A partita finita `hand` resta l'ultima mano, finita, e ogni mossa viene rifiutata con "La partita è finita.". Un punteggio diverso da 150, 300 o 500 (anche `True` o `"300"`) viene rifiutato con "Punteggio non valido: si gioca a 150, 300 o 500.".
- **Note per il contratto o per gli altri**: i campi di GameState corrispondono a quelli della vista (`hand_number`, `dealer_seat`, `scores`, `last_hand`, `result.winner_team` con None per il pareggio): P15 li userà direttamente.

### P13 — Svolgimento di una mano (28/09/2026)

- **Commit**: 448da13, in dev e su GitHub (fast-forward, niente rebase)
- **File**: creati app/game/engine/actions.py, state.py, game.py, tests/engine/test_mano.py
- **Controlli**: 412 PASS (129 + 283 nuovi: le mani intere si provano con 100 semi fissi per modalità), ruff check . pulito
- **Decisioni prese**: nessuna sul gioco. Correzione a quanto ti avevo scritto sul contratto: il contatore version non sta nello stato del motore ma nella stanza (P24/P25), perché secondo il contratto deve salire anche per scollegamenti e rientri, che il motore non conosce. Il contratto non cambia.
- **Note tecniche**: legal_actions(stato, posto) sta in game.py, come chiede CLAUDE.md, e P15 la userà per legal. La squadra di un posto è posto % 2. new_hand riceve un mazzo già mescolato e chi comincia: mescolare e applicare D11 spetta a P14.
- **Domande nuove**: nessuna
- **Punti delicati**: dopo un canto il turno resta a chi ha cantato, che deve ancora giocare la carta. Un test prova tutte le 40 carte e i 4 semi su ogni posizione di 20 mani e controlla che le mosse legali siano esattamente quelle accettate da apply.

### P12 — Cantare 40 e 20 (28/09/2026)

- **Commit**: b5d7123, in dev e su GitHub (fast-forward, niente rebase)
- **File**: creati app/game/engine/singing.py, tests/engine/test_canti.py. Modificato fuori elenco, con il mio ok: app/game/engine/errors.py. Ho aggiunto NotYourTurnError, un caso particolare di InvalidMoveError, così il server (P24) può rispondere not_your_turn invece di illegal_move, come chiede il contratto (1.2). È un file mio (P10) e nessun altro lo tocca.
- **Controlli**: 129 PASS (106 + 23 nuovi), ruff check . pulito
- **Decisioni prese**: nessuna nuova ("un seme alla volta" è già in DECISIONI.md). Nota tecnica: i canti della mano sono un elenco Sing(seat, suit, points), nella stessa forma di sings nella vista. La briscola è il seme del primo canto e si ricava dall'elenco, senza salvarla a parte.
- **Domande nuove**: nessuna
- **Punti delicati**: il 40 è il primo canto della mano di chiunque, non di ciascun giocatore. Il controllo "Re o Cavallo già giocato" non cambia mai l'esito da solo, perché senza quella carta la coppia manca comunque, ma dà il messaggio giusto. Una prova su 3.000 situazioni controlla che singable_suits (per legal.sing) e sing diano sempre la stessa risposta.

### P11 — Chi vince la presa (28/09/2026)

- **Commit**: 121aea7 sul branch feature/p11-presa
- **File**: creati app/game/engine/trick.py, tests/engine/test_presa.py
- **Controlli**: 106 PASS (76 + 30 nuovi), ruff check . pulito
- **Decisioni prese**: nessuna. Nota tecnica: trick_winner(carte, briscola) restituisce la posizione della carta vincente nell'ordine di gioco (0 = chi ha aperto); sarà P13 a trasformarla nel giocatore.
- **Domande nuove**: nessuna
- **Punti delicati**: le carte di un seme diverso da quello di uscita e dalla briscola non prendono mai, nemmeno l'Asso. I test controllano tutte le coppie di carte e 2.000 prese da 4 carte.

### P10 — Carte, mazzo, parametri delle regole (28/09/2026)

- **Commit**: 3052632, in dev e su GitHub (rebase su b8db176, poi fast-forward)
- **File**: creati app/game/engine/cards.py, deck.py, rules.py, errors.py, tests/engine/test_carte_mazzo.py
- **Controlli**: 76 PASS (31 + 45 nuovi), ruff check . pulito
- **Decisioni prese**: nessuna nuova. Nota tecnica: i punteggi 150/300/500 sono sia in config.py sia in RuleSet, perché il motore non può importare config.py; un test controlla che restino uguali.
- **Domande nuove**: nessuna
- **Punti delicati**: i codici delle carte ("denari-1") si confrontano in modo esatto, e ogni codice diverso viene rifiutato con "Carta non valida." (serve per le azioni che arrivano dal client). C'è un test che impedisce al motore di importare Flask, il database o config.py.
