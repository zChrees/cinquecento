/**
 * Le variabili CSS (--x, --i, --timer-left, ...) dentro style={{ ... }}.
 *
 * TypeScript conosce solo le proprietà vere del CSS (color, width, ...): questo
 * blocco gli dice che in CSSProperties, il tipo di style={{ ... }}, ci possono
 * essere anche nomi che cominciano con "--", con un testo come valore.
 * `--${string}` vuol dire "due trattini e poi qualunque testo". React le scrive
 * con element.style.setProperty, che la CSP permette.
 *
 * Sta in un file a parte perché serve a tutto il frontend, anche al tavolo (--i e --n dei ventagli,
 * --timer-left dell'anello del tempo). Un file .d.ts contiene solo tipi: non
 * produce codice. L'import qui sotto lo rende un "modulo", così "declare module"
 * aggiunge un campo al tipo di React invece di sostituirlo.
 *
 * DA DOVE ARRIVANO I DATI: da nessuna parte; tsc legge questo file insieme agli
 * altri di src/ (tsconfig.json, "include").
 */

import 'react';

declare module 'react' {
  interface CSSProperties {
    [name: `--${string}`]: string;
  }
}
