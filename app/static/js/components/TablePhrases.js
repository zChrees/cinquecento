/**
 * Frasi del tavolo nella pagina (P56, D24; contratto 3.2).
 *
 * - PhrasesButton: il pulsante sopra la mano, a destra (P71; icona del fumetto,
 *   etichetta accessibile "Frasi"; su computer anche la scritta).
 * - PhrasesMenu: l'elenco delle frasi, sopra il pulsante (P71), come pillole che vanno a
 *   capo; l'elenco è quello ricevuto dal server con game:phrases (la pagina non ne
 *   tiene una copia sua).
 * - PhraseBubble: il fumetto accanto all'avatar di chi ha parlato.
 *
 * Il testo delle frasi e i nomi entrano sempre come testo (utils/dom.js), mai come
 * HTML. Quando aprire, chiudere e disattivare lo decide pages/game.js.
 * Stile in css/components/table-phrases.css.
 */

import { el, icon } from '../utils/dom.js';

/**
 * @param {object} options
 * @param {boolean} options.open l'elenco è aperto
 * @param {boolean} options.disabled pulsante spento (subito dopo una frase, o mentre parte)
 * @param {function} options.onToggle apre o chiude l'elenco
 */
export function PhrasesButton({ open, disabled, onToggle }) {
  return el('button', {
    class: 'btn btn--ghost btn--small phrases-button',
    data: { phrasesButton: '' },
    attrs: {
      type: 'button',
      'aria-label': 'Frasi',
      'aria-expanded': open ? 'true' : 'false',
      'aria-controls': 'table-phrases',
      disabled,
    },
    on: { click: onToggle },
  }, [icon('chat_bubble'), el('span', { class: 'phrases-button__text', text: 'Frasi', attrs: { 'aria-hidden': 'true' } })]);
}

/**
 * @param {Array<{code: string, text: string}>} phrases l'elenco di game:phrases
 * @param {object} options
 * @param {boolean} options.disabled frasi spente
 * @param {function} options.onPick frase scelta (code)
 */
export function PhrasesMenu(phrases, { disabled, onPick }) {
  return el('div', {
    class: 'phrases-menu',
    data: { phrasesMenu: '' },
    attrs: { id: 'table-phrases', role: 'group', 'aria-label': 'Frasi da mandare al tavolo' },
  }, phrases.map(({ code, text }) =>
    el('button', {
      class: 'phrase',
      text,
      data: { phraseCode: code },
      attrs: { type: 'button', disabled },
      on: { click: () => onPick(code) },
    }),
  ));
}

/**
 * @param {string} name chi ha parlato (letto dai lettori di schermo, non si vede)
 * @param {string} text la frase
 * @param {string} position 'bottom' | 'right' | 'top' | 'left', il posto al tavolo
 */
export function PhraseBubble(name, text, position) {
  return el('p', {
    class: `phrase-bubble phrase-bubble--${position}`,
    data: { phraseBubble: '' },
    attrs: { role: 'status' },
  }, [el('span', { class: 'visually-hidden', text: `${name}: ` }), text]);
}
