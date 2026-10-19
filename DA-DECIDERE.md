# Da decidere

Domande ancora aperte, per l'utente o per il gruppo. Quando una è decisa: spuntala, spostala in `DECISIONI.md` con data e motivo, e cancellala da qui.
I punti del tracker (`REVIEW.md`; prima la scaletta, ora in `docs/archivio/SCALETTA-2026-09.md`) che dipendono da una domanda la richiamano con il suo codice (D1, D2, …).
Il 29/09/2026 sono state chiuse D5, D8, D10, D20, D29, D40, D41 e D42; il 30/09/2026 D44; il 04/10/2026 D43, D45 e D46; il 05/10/2026 D47; il 07/10/2026 D48; l'08/10/2026 D49, D1 (consegna il 12/10) e D31; il 10/10/2026 D50 e D51, aperta e chiusa lo stesso giorno (vedi `DECISIONI.md`).

## Messa in servizio

- [ ] **D21 — Dopo la consegna**: VPS o hosting gestito (Render o Railway), come spiegato il 26/09/2026. Lasciata aperta da Christian il 29/09/2026: è per un futuro lontano.

## Codice commentato (regole-codice.md)

- [ ] **D52 — Dove mettere `hasValue`**: la funzione che dice se un valore non è né `null` né `undefined` (al posto di `x != null`, regole-codice.md sezione 5) oggi sta solo in `app/static/js/components/Hand.js`. Servirà in molti file JS: proposta di spostarla in `app/static/js/utils/dom.js` e importarla da lì, invece di ricopiarla in ogni file. Lasciata aperta da Christian il 19/10/2026.
- [ ] **D53 — Togliere `HiddenHand`**: la funzione di `Hand.js` che disegna una fila di carte coperte non la chiama nessun file del progetto (al tavolo gli avversari usano `EdgeHand`); per ora è segnalata nel suo commento. Proposta: toglierla. Lasciata aperta da Christian il 19/10/2026.
