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

## Interfaccia

- [ ] **D40 — Font delle icone più leggero** (emerso con P22, 28/09/2026): il font delle icone (Material Symbols Rounded con tutti gli assi, da `base.html`) pesa **5,4 MB** e sulla connessione del PC di Christian ci mette 20–45 secondi ad arrivare la prima volta; finché non arriva le icone non si vedono. Proposta: caricare da Google Fonts solo le icone che usiamo (parametro `icon_names`) e fissare gli assi; il file diventa di poche decine di KB. Tocca `base.html` e l'elenco delle risorse in `docs/prototipo/LEGGIMI.md`, e va rifatto quando si aggiunge un'icona (lo può controllare un test). Farlo come punto nuovo di Christian?
- [ ] **D42 — Conversazioni con gli ex amici** (emersa con P48, 28/09/2026): il contratto dice che dopo la fine dell'amicizia o un blocco la conversazione "resta visibile", ma il pannello apre la chat solo dalla lista degli amici: un ex amico non c'è più, quindi la conversazione si vede solo se era già aperta. Serve un posto nel pannello per le conversazioni con chi non è più amico? Se sì, è un punto nuovo di Christian.
- [ ] **D29 — Set di avatar**: deciso il 28/09/2026 che sono 12 in SVG, con i 4 semi e 8 figure siciliane; le figure le ha fissate P17 (codici in `app/services/avatars.py`, vedi `DECISIONI.md`). Restano aperti: chi disegna le immagini o da dove si prendono, e con che licenza (serve a P43).

## Contratto

- [ ] **D41 — `cannot_write` in `chat:history`** (proposta di Giuseppe in P48, 28/09/2026, già nel codice): la risposta di `chat:history` ha anche `cannot_write`: `null` se si può scrivere, altrimenti `"not_friends"` o `"blocked"`, così la pagina può dire "Bloccato" e non solo che non si può scrivere. È un campo in più (chi non lo legge non si rompe), ma cambia il contratto 5.4: serve l'ok dei tre, poi chi è di turno lo scrive nel contratto.

## Tempi

- [ ] **D31 — Ordine di taglio se il tempo non basta**: proposto in `SCALETTA.md`, sezione 5 (tema scuro → frasi del tavolo → avatar e logo → carte vere → chat → matchmaking 2v2 → rifinitura mobile; non si tagliano mai P6, P15, P24, P31 e P32). Va bene, o preferite un altro ordine?

## Messa in servizio

- [ ] **D20 — Quale PC ospita la demo** e come si collegano gli altri: stessa rete Wi-Fi (consigliato), oppure un tunnel come ngrok (richiede un account gratuito; il passo 11 di `docs/DEMO.md` vale solo per la stessa rete). E **da quale branch si installa** la demo: `dev` finché `main` non viene aggiornato (portare `dev` in `main` lo decide il gruppo). In `docs/DEMO.md` ci sono i segnaposti da riempire; blocca il resto di P38 e P39 (Giuseppe).
- [ ] **D21 — Dopo la consegna**: VPS o hosting gestito (Render o Railway), come spiegato il 26/09/2026.
