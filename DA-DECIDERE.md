# Da decidere

Domande ancora aperte, per l'utente o per il gruppo. Quando una è decisa: spuntala, spostala in `DECISIONI.md` con data e motivo, e cancellala da qui.
I punti di `SCALETTA.md` che dipendono da una domanda la richiamano con il suo codice (D1, D2, …).
Per D7, D8, D9, D10, D16, D24, D26 e D27, `config.py` (P4) usa già il valore consigliato, con il commento "provvisorio, Dn": se la decisione è diversa, si cambia solo quel numero.

## Processo e gruppo

- [ ] **D1 — Data esatta di consegna** e cosa va consegnato (codice, dimostrazione dal vivo, relazione?).
- [ ] **D2 — Chi dà l'ok ai merge in `dev` degli altri due studenti**, e dopo il merge si fa subito il push (così gli altri vedono il lavoro) oppure no? Consigliato: ognuno dà l'ok ai propri punti dopo averli provati, e fa il push su `dev` subito dopo il merge. Resta da decidere anche cosa fare del branch `christian`, che non è più il branch di partenza: lasciarlo com'è *(consigliato)* o cancellarlo.
- [ ] **D3 — Chi è lo Studente 1, 2 e 3** della sezione 9 di `SCALETTA.md`, e se la divisione proposta va bene.
- [ ] **D22 — Chi aggiorna i documenti condivisi** (`SCALETTA.md`, la riga "Stato" di `CLAUDE.md`, `DECISIONI.md`, `DA-DECIDERE.md`). Se li modificano tutti e tre nei branch dei punti, i conflitti sono quasi certi, perché le righe da spuntare sono vicine tra loro. Opzioni: a) nei branch dei punti non si toccano; **una sola persona li aggiorna a fine giornata**, su un branch apposito da `dev` *(consigliata)*; b) ognuno li aggiorna nel proprio branch e i conflitti si risolvono a mano; c) la riga "Stato" diventa una riga per studente, e per il resto vale la a).

## Tecnologia

- [ ] **D5 — Piano B se una libreria non funziona con Python 3.14**: passare tutti alla 3.13 (consigliato), oppure cercare una libreria alternativa.

## Dati

- [ ] **D6 — Cosa succede alle partite quando un utente cancella l'account**: a) si **anonimizzano** (la partita resta per le statistiche degli altri, il nome diventa "utente eliminato") *(consigliata)*; b) si cancellano anche le sue righe nelle partite. → **Proposta di Christian (27/09/2026): a), da confermare con il gruppo.**
- [ ] **D7 — Regole per lo username**: consigliato da 3 a 20 caratteri, solo lettere, numeri e `_`, e senza distinzione tra maiuscole e minuscole (`Mario` e `mario` sono lo stesso utente). → **Proposta di Christian (27/09/2026): come consigliato, da confermare con il gruppo.** Serve per la colonna `username` di P5 (vedi D38).
- [ ] **D8 — Regole per la password**: consigliato almeno 8 caratteri, senza altri obblighi.
- [ ] **D9 — Rating iniziale e visibilità**: consigliato 1500, mostrato come "provvisorio" per le prime 10 partite.
- [ ] **D10 — Per quanti giorni tenere i backup**: consigliato 14 giorni.
- [ ] **D38 — Tabelle del database (P5) e creazione dell'utente MySQL**: proposta di Claude del 27/09/2026, **non ancora approvata** (Christian ne parla con il gruppo). Vale se D6, D7, D23 e D24 restano come proposto sopra.
  - Tutte le tabelle in `utf8mb4`, InnoDB, collation `utf8mb4_0900_ai_ci`, che non distingue maiuscole e minuscole: `Mario` e `mario` sono lo stesso username, garantito dal database (D7).

    | Tabella | Colonne principali | Se l'utente cancella l'account |
    |---|---|---|
    | `users` | `id`, `username` VARCHAR(20) unico, `email` VARCHAR(254) unica, `password_hash`, `avatar` (facoltativo), `created_at` | — |
    | `ratings` | `user_id`, `mode` (`1v1`/`2v2`), `rating`, `rd`, `volatility`, `updated_at`; chiave (`user_id`, `mode`) | si cancella |
    | `matches` | `id`, `mode`, `target_score` (il database accetta solo 150, 300, 500), `rated` (sì/no), `started_at`, `ended_at`, `end_reason` (`score`/`abandon`), `winner_team` (vuoto = pareggio), `team0_score`, `team1_score` | resta |
    | `match_players` | `match_id`, `seat` (0–3), `team` (0/1), `user_id`, `result` (`win`/`loss`/`draw`), `abandoned` | resta, con `user_id` vuoto → "utente eliminato" (D6) |
    | `match_events` | `match_id`, `seq`, `hand_no`, `seat`, `type`, `data` (JSON), `created_at` | resta (contiene solo i posti, non gli utenti) |
    | `friendships` | `requester_id`, `addressee_id`, `status` (`pending`/`accepted`), `created_at`, `responded_at`; una sola riga per coppia, in qualunque direzione | si cancella |
    | `user_blocks` | `blocker_id`, `blocked_id`, `created_at` (D23) | si cancella |
    | `chat_messages` | `id`, `sender_id`, `recipient_id`, `body` VARCHAR(300), `created_at`, `read_at` | si cancella (D24) |
    | `schema_version` | `version`, `filename`, `applied_at` | — |

  - **Niente stato duplicato**: le statistiche (partite, vinte, perse) e il numero di partite del rating provvisorio (D9) si calcolano da `match_players`, senza contatori; il rating iniziale sta solo in `config.py`. Una richiesta di amicizia rifiutata si cancella (così si può rimandare). La pulizia dei messaggi più vecchi di 30 giorni la fa P48.
  - **`setup_db.sql`** (lanciato come root, una volta sola) crea `cinquecento_dev`, `cinquecento_test` e l'utente MySQL `cinquecento` con i permessi solo su quei due database. La password **non sta nel file**: `IDENTIFIED BY RANDOM PASSWORD` di MySQL 8.0 la genera e la mostra una volta sola, e ognuno la copia nel proprio `.env`; rilanciando il file non viene rigenerata. Un commento spiega come crearne una nuova se si perde.
  - **`migrate.py`** applica in ordine le migrazioni non ancora registrate in `schema_version`; `--test` lavora su `cinquecento_test`. Le istruzioni che creano tabelle, in MySQL, non si annullano in blocco: se un file si ferma a metà, lo script si ferma con un messaggio chiaro e non segna la versione.
  - **Chi lancia `setup_db.sql`** sul PC di Christian: a) lui stesso, con `mysql -u root -p < scripts/setup_db.sql` *(consigliato)*; b) Claude, con le credenziali di root del `.env`, senza stamparle.

