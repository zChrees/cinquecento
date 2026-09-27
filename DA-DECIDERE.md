# Da decidere

Domande ancora aperte, per l'utente o per il gruppo. Quando una è decisa: spuntala, spostala in `DECISIONI.md` con data e motivo, e cancellala da qui.
I punti di `SCALETTA.md` che dipendono da una domanda la richiamano con il suo codice (D1, D2, …).
Per D7, D8, D9, D10, D16, D24, D26 e D27, `config.py` (P4) usa già il valore consigliato, con il commento "provvisorio, Dn": se la decisione è diversa, si cambia solo quel numero.

## Processo e gruppo

- [ ] **D1 — Data esatta di consegna** e cosa va consegnato (codice, dimostrazione dal vivo, relazione?).

## Tecnologia

- [ ] **D5 — Piano B se una libreria non funziona con Python 3.14**: passare tutti alla 3.13 (consigliato), oppure cercare una libreria alternativa.

## Dati

- [ ] **D8 — Regole per la password**: consigliato almeno 8 caratteri, senza altri obblighi.
- [ ] **D9 — Rating iniziale e visibilità**: consigliato 1500, mostrato come "provvisorio" per le prime 10 partite.
- [ ] **D10 — Per quanti giorni tenere i backup**: consigliato 14 giorni.

## Gioco

- [ ] **D13 — Abbandono nel 2v2**: consigliato che perda tutta la squadra, con penalità sul rating solo per chi ha abbandonato; oppure penalità per tutta la squadra.
- [ ] **D14 — Stesso utente in due schede o dispositivi**: consigliato che l'ultima scheda aperta prenda il posto della precedente, che mostra "partita aperta altrove"; oppure la seconda scheda viene bloccata.
- [ ] **D15 — Per quanto tempo si mostrano le carte del canto** agli avversari: consigliati 3 secondi, più un'icona fissa accanto al giocatore per tutta la mano.
- [ ] **D16 — Tolleranza del matchmaking**: consigliato di partire con ±100 punti di rating, allargare di +50 ogni 10 secondi, fino a ±400. Dopo 2 minuti si accetta qualunque avversario.
- [ ] **D17 — Formazione delle squadre nella coda 2v2**: consigliato di unire i 4 giocatori in modo che le medie delle due squadre siano il più vicine possibile.

## Amici e chat

- [ ] **D25 — Con chi si chatta**: consigliato **solo tra amici**, uno a uno, senza chat durante la partita. → **Aggiornamento del 27/09/2026**: al tavolo c'è la chat con le **frasi pronte** (D24), per tutti i giocatori della partita; la chat a testo libero resta solo tra amici.
- [ ] **D26 — Limiti**: consigliati al massimo 100 amici e non più di 1 messaggio al secondo. La lunghezza dei messaggi è decisa il 27/09/2026: al massimo 1000 caratteri (vedi `DECISIONI.md`).
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
