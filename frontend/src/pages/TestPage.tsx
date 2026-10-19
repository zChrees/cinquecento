/**
 * Pagina di prova della SPA (passo 1 della migrazione): serve solo a vedere che
 * React, il router, il build e Flask funzionano insieme. Esiste solo in
 * sviluppo e nei test (con APP_ENV=demo Flask risponde 404) e si toglie con la
 * prima pagina vera (passo 4).
 *
 * Cosa contiene:
 *   <TestPage />   un titolo, un pulsante che conta i clic e un link alla home
 *
 * DA DOVE ARRIVANO I DATI: da nessuna parte, la pagina non parla con il server;
 * il numero di clic lo tiene React (useState).
 */

import { useState } from 'react';
import type { JSX } from 'react';

/**
 * La pagina di prova.
 *
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <TestPage />
 *   Disegna il titolo, una frase con il numero di clic e il pulsante "Premi".
 *   Ogni clic aumenta il numero e React ridisegna solo la frase.
 *   Lo usa routes.tsx per l'indirizzo /prova-react.
 *
 *   JSX.Element: il tipo di quello che restituisce un componente, cioè un pezzo
 *   di pagina descritto con le righe <main>...</main>.
 */
export function TestPage(): JSX.Element {
  // useState restituisce due cose: il valore attuale (clicks, all'inizio 0) e la
  // funzione per cambiarlo (setClicks), che fa ridisegnare il componente.
  // È l'unica destrutturazione ammessa (regole-codice.md, sezione 6). Gli hook
  // come useState si chiamano sempre in cima al componente, mai dentro un if.
  const [clicks, setClicks] = useState<number>(0);

  /**
   * Gestore del clic sul pulsante.
   *
   * In parole semplici:
   *   handleClick()
   *   Aumenta di uno il numero di clic. React lo chiama quando premi "Premi".
   */
  function handleClick(): void {
    setClicks(clicks + 1);
  }

  // message: la frase sotto il titolo, decisa con un if prima del return
  let message = 'Non hai ancora premuto il pulsante.';
  if (clicks === 1) {
    message = 'Hai premuto il pulsante una volta.';
  } else if (clicks > 1) {
    message = `Hai premuto il pulsante ${clicks} volte.`;
  }

  // data-spa-*: attributi stabili per i test (come i data-* del frontend di oggi)
  return (
    <main data-spa-test="">
      <h1>Prova React</h1>
      <p data-spa-message="">{message}</p>
      <button type="button" onClick={handleClick} data-spa-button="">Premi</button>
      <p>
        <a href="/">Torna alla home</a> (è una pagina Jinja: si ricarica)
      </p>
    </main>
  );
}
