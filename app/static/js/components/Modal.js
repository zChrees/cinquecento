/**
 * Finestra nella pagina, al posto di alert / confirm / prompt (P19).
 *
 * Esempio (uscita dal tavolo, P21):
 *
 *   import { confirmModal } from '../components/Modal.js';
 *   const ok = await confirmModal({
 *     title: 'Vuoi uscire dalla partita?',
 *     message: 'La partita sarà persa per abbandono.',
 *     confirmLabel: 'Esci',
 *     danger: true,
 *   });
 *   if (ok) { ... }
 *
 * La finestra si chiude con i pulsanti, con la X, con Esc o toccando fuori (queste
 * ultime tre valgono come "Annulla"). Dopo la prima scelta i pulsanti si
 * disattivano: un doppio clic non conta due volte. Titolo e messaggio sono sempre
 * inseriti come testo, mai come HTML. Stile in css/components/modal.css.
 */

import { el, icon } from '../utils/dom.js';

let nextId = 0;

function reduceMotion() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/**
 * Apre una finestra con dei pulsanti e restituisce il valore di quello scelto.
 *
 * @param {object} options
 * @param {string} options.title titolo (testo)
 * @param {string} [options.message] testo sotto il titolo
 * @param {Node} [options.content] contenuto in più (un elemento già creato con el())
 * @param {Node} [options.footer] riga in fondo, sotto i pulsanti (es. i crediti delle immagini, D39)
 * @param {Array<{label: string, value: *, variant?: 'primary'|'ghost'|'danger'}>} options.actions
 *        pulsanti, nell'ordine in cui compaiono (il principale per ultimo); il primo riceve il focus
 * @param {*} [options.dismissValue] valore per X, Esc e tocco fuori (predefinito: null)
 * @returns {Promise<*>}
 */
export function openModal({ title, message = '', content = null, footer = null, actions, dismissValue = null }) {
  return new Promise((resolve) => {
    const titleId = `dialog-title-${++nextId}`;
    let closing = false;

    const buttons = actions.map((action, index) =>
      el('button', {
        class: `btn btn--${action.variant ?? 'primary'}`,
        text: action.label,
        attrs: { type: 'button', autofocus: index === 0 },
        on: { click: () => finish(action.value) },
      }),
    );
    const closeButton = el(
      'button',
      {
        class: 'icon-btn',
        attrs: { type: 'button', 'aria-label': 'Chiudi' },
        on: { click: () => finish(dismissValue) },
      },
      icon('close'),
    );

    const dialog = el(
      'dialog',
      { class: 'dialog', attrs: { 'aria-labelledby': titleId }, data: { animated: '', modal: '' } },
      [
        el('div', { class: 'dialog__head' }, [
          el('h2', { class: 'dialog__title', text: title, attrs: { id: titleId } }),
          closeButton,
        ]),
        message ? el('p', { class: 'dialog__body', text: message }) : null,
        content,
        el('div', { class: 'dialog__actions' }, buttons),
        footer,
      ],
    );

    // Esc: il browser chiuderebbe subito; lo gestiamo noi per l'animazione
    dialog.addEventListener('cancel', (event) => {
      event.preventDefault();
      finish(dismissValue);
    });
    // Tocco fuori dalla finestra: il clic arriva al <dialog> stesso (lo sfondo)
    dialog.addEventListener('click', (event) => {
      if (event.target === dialog) finish(dismissValue);
    });

    function finish(value) {
      if (closing) return;
      closing = true;
      for (const button of [...buttons, closeButton]) button.disabled = true;

      const done = () => {
        dialog.close();
        dialog.remove();
        resolve(value);
      };
      if (reduceMotion()) {
        done();
        return;
      }
      dialog.classList.add('is-closing');
      dialog.addEventListener('animationend', done, { once: true });
      // Se l'animazione non parte (per esempio scheda in secondo piano), chiude comunque
      setTimeout(() => dialog.isConnected && done(), 400);
    }

    document.body.append(dialog);
    dialog.showModal();
  });
}

/**
 * Chiede una conferma: restituisce true con "Conferma", false con "Annulla", la X,
 * Esc o un tocco fuori.
 *
 * @param {object} options
 * @param {string} options.title domanda (testo)
 * @param {string} [options.message] spiegazione, per esempio cosa succede confermando
 * @param {string} [options.confirmLabel] testo del pulsante di conferma
 * @param {string} [options.cancelLabel] testo del pulsante per annullare
 * @param {boolean} [options.danger] true per un'azione che non si annulla (pulsante rosso)
 * @returns {Promise<boolean>}
 */
export function confirmModal({
  title,
  message = '',
  confirmLabel = 'Conferma',
  cancelLabel = 'Annulla',
  danger = false,
}) {
  return openModal({
    title,
    message,
    actions: [
      { label: cancelLabel, value: false, variant: 'ghost' },
      { label: confirmLabel, value: true, variant: danger ? 'danger' : 'primary' },
    ],
    dismissValue: false,
  });
}
