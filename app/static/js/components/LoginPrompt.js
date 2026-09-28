/**
 * Finestra "Accedi o registrati per giocare" (P40, DECISIONI.md: chi non ha fatto
 * il login e tocca un'azione riservata vede questa finestra, non un errore).
 *
 * La apre js/core/layout.js per avatar e amici della navbar; le altre pagine la
 * riusano, per esempio la home (P22) per le carte-pulsante:
 *
 *   import { openLoginPrompt } from '../components/LoginPrompt.js';
 *   openLoginPrompt();
 *
 * Costruita su openModal di Modal.js (P19): si chiude con la X, con Esc o
 * toccando fuori. Le pagine di accesso e registrazione le crea P16.
 * In fondo c'è la riga dei crediti delle immagini (D39), la stessa del pannello
 * statistiche (partials/navbar.html, D37): chi non ha fatto il login vede già le
 * carte nel logo, ma il pannello statistiche si apre solo con il login.
 */

import { el } from '../utils/dom.js';
import { openModal } from './Modal.js';

export const LOGIN_URL = '/auth/login';
export const REGISTER_URL = '/auth/register';

export const LICENSE_URL = 'https://creativecommons.org/licenses/by-sa/3.0/deed.it';

let open = false;

/** Riga dei crediti delle immagini delle carte (licenza CC BY-SA 3.0, D37 e D39). */
function credits() {
  return el('p', { class: 'sheet__credits', data: { credits: '' } }, [
    'Immagini delle carte: Matsoftware, ',
    el('a', { text: 'CC BY-SA 3.0', attrs: { href: LICENSE_URL, target: '_blank', rel: 'noopener' } }),
    ', da Wikimedia Commons',
  ]);
}

/**
 * @param {object} [options]
 * @param {string} [options.message] spiegazione sotto il titolo
 * @returns {Promise<void>}
 */
export async function openLoginPrompt({
  message = 'Per giocare, vedere le tue statistiche e i tuoi amici serve un account.',
} = {}) {
  if (open) return;   // doppio clic: una finestra sola
  open = true;
  try {
    const choice = await openModal({
      title: 'Accedi o registrati per giocare',
      message,
      footer: credits(),
      actions: [
        { label: 'Registrati', value: REGISTER_URL, variant: 'ghost' },
        { label: 'Accedi', value: LOGIN_URL, variant: 'primary' },
      ],
    });
    if (choice) window.location.assign(choice);
  } finally {
    open = false;
  }
}
