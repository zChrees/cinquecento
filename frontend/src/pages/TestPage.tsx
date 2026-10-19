/**
 * Pagina di prova della SPA (passi 1 e 3 della migrazione): serve solo a vedere
 * che React, il router, il build, Flask e il tempo reale funzionano insieme.
 * Esiste solo in sviluppo e nei test (con APP_ENV=demo Flask risponde 404) e si
 * toglie con la prima pagina vera (passo 4).
 *
 * Cosa contiene:
 *   <TestPage />   un pulsante che conta i clic (passo 1); lo stato della
 *                  connessione, i giocatori online e un pulsante che manda un
 *                  evento al server (passo 3)
 *
 * DA DOVE ARRIVANO I DATI: il numero di clic lo tiene React (useState); lo stato
 * della connessione e i giocatori online arrivano dal server (useConnection e
 * home:status, che il server manda appena la scheda si collega, contratto 5.1).
 */

import { useState } from 'react';
import type { JSX } from 'react';
import { send } from '../socket/client';
import type { ConnectionStatus } from '../socket/client';
import { useConnection, useSocketEvent } from '../socket/hooks';
import type { HomeStatus } from '../types/events';

// STATUS_TEXT: il testo da mostrare per ogni stato della connessione.
// Record<A, B> è "un oggetto con una chiave per ogni valore di A, e valori di
// tipo B": se manca uno stato, TypeScript lo segnala.
const STATUS_TEXT: Record<ConnectionStatus, string> = {
  connecting: 'Collegamento in corso…',
  connected: 'Collegato',
  disconnected: 'Scollegato',
  not_logged_in: 'Non hai fatto il login',
};

/**
 * La pagina di prova.
 *
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <TestPage />
 *   Disegna il titolo, il contatore dei clic e la parte del tempo reale. Ogni
 *   volta che cambia uno stato (clic, connessione, online, risposta) React
 *   ridisegna solo i pezzi cambiati. Lo usa routes.tsx per l'indirizzo /prova-react.
 *
 *   JSX.Element: il tipo di quello che restituisce un componente, cioè un pezzo
 *   di pagina descritto con le righe <main>...</main>.
 */
export function TestPage(): JSX.Element {
  // useState restituisce due cose: il valore attuale e la funzione per
  // cambiarlo, che fa ridisegnare il componente. È l'unica destrutturazione
  // ammessa (regole-codice.md, sezione 6). Gli hook (useState, useConnection,
  // useSocketEvent) si chiamano sempre in cima al componente, mai dentro un if.
  // clicks: quante volte è stato premuto "Premi"
  const [clicks, setClicks] = useState<number>(0);
  // online: i giocatori online di home:status; null finché non arriva
  const [online, setOnline] = useState<number | null>(null);
  // answer: il testo della risposta all'ultimo "Manda queue:leave"; '' all'inizio
  const [answer, setAnswer] = useState<string>('');
  // sending: true mentre si aspetta la risposta (il pulsante resta spento)
  const [sending, setSending] = useState<boolean>(false);
  // status: lo stato della connessione, per esempio 'connected'
  const status = useConnection();

  /** Arriva home:status: salva il numero di giocatori online. */
  function handleHomeStatus(data: HomeStatus): void {
    setOnline(data.online_count);
  }

  useSocketEvent('home:status', handleHomeStatus);

  /** Clic su "Premi": aumenta il contatore. */
  function handleClick(): void {
    setClicks(clicks + 1);
  }

  /**
   * Clic su "Manda queue:leave": manda l'evento (lasciare la coda, che va bene
   * anche se non si è in coda, contratto 4) e mostra se il server ha risposto
   * "fatto". async: la funzione può usare await, cioè aspettare la risposta
   * senza bloccare la pagina.
   */
  async function handleSend(): Promise<void> {
    setSending(true);
    const result = await send('queue:leave', {});
    if (result.ok) {
      setAnswer('Il server ha risposto: ok');
    } else {
      setAnswer(`Il server ha risposto con un errore: ${result.error.message}`);
    }
    setSending(false);
  }

  // message: la frase del contatore, decisa con un if prima del return
  let message = 'Non hai ancora premuto il pulsante.';
  if (clicks === 1) {
    message = 'Hai premuto il pulsante una volta.';
  } else if (clicks > 1) {
    message = `Hai premuto il pulsante ${clicks} volte.`;
  }

  // onlineText: i giocatori online, o un trattino finché non arriva home:status
  let onlineText = '–';
  if (online !== null) {
    onlineText = String(online);
  }

  // sendDisabled: il pulsante è spento senza connessione e mentre si aspetta
  // la risposta (niente doppio clic, CLAUDE.md "Azioni ripetibili")
  let sendDisabled = false;
  if (status !== 'connected' || sending) {
    sendDisabled = true;
  }

  // data-spa-*: attributi stabili per i test (come i data-* del frontend di oggi)
  return (
    <main data-spa-test="">
      <h1>Prova React</h1>
      <p data-spa-message="">{message}</p>
      <button type="button" onClick={handleClick} data-spa-button="">Premi</button>

      <h2>Tempo reale</h2>
      <p>
        Connessione: <span data-spa-connection={status}>{STATUS_TEXT[status]}</span>
      </p>
      <p>
        Giocatori online: <span data-spa-online="">{onlineText}</span>
      </p>
      <button type="button" onClick={handleSend} disabled={sendDisabled} data-spa-send="">
        Manda queue:leave
      </button>
      <p data-spa-answer="">{answer}</p>

      <p>
        <a href="/">Torna alla home</a> (è una pagina Jinja: si ricarica)
      </p>
    </main>
  );
}
