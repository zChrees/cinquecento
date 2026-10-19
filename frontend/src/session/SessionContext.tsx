/**
 * Chi è collegato, per tutta la SPA (passo 5 della migrazione): prende il posto
 * di current_user nei template Jinja e degli attributi data-user-* di base.html.
 *
 * Cosa contiene:
 *   <SessionProvider>...</SessionProvider>   chiede la sessione una volta e la passa giù
 *   useSession()                             la sessione, in qualunque componente sotto
 *
 * Per esempio:
 *   const session = useSession();
 *   if (session.loaded && session.user !== null) { ... session.user.username ... }
 *
 * Un "Context" di React è un valore messo a disposizione di tutti i componenti
 * sotto il Provider, senza passarlo a mano di componente in componente (come una
 * variabile globale, ma solo per quel pezzo di pagina, e che fa ridisegnare chi la
 * usa quando cambia).
 *
 * DA DOVE ARRIVANO I DATI: GET /api/auth/session (api/client.ts, loadSession),
 * che dice l'utente collegato oppure null. La stessa risposta dà anche il codice
 * CSRF e i messaggi (FormPage.tsx): la richiesta parte una volta sola.
 */

import { createContext, useContext, useEffect, useState } from 'react';
import type { Context, JSX, ReactNode } from 'react';
import { loadSession } from '../api/client';
import type { UserRef } from '../types/common';

// SessionInfo: quello che sanno i componenti sulla sessione
export interface SessionInfo {
  // false finché non è arrivata la risposta di /api/auth/session
  loaded: boolean;
  // l'utente collegato, oppure null (senza login, o finché non si sa)
  user: UserRef | null;
  // il codice CSRF, per i moduli che la pagina manda da sé (per esempio "Esci"); '' finché non si sa
  csrfToken: string;
}

// NOT_LOADED: la sessione prima della risposta
const NOT_LOADED: SessionInfo = { loaded: false, user: null, csrfToken: '' };

// SessionContext: il "canale" da cui i componenti leggono la sessione
const SessionContext: Context<SessionInfo> = createContext<SessionInfo>(NOT_LOADED);

// SessionProviderProps: cosa riceve il componente
interface SessionProviderProps {
  // tutta la pagina (quello che sta tra <SessionProvider> e </SessionProvider>)
  children: ReactNode;
}

/**
 * Chiede la sessione e la mette a disposizione di tutta la pagina.
 *
 * @param {SessionProviderProps} props
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <SessionProvider><RouterProvider ... /></SessionProvider>   (in main.tsx)
 *   Senza rete, o se il server sbaglia, la sessione resta "senza login" ma
 *   segnata come arrivata: la pagina si mostra lo stesso.
 */
export function SessionProvider(props: SessionProviderProps): JSX.Element {
  // useState restituisce il valore attuale e la funzione per cambiarlo, che fa
  // ridisegnare il componente (regole-codice.md, sezione 6)
  const [session, setSession] = useState<SessionInfo>(NOT_LOADED);

  /** Effetto: chiede la sessione una volta, quando la pagina si apre. */
  function load(): () => void {
    // active: false se il componente sparisce prima della risposta
    let active = true;

    async function read(): Promise<void> {
      const answer = await loadSession();
      if (!active) {
        return;
      }
      if (answer.ok) {
        setSession({ loaded: true, user: answer.data.user, csrfToken: answer.data.csrf_token });
      } else {
        setSession({ loaded: true, user: null, csrfToken: '' });
      }
    }

    function stop(): void {
      active = false;
    }

    read();
    return stop;
  }

  // []: una volta sola
  useEffect(load, []);

  return <SessionContext.Provider value={session}>{props.children}</SessionContext.Provider>;
}

/**
 * La sessione, letta da qualunque componente dentro <SessionProvider>.
 *
 * In parole semplici:
 *   const session = useSession();   →   { loaded, user, csrfToken }
 */
export function useSession(): SessionInfo {
  return useContext(SessionContext);
}
