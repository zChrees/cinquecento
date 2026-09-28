/**
 * Tempo del turno (P21): un anello attorno all'avatar di chi deve giocare, che si
 * svuota in 30 secondi e sotto i 10 diventa rosso. Si muove con un'animazione CSS
 * che parte dai secondi rimasti (turn.seconds_left): niente conteggio in JS.
 * Con "riduci movimento" l'anello resta fermo su quanto tempo restava all'arrivo
 * della vista. Stile in css/components/timer.css.
 */

import { el } from '../utils/dom.js';

/**
 * @param {{seconds_total: number, seconds_left: number}} turn il campo turn della vista
 * @returns {HTMLElement}
 */
export function Timer(turn) {
  const total = Math.max(1, turn.seconds_total);
  const left = Math.min(Math.max(0, turn.seconds_left), total);
  const timer = el('span', {
    class: 'timer',
    data: { timer: '', secondsLeft: Math.round(left) },
    attrs: { role: 'timer', 'aria-label': `Tempo del turno: ${Math.round(left)} secondi` },
  });
  timer.style.setProperty('--timer-start', String(left / total));
  timer.style.setProperty('--timer-left', String(left));
  timer.classList.toggle('timer--warn', left <= 10);
  return timer;
}
