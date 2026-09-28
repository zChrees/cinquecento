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

- [ ] **D19 — Immagini delle carte**: da dove vengono le vostre immagini e con che licenza? Serve saperlo per usarle nella versione finale (punto P35). Fino ad allora in gioco si vedono le carte segnaposto di P20.
  **Proposta per la fonte (28/09/2026, da verificare)**: le carte già nel progetto (`app/static/img/cards-bg/`: Cavallo, Re, Asso e Tre) sono ritagli delle scansioni di **Matsoftware** su Wikimedia Commons, un foglio per seme (`Carte_da_gioco_siciliane_-_<seme>.jpg`), con licenza **CC BY-SA 3.0**. Probabilmente ogni foglio contiene tutte le 10 carte del seme: in quel caso si ritagliano da lì tutte le 40 carte, con la stessa licenza e la riga dei crediti che c'è già (D37, D39). Da controllare all'inizio di P35, aprendo le quattro scansioni.
- [ ] **D40 — Font delle icone più leggero** (emerso con P22, 28/09/2026): il font delle icone (Material Symbols Rounded con tutti gli assi, da `base.html`) pesa **5,4 MB** e sulla connessione del PC di Christian ci mette 20–45 secondi ad arrivare la prima volta; finché non arriva le icone non si vedono. Proposta: caricare da Google Fonts solo le icone che usiamo (parametro `icon_names`) e fissare gli assi; il file diventa di poche decine di KB. Tocca `base.html` e l'elenco delle risorse in `docs/prototipo/LEGGIMI.md`, e va rifatto quando si aggiunge un'icona (lo può controllare un test). Farlo come punto nuovo di Christian?
- [ ] **D29 — Set di avatar**: deciso il 28/09/2026 che sono 12 in SVG, con i 4 semi e 8 figure siciliane; le figure le ha fissate P17 (codici in `app/services/avatars.py`, vedi `DECISIONI.md`). Restano aperti: chi disegna le immagini o da dove si prendono, e con che licenza (serve a P43).

## Tempi

- [ ] **D31 — Ordine di taglio se il tempo non basta**: proposto in `SCALETTA.md`, sezione 5 (tema scuro → frasi del tavolo → avatar e logo → carte vere → chat → matchmaking 2v2 → rifinitura mobile; non si tagliano mai P6, P15, P24, P31 e P32). Va bene, o preferite un altro ordine?

## Messa in servizio

- [ ] **D20 — Quale PC ospita la demo** e come si collegano gli altri: stessa rete Wi-Fi (consigliato), oppure un tunnel come ngrok (richiede un account gratuito).
- [ ] **D21 — Dopo la consegna**: VPS o hosting gestito (Render o Railway), come spiegato il 26/09/2026.
