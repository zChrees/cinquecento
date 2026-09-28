# Carte del gioco: autore e licenza

Le 40 carte che si vedono in partita (P35, 28/09/2026), usate da `js/components/Card.js`. Il dorso non è qui: è `img/cards-bg/dorso.webp` (vedi `img/cards-bg/LICENZA.md`).

| File | Cosa | Fonte | Licenza |
|---|---|---|---|
| `<seme>-<valore>.webp` (40 file: `coppe`, `denari`, `spade`, `bastoni`; valore da 1 = Asso a 10 = Re, come i codici del motore) | Carte intere, ritagliate una per una dalle scansioni e portate a 200 × 326 px, WebP qualità 80 | Wikimedia Commons, file `Carte_da_gioco_siciliane_-_<seme>.jpg` (un foglio per seme, con tutte le 10 carte), autore **Matsoftware** | **CC BY-SA 3.0** (<https://creativecommons.org/licenses/by-sa/3.0/deed.it>): si possono usare citando autore e licenza; i ritagli restano sotto la stessa licenza |

Autore e licenza verificati il 28/09/2026 con l'API di Wikimedia Commons (campi `Artist` e `LicenseShortName` di ciascun file). Sono la stessa fonte e la stessa licenza delle carte di `img/cards-bg/`.

**Crediti nel sito** (obbligatori per CC BY-SA 3.0, D37 e D39): la riga "Immagini delle carte: Matsoftware, CC BY-SA 3.0, da Wikimedia Commons", con il collegamento alla licenza, in fondo al pannello statistiche e alla finestra "Accedi o registrati". Vale anche per queste carte: non serve cambiarla.

**Come sono state ritagliate**: per ogni carta un riquadro stimato sulla scansione, corretto cercando entro 25 px la riga più scura (il bordo tra due carte), poi 3 px più all'interno. Le carte della colonna sinistra sono tagliate un po' dal bordo della scansione. Gli angoli arrotondati li fa il CSS (`card.css`), che nasconde gli angoli grigi del fondo dello scanner.
