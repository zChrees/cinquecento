/**
 * Avatar di un utente (P43): l'immagine del set (D29) o, per chi non ne ha scelto
 * uno, l'iniziale del nome. È l'unico posto delle pagine che decide quale dei due
 * mostrare: tavolo, pannello amici, carta-modal e schermata di coda lo usano.
 * Navbar, pannello statistiche e impostazioni usano la macro gemella
 * templates/partials/avatar.html.
 *
 *   Avatar({ username: 'Giulia', avatar: 're_coppe' })                    // class="avatar"
 *   Avatar(friend, 'mini-avatar mini-avatar--2')                          // negli elenchi
 *
 * Le immagini sono app/static/img/avatars/<codice>.svg, una per codice di
 * app/services/avatars.py: AVATAR_CODES deve restare uguale a quell'elenco (lo
 * controlla tests/frontend/test_avatar.py con Node). Un codice fuori elenco (per
 * esempio negli esempi di app/static/dev/) mostra l'iniziale.
 * L'avatar è decorativo (aria-hidden): accanto c'è sempre il nome.
 * La CPU (giocatore con `cpu: true` nella vista, P68) ha l'icona del robot (P73, D43).
 */

import { el, icon } from '../utils/dom.js';
import { reusedImage } from './Card.js';

export const AVATAR_CODES = Object.freeze([
  'coppe', 'denari', 'spade', 'bastoni',
  're_coppe', 're_denari', 're_spade', 're_bastoni',
  'cavallo_coppe', 'cavallo_bastoni', 'fante_denari', 'fante_spade',
]);

const IMG_BASE = new URL('../../img/avatars/', import.meta.url).href;

/** Indirizzo dell'immagine di un codice, o null se il codice non è del set. */
export function avatarUrl(code) {
  return AVATAR_CODES.includes(code) ? `${IMG_BASE}${code}.svg` : null;
}

/**
 * @param {{username: string, avatar?: string|null, cpu?: boolean}} user
 * @param {string} [className] classi dell'elemento ('avatar', 'mini-avatar …')
 * @returns {HTMLElement}
 */
export function Avatar(user, className = 'avatar') {
  if (user.cpu) {
    return el('span', { class: `${className} avatar--cpu`, data: { cpu: '' }, attrs: { 'aria-hidden': 'true' } }, [icon('smart_toy')]);
  }
  const url = avatarUrl(user.avatar);
  if (!url) {
    return el('span', { class: className, text: user.username.charAt(0).toUpperCase(), attrs: { 'aria-hidden': 'true' } });
  }
  return el('span', { class: `${className} avatar--img`, data: { avatar: user.avatar }, attrs: { 'aria-hidden': 'true' } }, [
    // decoding sync: il tavolo si ridisegna a ogni vista, e un'immagine nuova
    // decodificata dopo si vedrebbe vuota per un attimo (come le carte in P70);
    // P119: al tavolo si riusa proprio l'immagine del disegno di prima (reusedImage)
    reusedImage('avatar__img', url, { decoding: 'sync' }),
  ]);
}
