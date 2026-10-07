# Da decidere

Domande ancora aperte, per l'utente o per il gruppo. Quando una è decisa: spuntala, spostala in `DECISIONI.md` con data e motivo, e cancellala da qui.
I punti di `SCALETTA.md` che dipendono da una domanda la richiamano con il suo codice (D1, D2, …).
Il 29/09/2026 sono state chiuse D5, D8, D10, D20, D29, D40, D41 e D42; il 30/09/2026 D44; il 04/10/2026 D43, D45 e D46; il 05/10/2026 D47; il 07/10/2026 D48 (vedi `DECISIONI.md`).

## Processo e gruppo

- [ ] **D1 — Data esatta di consegna**. Cosa si consegna è deciso il 29/09/2026 (repository, dimostrazione dal vivo e relazione scritta, da scrivere alla fine: `DECISIONI.md`, Progetto e tempi); manca solo il giorno esatto. **01/10/2026**: la consegna intorno al 03/10 è stata **spostata**; la nuova data non è ancora fissata.
- [ ] **D49 — Contratto di `cpu:start` per il 2v2** (P122, P123; decisione in `DECISIONI.md`, Gioco, 07/10/2026). Proposta di Claude, approvata da Christian il 07/10/2026: (1) `cpu:start` riceve `{"request_id", "target_score", "mode"}`, con `mode` **obbligatorio**, `"1v1"` o `"2v2"`, controllato come in `queue:join`; un valore mancante o diverso si rifiuta con un messaggio chiaro; (2) i nomi **"CPU 1"** (compagna), **"CPU 2"**, **"CPU 3"** li decide il server, nel campo `username` dei giocatori della vista (nel 1v1 resta "CPU"); (3) `game:advise` quando il compagno è una CPU si **rifiuta** con un messaggio (per esempio "La CPU non riceve consigli."). Oggi la home non manda `mode` e il server ignora i campi in più [L]: per non rompere la CPU del 1v1, P123 (che manda `mode`) va in `dev` prima o insieme a P122. Manca l'**ok di Giuseppe**, che può cambiare nomi e forme come in P68; P122 e P123 partono dopo. Aperta il 07/10/2026.

## Tempi

- [ ] **D31 — Ordine di taglio se il tempo non basta**: proposto in `SCALETTA.md`, sezione 5 (tema scuro → frasi del tavolo → avatar e logo → carte vere → chat → matchmaking 2v2 → rifinitura mobile; non si tagliano mai P6, P15, P24, P31 e P32). Lasciata aperta da Christian il 29/09/2026. Di quella lista sono già fatti frasi del tavolo, logo, carte vere, chat e matchmaking 2v2: restano da tagliare, eventualmente, P53 (tema scuro), P43 (avatar), P59 (2v2 con più amici) e P34 (rifinitura mobile). **29/09/2026**: la prova sul telefono ha aggiunto P63–P73; i punti che si possono tagliare sono soprattutto la CPU (P68, P73, il più grande) e le animazioni (P70): va rivista la lista con la scadenza (D1). **01/10/2026**: P53 è tolto (30/09), P43, P59 e P70 sono fatti, P34 manca solo della prova sul telefono; resta da tagliare, eventualmente, la **CPU** (P68 da rifare, P73).

## Messa in servizio

- [ ] **D21 — Dopo la consegna**: VPS o hosting gestito (Render o Railway), come spiegato il 26/09/2026. Lasciata aperta da Christian il 29/09/2026: è per un futuro lontano.
