# Da decidere

Domande ancora aperte, per l'utente o per il gruppo. Quando una è decisa: spuntala, spostala in `DECISIONI.md` con data e motivo, e cancellala da qui.
I punti di `SCALETTA.md` che dipendono da una domanda la richiamano con il suo codice (D1, D2, …).
Per D8 e D10, `config.py` (P4) usa già il valore consigliato, con il commento "provvisorio, Dn": se la decisione è diversa, si cambia solo quel numero.

## Processo e gruppo

- [ ] **D1 — Data esatta di consegna** e cosa va consegnato (codice, dimostrazione dal vivo, relazione?).

## Tecnologia

- [ ] **D5 — Piano B se una libreria non funziona con Python 3.14**: passare tutti alla 3.13 (consigliato), oppure cercare una libreria alternativa.

## Dati

- [ ] **D8 — Regole per la password**: consigliato almeno 8 caratteri, senza altri obblighi.
- [ ] **D10 — Per quanti giorni tenere i backup**: consigliato 14 giorni.

## Gioco

- [ ] **D17 — Formazione delle squadre nella coda 2v2**: consigliato di unire i 4 giocatori in modo che le medie delle due squadre siano il più vicine possibile.

## Interfaccia

- [ ] **D18 — Colore del tavolo di gioco**: colori e stile delle pagine vengono dal prototipo scritto da Claude (P52, stile siciliano; per ora solo tema chiaro, il tema scuro è P53). Resta da decidere il tavolo, che il prototipo non comprende: consigliato il verde classico, accostato alla palette del prototipo, con una versione per il tema scuro quando arriva P53.
- [ ] **D19 — Immagini delle carte**: da dove vengono le vostre immagini e con che licenza? Serve saperlo per usarle nella versione finale (punto P35).
- [ ] **D29 — Set di avatar**: deciso il 28/09/2026 che sono 12 in SVG, con i 4 semi e 8 figure siciliane (vedi `DECISIONI.md`). Restano aperti: quali 8 figure (Re, Cavallo e Fante di quali semi), chi li disegna o da dove si prendono, e con che licenza.
- [ ] **D39 — Crediti delle immagini per chi non ha fatto il login**: la riga "Immagini delle carte: Matsoftware, CC BY-SA 3.0…" sta nel pannello statistiche (D37), che si apre solo con il login, ma le carte si vedono già nel logo della navbar (e con P22 nella home). Consigliato aggiungere la stessa riga, piccola, in fondo alla finestra "Accedi o registrati" (P40), così è visibile a tutti.

## Tempi

- [ ] **D31 — Ordine di taglio se il tempo non basta**: proposto in `SCALETTA.md`, sezione 5 (tema scuro → frasi del tavolo → avatar e logo → carte vere → chat → matchmaking 2v2 → rifinitura mobile; non si tagliano mai P6, P15, P24, P31 e P32). Va bene, o preferite un altro ordine?

## Messa in servizio

- [ ] **D20 — Quale PC ospita la demo** e come si collegano gli altri: stessa rete Wi-Fi (consigliato), oppure un tunnel come ngrok (richiede un account gratuito).
- [ ] **D21 — Dopo la consegna**: VPS o hosting gestito (Render o Railway), come spiegato il 26/09/2026.
