/**
 * Pagine di accesso e registrazione (P125): stesso script per tutte e due.
 *
 * - Avvia navbar e logo (core/layout.js): senza login "Accedi" e "Amici" aprono
 *   la finestra "Accedi o registrati per giocare", come nelle altre pagine.
 * - Il modulo si invia normalmente; al primo invio il pulsante si disattiva, così
 *   un doppio clic non manda due richieste (alla registrazione la seconda
 *   troverebbe l'username già preso e mostrerebbe un errore).
 * - Senza connessione il modulo non parte: compare una finestra che lo dice.
 */

import { initLayout } from '../core/layout.js';
import { openModal } from '../components/Modal.js';

initLayout();

const form = document.querySelector('[data-login-form], [data-register-form]');
const submit = form.querySelector('button[type="submit"]');

function showOffline() {
  return openModal({
    title: 'Nessuna connessione',
    message: 'Controlla la connessione a internet e riprova.',
    actions: [{ label: 'Ok', value: true }],
  });
}

form.addEventListener('submit', (event) => {
  if (!navigator.onLine) {
    event.preventDefault();
    showOffline();
    return;
  }
  if (submit.disabled) {
    event.preventDefault();
    return;
  }
  submit.disabled = true;
});

// Tornando indietro alla pagina (cache del browser) il pulsante si riattiva
window.addEventListener('pageshow', () => {
  submit.disabled = false;
});
