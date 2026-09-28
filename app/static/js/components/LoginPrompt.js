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
 * Costruita su openModal di Modal.js (P19): si chiude con "Annulla", X, Esc o
 * toccando fuori. Le pagine di accesso e registrazione le crea P16.
 */

import { openModal } from './Modal.js';

export const LOGIN_URL = '/auth/login';
export const REGISTER_URL = '/auth/register';

let open = false;

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