## Gioco

- [ ] **D11 — Chi fa il mazziere e chi gioca per primo**: consigliato mazziere a caso nella prima mano, poi a rotazione verso destra, e gioca per primo il giocatore alla destra del mazziere.
- [ ] **D12 — Quale carta gioca il server quando scadono i 30 secondi**: consigliata la carta di valore più basso, senza cantare.
- [ ] **D13 — Abbandono nel 2v2**: consigliato che perda tutta la squadra, con penalità sul rating solo per chi ha abbandonato; oppure penalità per tutta la squadra.
- [ ] **D14 — Stesso utente in due schede o dispositivi**: consigliato che l'ultima scheda aperta prenda il posto della precedente, che mostra "partita aperta altrove"; oppure la seconda scheda viene bloccata.
- [ ] **D15 — Per quanto tempo si mostrano le carte del canto** agli avversari: consigliati 3 secondi, più un'icona fissa accanto al giocatore per tutta la mano.
- [ ] **D16 — Tolleranza del matchmaking**: consigliato di partire con ±100 punti di rating, allargare di +50 ogni 10 secondi, fino a ±400. Dopo 2 minuti si accetta qualunque avversario.
- [ ] **D17 — Formazione delle squadre nella coda 2v2**: consigliato di unire i 4 giocatori in modo che le medie delle due squadre siano il più vicine possibile.

## Amici e chat

- [ ] **D23 — Blocco degli utenti**: consigliato **sì**. Un utente bloccato non può mandarti richieste né messaggi, e il blocco rimuove l'amicizia. Serve saperlo **prima di P5**, perché cambia le tabelle. → **Proposta di Christian (27/09/2026): sì, da confermare con il gruppo.**
- [ ] **D24 — Per quanto tempo si conservano i messaggi della chat**: consigliati 30 giorni. Si cancellano comunque con l'account. Serve **prima di P5**. → **Proposta di Christian (27/09/2026): 30 giorni, da confermare con il gruppo.**
- [ ] **D25 — Con chi si chatta**: consigliato **solo tra amici**, uno a uno, senza chat durante la partita.
- [ ] **D26 — Limiti**: consigliati al massimo 100 amici, messaggi di 300 caratteri al massimo, non più di 1 messaggio al secondo.
- [ ] **D27 — Inviti a partita**: consigliata una scadenza di 60 secondi. Dal prototipo approvato il 27/09/2026: nel 1v1 l'amico invitato è l'avversario; nel 2v2 è il **compagno di squadra** e gli avversari arrivano dal matchmaking. Si invita un amico alla volta. Resta da decidere cosa succede se l'amico rifiuta o non risponde (consigliato: l'invito scade, compare un avviso e si può invitare un altro amico).
- [ ] **D33 — Ricerca di un utente per mandargli la richiesta**: consigliato **username esatto** (protegge la privacy ed evita lo spam); oppure ricerca per parte del nome.

## Interfaccia

- [ ] **D18 — Colore del tavolo di gioco**: colori e stile delle pagine vengono dal prototipo scritto da Claude (P52, stile siciliano, tema chiaro e scuro). Resta da decidere il tavolo, che il prototipo non comprende: consigliato il verde classico, accostato alla palette del prototipo, con una versione per il tema scuro.
- [ ] **D19 — Immagini delle carte**: da dove vengono le vostre immagini e con che licenza? Serve saperlo per usarle nella versione finale (punto P35).
- [ ] **D29 — Set di avatar**: quanti e con che soggetti? Consigliati 12 (i 4 semi e le 8 figure siciliane: Re, Cavallo e Fante di alcuni semi), in formato SVG. Chi li disegna, o da dove si prendono, e con che licenza?

## Tempi

- [ ] **D31 — Ordine di taglio se il tempo non basta**: proposto in `SCALETTA.md`, sezione 5 (avatar e logo → carte vere → chat → matchmaking 2v2 → rifinitura mobile). Va bene, o preferite un altro ordine?

## Messa in servizio

- [ ] **D20 — Quale PC ospita la demo** e come si collegano gli altri: stessa rete Wi-Fi (consigliato), oppure un tunnel come ngrok (richiede un account gratuito).
- [ ] **D21 — Dopo la consegna**: VPS o hosting gestito (Render o Railway), come spiegato il 26/09/2026.
