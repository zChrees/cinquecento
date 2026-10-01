# Da decidere

Domande ancora aperte, per l'utente o per il gruppo. Quando una è decisa: spuntala, spostala in `DECISIONI.md` con data e motivo, e cancellala da qui.
I punti di `SCALETTA.md` che dipendono da una domanda la richiamano con il suo codice (D1, D2, …).
Il 29/09/2026 sono state chiuse D5, D8, D10, D20, D29, D40, D41 e D42; il 30/09/2026 D44 (vedi `DECISIONI.md`).

## Processo e gruppo

- [ ] **D1 — Data esatta di consegna**. Cosa si consegna è deciso il 29/09/2026 (repository, dimostrazione dal vivo e relazione scritta, da scrivere alla fine: `DECISIONI.md`, Progetto e tempi); manca solo il giorno esatto.

## Tempi

- [ ] **D31 — Ordine di taglio se il tempo non basta**: proposto in `SCALETTA.md`, sezione 5 (tema scuro → frasi del tavolo → avatar e logo → carte vere → chat → matchmaking 2v2 → rifinitura mobile; non si tagliano mai P6, P15, P24, P31 e P32). Lasciata aperta da Christian il 29/09/2026. Di quella lista sono già fatti frasi del tavolo, logo, carte vere, chat e matchmaking 2v2: restano da tagliare, eventualmente, P53 (tema scuro), P43 (avatar), P59 (2v2 con più amici) e P34 (rifinitura mobile). **29/09/2026**: la prova sul telefono ha aggiunto P63–P73; i punti che si possono tagliare sono soprattutto la CPU (P68, P73, il più grande) e le animazioni (P70): va rivista la lista con la scadenza (D1). **01/10/2026**: P53 è tolto (30/09), P43, P59 e P70 sono fatti, P34 manca solo della prova sul telefono; resta da tagliare, eventualmente, la **CPU** (P68 da rifare, P73).

## Gioco e tavolo

- [ ] **D43 — Partita contro la CPU** (P68, P73): (1) **come sceglie le mosse** la CPU, visto che non devono essere casuali (per esempio: quando prende e quando lascia, quando usa la briscola, quando canta); (2) solo **1v1** o anche **2v2** (CPU come compagno o come avversari); (3) la partita si **salva** e conta per **statistiche e rating**? (4) **dove si avvia** nella home, che non scorre: una carta-pulsante nuova o una scelta dentro quelle che ci sono; (5) nome e avatar della CPU e quanto aspetta prima di giocare. Da decidere insieme (Christian e Giuseppe).
  - **30/09/2026, proposta di Giuseppe** (già in `dev` con P68, riepilogo in `giuseppe.md`): (1) strategia "giocatore medio" (canta appena può; prende senza briscola con la carta più economica; briscola solo per prese da almeno 10 punti; scarta la carta che vale meno; apre basso); (2) solo 1v1; (3) non si salva e non conta; (4) una scelta nella carta-modal; (5) nome "CPU", senza avatar, 1,5 s prima di giocare.
  - **01/10/2026, Christian**: la strategia (1) è **scartata**: contro la CPU si vince troppo facilmente; serve un modo diverso, più forte, di scegliere le mosse, da cercare insieme. I punti (2)–(5) restano proposte da discutere. Per riconoscere la CPU nella vista Christian preferisce un campo **`cpu: true`** per giocatore, se non complica troppo, invece di `user_id` 0. Il contratto di `cpu:start` resta aperto.

## Messa in servizio

- [ ] **D21 — Dopo la consegna**: VPS o hosting gestito (Render o Railway), come spiegato il 26/09/2026. Lasciata aperta da Christian il 29/09/2026: è per un futuro lontano.
