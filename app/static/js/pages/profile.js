/**
 * Pagina delle impostazioni (P17): avatar e cancellazione dell'account.
 *
 * - Il modulo dell'avatar si invia normalmente; al primo invio il pulsante si
 *   disattiva, così un doppio clic non manda due richieste.
 * - "Cancella l'account" apre una finestra nella pagina (Modal.js) che chiede la
 *   password; il modulo parte solo con "Cancella l'account". Il controllo della
 *   password lo fa il server.
 * - Senza connessione nessun modulo parte: compare una finestra che lo dice.
 */

import { initLayout } from '../core/layout.js';
import { openModal } from '../components/Modal.js';
import { el } from '../utils/dom.js';

initLayout();

const avatarForm = document.querySelector('[data-avatar-form]');
const avatarSubmit = document.querySelector('[data-avatar-submit]');
const deleteForm = document.querySelector('[data-delete-form]');
const deletePassword = document.querySelector('[data-delete-password]');
const deleteOpen = document.querySelector('[data-delete-open]');

function showOffline() {
  return openModal({
    title: 'Nessuna connessione',
    message: 'Controlla la connessione a internet e riprova.',
    actions: [{ label: 'Ok', value: true }],
  });
}

avatarForm.addEventListener('submit', (event) => {
  if (!navigator.onLine) {
    event.preventDefault();
    showOffline();
    return;
  }
  avatarSubmit.disabled = true;
});

deleteOpen.addEventListener('click', async () => {
  const input = el('input', {
    class: 'input',
    attrs: { type: 'password', id: 'delete-password', autocomplete: 'current-password', required: true },
  });
  const field = el('div', { class: 'field' }, [
    el('label', { class: 'field__label', text: 'Password', attrs: { for: 'delete-password' } }),
    input,
  ]);
  const choice = openModal({
    title: "Cancellare l'account?",
    message: 'Non si può annullare. Per confermare scrivi la tua password.',
    content: field,
    actions: [
      { label: 'Annulla', value: false, variant: 'ghost' },
      { label: "Cancella l'account", value: true, variant: 'danger' },
    ],
    dismissValue: false,
  });
  input.focus();
  // Invio nel campo della password = "Cancella l'account"
  input.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      input.closest('dialog')?.querySelector('.btn--danger')?.click();
    }
  });

  if (!(await choice)) return;
  if (!navigator.onLine) {
    showOffline();
    return;
  }
  deletePassword.value = input.value;
  deleteOpen.disabled = true;
  deleteForm.submit();
});

// Tornando indietro alla pagina (cache del browser) i pulsanti si riattivano
window.addEventListener('pageshow', () => {
  avatarSubmit.disabled = false;
  deleteOpen.disabled = false;
  deletePassword.value = '';
});
