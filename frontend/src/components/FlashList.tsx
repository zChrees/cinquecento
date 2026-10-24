/**
 * I messaggi in basso (P19; stile in app/static/css/base/layout.css: compaiono in
 * basso e spariscono da soli).
 *
 * Cosa contiene:
 *   <FlashList flashes={[{ kind: 'error', message: 'Credenziali non valide.' }]} />
 *
 * DA DOVE ARRIVANO I DATI: dalla sessione (loadSession: i messaggi lasciati da
 * un'altra pagina con flash()) e dalle pagine stesse (per esempio l'errore del login).
 */

import type { JSX } from 'react';
import type { Flash, FlashKind } from '../types/api';

// ICONS: l'icona di ogni tipo di messaggio (come in flash.html)
const ICONS: Record<FlashKind, string> = {
  success: 'check_circle',
  error: 'error',
  info: 'info',
};

// FlashListProps: cosa riceve il componente
interface FlashListProps {
  // i messaggi da mostrare, dal più vecchio al più nuovo; vuoto = niente
  flashes: Flash[];
}

/**
 * La lista dei messaggi.
 *
 * @param {FlashListProps} props
 * @returns {JSX.Element | null}
 *
 * In parole semplici:
 *   <FlashList flashes={flashes} />
 *   Senza messaggi non disegna niente (null). Un errore ha role="alert" (il
 *   lettore di schermo lo legge subito), gli altri role="status".
 */
export function FlashList(props: FlashListProps): JSX.Element | null {
  if (props.flashes.length === 0) {
    return null;
  }

  // items: un <p> per messaggio. key: il "nome" con cui React riconosce lo stesso
  // messaggio tra un disegno e l'altro (qui la posizione e il testo insieme: lo
  // stesso testo può arrivare due volte)
  const items: JSX.Element[] = [];
  for (let i = 0; i < props.flashes.length; i++) {
    const flash = props.flashes[i];
    let role = 'status';
    if (flash.kind === 'error') {
      role = 'alert';
    }
    items.push(
      <p key={`${i}-${flash.message}`} className={`flash flash--${flash.kind}`} role={role} data-flash-kind={flash.kind}>
        <span className="icon" aria-hidden="true">{ICONS[flash.kind]}</span>
        <span>{flash.message}</span>
      </p>,
    );
  }

  return <div className="flash-list" data-flash="">{items}</div>;
}
