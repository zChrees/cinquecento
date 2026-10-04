/**
 * Pulsanti "Canta 40" / "Canta 20" (P21): uno per ogni seme che puoi cantare
 * adesso (legal.sing della vista, già deciso dal server: turno, prima della carta,
 * Re e Cavallo in mano, almeno 3 carte a mazzo finito). Nessun pulsante quando
 * non puoi cantare.
 *
 * Il numero sul pulsante segue il contratto: il primo canto della mano vale 40,
 * i successivi 20 (sings vuoto = 40). Serve solo all'etichetta: i punti li
 * decide il server. Stile in css/components/table.css.
 *
 * P85: accanto, "Cala le carte" quando legal.lay_down è vero (D45: solo a inizio
 * presa, dopo aver cantato tutto; il perché lo sa solo il server).
 */

import { el, icon } from '../utils/dom.js';

/**
 * @param {string[]} suits semi cantabili (legal.sing)
 * @param {Array} sings canti della mano in corso (sings della vista)
 * @param {function} onSing chiamata con il seme scelto
 * @param {object} [layDown] P85, "Cala le carte"
 * @param {boolean} [layDown.can] legal.lay_down
 * @param {function} [layDown.onLayDown] chiamata quando si preme
 * @returns {HTMLElement}
 */
export function SingButtons(suits, sings, onSing, { can = false, onLayDown = null } = {}) {
  const points = sings.length === 0 ? 40 : 20;
  const buttons = suits.map((suit) =>
    el('button', {
      class: 'btn btn--primary btn--small sing-button',
      data: { singButton: '', suit },
      attrs: { type: 'button' },
      on: { click: () => onSing(suit) },
    }, [icon('campaign'), `Canta ${points} a ${suit}`]),
  );
  if (can && onLayDown) {
    buttons.push(el('button', {
      class: 'btn btn--primary btn--small lay-down-button',
      data: { layDownButton: '' },
      attrs: { type: 'button' },
      on: { click: onLayDown },
    }, [icon('playing_cards'), 'Cala le carte']));
  }
  return el('div', { class: 'sing-buttons', data: { singButtons: '' } }, buttons);
}
