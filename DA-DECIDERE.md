# Da decidere

Domande ancora aperte, per l'utente o per il gruppo. Quando una è decisa: spuntala, spostala in `DECISIONI.md` con data e motivo, e cancellala da qui.
I punti di `SCALETTA.md` che dipendono da una domanda la richiamano con il suo codice (D1, D2, …).

## Processo e gruppo

- [ ] **D1 — Data esatta di consegna** e cosa va consegnato (codice, dimostrazione dal vivo, relazione?).
- [ ] **D2 — Chi dà l'ok ai merge in `dev` degli altri due studenti**, e dopo il merge si fa subito il push (così gli altri vedono il lavoro) oppure no? Consigliato: ognuno dà l'ok ai propri punti dopo averli provati, e fa il push su `dev` subito dopo il merge. Resta da decidere anche cosa fare del branch `christian`, che non è più il branch di partenza: lasciarlo com'è *(consigliato)* o cancellarlo.
- [ ] **D3 — Chi è lo Studente 1, 2 e 3** della sezione 9 di `SCALETTA.md`, e se la divisione proposta va bene.
- [ ] **D22 — Chi aggiorna i documenti condivisi** (`SCALETTA.md`, la riga "Stato" di `CLAUDE.md`, `DECISIONI.md`, `DA-DECIDERE.md`). Se li modificano tutti e tre nei branch dei punti, i conflitti sono quasi certi, perché le righe da spuntare sono vicine tra loro. Opzioni: a) nei branch dei punti non si toccano; **una sola persona li aggiorna a fine giornata**, su un branch apposito da `dev` *(consigliata)*; b) ognuno li aggiorna nel proprio branch e i conflitti si risolvono a mano; c) la riga "Stato" diventa una riga per studente, e per il resto vale la a).
- [ ] **D4 — Strumento di controllo del codice (lint)**: consigliato `ruff`, installato solo per lo sviluppo, che segnala errori ed è veloce; oppure nessuno strumento, solo i test.

## Tecnologia

- [ ] **D5 — Piano B se una libreria non funziona con Python 3.14**: passare tutti alla 3.13 (consigliato), oppure cercare una libreria alternativa.

## Dati

- [ ] **D6 — Cosa succede alle partite quando un utente cancella l'account**: a) si **anonimizzano** (la partita resta per le statistiche degli altri, il nome diventa "utente eliminato") *(consigliata)*; b) si cancellano anche le sue righe nelle partite.
- [ ] **D7 — Regole per lo username**: consigliato da 3 a 20 caratteri, solo lettere, numeri e `_`, e senza distinzione tra maiuscole e minuscole (`Mario` e `mario` sono lo stesso utente).
- [ ] **D8 — Regole per la password**: consigliato almeno 8 caratteri, senza altri obblighi.
- [ ] **D9 — Rating iniziale e visibilità**: consigliato 1500, mostrato come "provvisorio" per le prime 10 partite.
- [ ] **D10 — Per quanti giorni tenere i backup**: consigliato 14 giorni.

## Gioco

- [ ] **D11 — Chi fa il mazziere e chi gioca per primo**: consigliato mazziere a caso nella prima mano, poi a rotazione verso destra, e gioca per primo il giocatore alla destra del mazziere.
- [ ] **D12 — Quale carta gioca il server quando scadono i 30 secondi**: consigliata la carta di valore più basso, senza cantare.
- [ ] **D13 — Abbandono nel 2v2**: consigliato che perda tutta la squadra, con penalità sul rating solo per chi ha abbandonato; oppure penalità per tutta la squadra.
- [ ] **D14 — Stesso utente in due schede o dispositivi**: consigliato che l'ultima scheda aperta prenda il posto della precedente, che mostra "partita aperta altrove"; oppure la seconda scheda viene bloccata.
- [ ] **D15 — Per quanto tempo si mostrano le carte del canto** agli avversari: consigliati 3 secondi, più un'icona fissa accanto al giocatore per tutta la mano.
- [ ] **D16 — Tolleranza del matchmaking**: consigliato di partire con ±100 punti di rating, allargare di +50 ogni 10 secondi, fino a ±400. Dopo 2 minuti si accetta qualunque avversario.
- [ ] **D17 — Formazione delle squadre nella coda 2v2**: consigliato di unire i 4 giocatori in modo che le medie delle due squadre siano il più vicine possibile.
- [ ] **D34 — Nome mostrato nell'interfaccia**: nel prototipo approvato la navbar dice **"Briscola"** (richiesta dell'utente), ma il gioco e il regolamento sono quelli del **Cinquecento**. Quale nome va nelle pagine vere, nel titolo della scheda del browser e nel logo (P42)? Consigliato: il nome del gioco che si gioca davvero.
- [ ] **D35 — Punteggio per vincere e matchmaking**: con la scelta 150 / 300 / 500 nel modal, la coda va divisa per modalità **e** per punteggio (chi sceglie 150 incontra solo chi ha scelto 150) *(consigliato)*, oppure il punteggio lo sceglie il server? E il rating conta allo stesso modo per una partita a 150 e una a 500? Consigliato: code separate per punteggio, rating uguale per tutti i punteggi.
- [ ] **D36 — Il 2v2 con un amico conta per il rating?** L'amico è il compagno e gli avversari arrivano dal matchmaking. Oggi vale la decisione "le partite nate da un invito non contano". Consigliato: **sì, conta**, perché gli avversari sono sconosciuti trovati dalla coda; il 1v1 contro un amico invece non conta.

