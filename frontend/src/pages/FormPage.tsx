/**
 * La cornice delle pagine con un modulo (accesso e registrazione): la navbar, il
 * <main class="page page--form"> e i messaggi in basso.
 *
 * Cosa contiene:
 *   <FormPage name="login" title="Accedi · Cinquecento" flashes={...}>...</FormPage>
 *   useSessionFlashes()   i messaggi lasciati da un'altra pagina (flash del server)
 *
 * DA DOVE ARRIVANO I DATI: i messaggi da GET /api/auth/session (api/client.ts);
 * il contenuto dalla pagina che usa la cornice.
 */

import { useEffect, useState } from 'react';
import type { JSX, ReactNode } from 'react';
import { loadSession } from '../api/client';
import { FlashList } from '../components/FlashList';
import { Navbar } from '../components/Navbar';
import type { Flash } from '../types/api';

// flashesTaken: true quando una pagina ha già preso i messaggi della sessione.
// Variabile del modulo: vale per tutta la scheda, così passando da Accedi a
// Registrati con il link (senza ricaricare) i messaggi non ricompaiono.
let flashesTaken = false;

// FormPageProps: cosa riceve il componente
interface FormPageProps {
  // il nome della pagina, in data-page di <main> ('login', 'register')
  name: string;
  // il titolo della scheda del browser
  title: string;
  // i messaggi da mostrare in basso
  flashes: Flash[];
  // il contenuto della pagina: quello scritto tra <FormPage> e </FormPage>.
  // ReactNode è "qualunque cosa React sappia disegnare" (elementi, testo, null)
  children: ReactNode;
}

/**
 * La cornice.
 *
 * @param {FormPageProps} props
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <FormPage ...>contenuto</FormPage>
 *   Disegna navbar, <main class="page page--form"> con il contenuto e i
 *   messaggi; quando compare cambia il titolo della scheda.
 */
export function FormPage(props: FormPageProps): JSX.Element {
  /** Effetto: il titolo della scheda. */
  function setTitle(): void {
    document.title = props.title;
  }

  // [props.title]: si rifà solo se il titolo cambia
  useEffect(setTitle, [props.title]);

  // <> ... </>: un contenitore che non diventa un elemento della pagina
  return (
    <>
      <Navbar />
      <main className="page page--form" data-page={props.name}>
        {props.children}
      </main>
      <FlashList flashes={props.flashes} />
    </>
  );
}

/**
 * I messaggi lasciati da un'altra pagina, letti una volta all'apertura.
 *
 * @returns {[Flash[], (flashes: Flash[]) => void]} i messaggi e la funzione per cambiarli
 *
 * In parole semplici:
 *   const [flashes, setFlashes] = useSessionFlashes();
 *   All'inizio non c'è niente; appena arriva la risposta di GET /api/auth/session
 *   ci sono i suoi messaggi (per esempio "Account cancellato."). La pagina può
 *   poi metterne altri con setFlashes (per esempio l'errore del login).
 *   Restituisce le due cose di useState, nella stessa forma.
 */
export function useSessionFlashes(): [Flash[], (flashes: Flash[]) => void] {
  // useState restituisce due cose: il valore attuale e la funzione per cambiarlo,
  // che fa ridisegnare il componente (regole-codice.md, sezione 6)
  const [flashes, setFlashes] = useState<Flash[]>([]);

  /** Effetto: chiede la sessione e ne prende i messaggi. */
  function readFlashes(): () => void {
    // active: false se il componente sparisce prima che arrivi la risposta
    let active = true;

    async function read(): Promise<void> {
      const answer = await loadSession();
      if (!active || flashesTaken || !answer.ok) {
        return;
      }
      flashesTaken = true;
      setFlashes(answer.data.flashes);
    }

    function stop(): void {
      active = false;
    }

    read();
    return stop;
  }

  // []: una volta sola, all'apertura della pagina
  useEffect(readFlashes, []);
  return [flashes, setFlashes];
}
