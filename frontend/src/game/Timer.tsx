/**
 * Il tempo del turno al tavolo React (P21, P132): un anello attorno all'avatar di
 * chi deve giocare, che si svuota e sotto i 10 secondi diventa rosso (stile in
 * css/components/timer.css).
 *
 * Cosa contiene:
 *   <Timer turn={{ seat: 3, seconds_total: 15, seconds_left: 12.5 }} paused={false} />
 *
 * L'anello si muove con un'animazione CSS che parte dai secondi rimasti: niente
 * conteggio in JavaScript. Con paused (il tavolo è in pausa, P132) resta pieno e
 * fermo finché il turno non comincia davvero.
 *
 * DA DOVE ARRIVANO I DATI: dal campo turn della vista; paused lo decide la pagina.
 */

import { useState } from 'react';
import type { CSSProperties, JSX } from 'react';
import type { Turn } from '../types/view';

// TimerProps: cosa riceve l'anello
interface TimerProps {
  // il campo turn della vista: { seat, seconds_total, seconds_left }
  turn: Turn;
  // true se il tavolo è in pausa (P132): l'anello resta fermo
  paused: boolean;
}

/**
 * L'anello del tempo.
 *
 * @param {TimerProps} props
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <Timer turn={view.turn} paused={false} />
 *   Disegna <span class="timer" data-timer data-seconds-left="13" role="timer">.
 *   Le variabili CSS --timer-start (la parte di anello ancora piena, da 0 a 1) e
 *   --timer-left (i secondi che restano) dicono all'animazione da dove partire.
 *   Lo usa Table.tsx, sull'avatar di chi è di turno.
 */
export function Timer(props: TimerProps): JSX.Element {
  // total e left: i secondi, con left tenuto tra 0 e total
  const total = Math.max(1, props.turn.seconds_total);
  const left = Math.min(Math.max(0, props.turn.seconds_left), total);
  const rounded = Math.round(left);
  // startLeft: i secondi del primo disegno. L'animazione CSS parte da lì e scende da
  // sola; cambiare --timer-left a metà la farebbe saltare (React tiene lo stesso
  // elemento). Per ripartire da secondi nuovi Table.tsx cambia la key (P132)
  const [startLeft] = useState(left);

  let className = 'timer';
  if (left <= 10) {
    className = 'timer timer--warn';
  }
  // style: i valori calcolati per il CSS; in pausa l'animazione è ferma
  const style: CSSProperties = { '--timer-start': String(startLeft / total), '--timer-left': String(startLeft) };
  let paused: string | undefined = undefined;
  if (props.paused) {
    paused = '';
    style.animationPlayState = 'paused';
  }
  return (
    <span
      className={className}
      data-timer=""
      data-seconds-left={rounded}
      data-paused={paused}
      role="timer"
      aria-label={`Tempo del turno: ${rounded} secondi`}
      style={style}
    />
  );
}
