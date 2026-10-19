/**
 * Punto di partenza della SPA: avvia React dentro <div id="root"> di index.html.
 *
 * Cosa contiene:
 *   start()   cerca il <div id="root"> e ci disegna il router (routes.tsx)
 *
 * DA DOVE ARRIVANO I DATI (la catena delle chiamate):
 *
 *   1. il browser apre una pagina della SPA (per esempio /prova-react);
 *   2. index.html carica questo file (<script type="module" src="/src/main.tsx">);
 *   3. start() passa il router di routes.tsx a React, che guarda l'indirizzo e
 *      disegna la pagina giusta; intorno c'è SessionProvider, che chiede al server
 *      chi è collegato (session/SessionContext.tsx).
 */

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { RouterProvider } from 'react-router';
import { router } from './routes';
import { SessionProvider } from './session/SessionContext';

/**
 * Avvia React.
 *
 * @returns {void}
 *
 * In parole semplici:
 *   start()
 *   Trova il <div id="root"> e ci mette dentro il router. Se il <div> manca,
 *   si ferma con un errore chiaro invece di lasciare la pagina bianca.
 *
 *   StrictMode: in sviluppo React esegue due volte alcune parti apposta, per
 *   scoprire gli effetti che non si fermano bene (rischio 3 del piano). Dopo il
 *   build non fa niente.
 */
function start(): void {
  // container: il <div id="root"> di index.html; null se non c'è
  const container: HTMLElement | null = document.getElementById('root');
  if (container === null) {
    throw new Error('Manca <div id="root"> in index.html.');
  }

  const root = createRoot(container);
  root.render(
    <StrictMode>
      <SessionProvider>
        <RouterProvider router={router} />
      </SessionProvider>
    </StrictMode>,
  );
}

start();