## Amici e chat

- [ ] **D23 — Blocco degli utenti**: consigliato **sì**. Un utente bloccato non può mandarti richieste né messaggi, e il blocco rimuove l'amicizia. Serve saperlo **prima di P5**, perché cambia le tabelle.
- [ ] **D24 — Per quanto tempo si conservano i messaggi della chat**: consigliati 30 giorni. Si cancellano comunque con l'account. Serve **prima di P5**.
- [ ] **D25 — Con chi si chatta**: consigliato **solo tra amici**, uno a uno, senza chat durante la partita.
- [ ] **D26 — Limiti**: consigliati al massimo 100 amici, messaggi di 300 caratteri al massimo, non più di 1 messaggio al secondo.
- [ ] **D27 — Inviti a partita**: consigliata una scadenza di 60 secondi. Dal prototipo approvato il 27/09/2026: nel 1v1 l'amico invitato è l'avversario; nel 2v2 è il **compagno di squadra** e gli avversari arrivano dal matchmaking. Si invita un amico alla volta. Resta da decidere cosa succede se l'amico rifiuta o non risponde (consigliato: l'invito scade, compare un avviso e si può invitare un altro amico).
- [ ] **D33 — Ricerca di un utente per mandargli la richiesta**: consigliato **username esatto** (protegge la privacy ed evita lo spam); oppure ricerca per parte del nome.

## Interfaccia

- [ ] **D18 — Colore del tavolo di gioco**: colori e stile delle pagine vengono dal prototipo scritto da Claude (P52, stile siciliano, tema chiaro e scuro). Resta da decidere il tavolo, che il prototipo non comprende: consigliato il verde classico, accostato alla palette del prototipo, con una versione per il tema scuro.
- [ ] **D19 — Immagini delle carte**: da dove vengono le vostre immagini e con che licenza? Serve saperlo per usarle nella versione finale (punto P35).
- [ ] **D29 — Set di avatar**: quanti e con che soggetti? Consigliati 12 (i 4 semi e le 8 figure siciliane: Re, Cavallo e Fante di alcuni semi), in formato SVG. Chi li disegna, o da dove si prendono, e con che licenza?
- [ ] **D37 — Dove mostrare i crediti delle immagini delle carte**: le carte dello sfondo (scansioni di Matsoftware su Wikimedia) hanno licenza **CC BY-SA 3.0**, che obbliga a citare autore e licenza in modo visibile. Prima era prevista la pagina Regole, che non c'è più. Opzioni: a) una riga piccola in fondo al pannello statistiche, sotto Impostazioni ed Esci *(consigliata)*; b) una pagina "Crediti" raggiungibile dalle impostazioni; c) sostituire le immagini con altre di pubblico dominio.

## Tempi

- [ ] **D31 — Ordine di taglio se il tempo non basta**: proposto in `SCALETTA.md`, sezione 5 (avatar e logo → carte vere → chat → matchmaking 2v2 → rifinitura mobile). Va bene, o preferite un altro ordine?

## Messa in servizio

- [ ] **D20 — Quale PC ospita la demo** e come si collegano gli altri: stessa rete Wi-Fi (consigliato), oppure un tunnel come ngrok (richiede un account gratuito).
- [ ] **D21 — Dopo la consegna**: VPS o hosting gestito (Render o Railway), come spiegato il 26/09/2026.
