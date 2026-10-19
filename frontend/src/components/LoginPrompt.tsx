/**
 * Finestra "Accedi o registrati per giocare" (P40): la versione React di
 * app/static/js/components/LoginPrompt.js. Chi non ha fatto il login e tocca
 * un'azione riservata (avatar e amici della navbar) vede questa finestra, non un
 * errore (DECISIONI.md).
 *
 * Cosa contiene:
 *   <LoginPrompt onDone={handleDone} />   la finestra; LOGIN_URL, REGISTER_URL
 *
 * Scegliendo "Accedi" o "Registrati" la pagina va a quell'indirizzo; con X, Esc
 * o un tocco fuori si chiude e basta. In fondo c'è la riga dei crediti delle
 * immagini delle carte (licenza CC BY-SA 3.0, D37 e D39).
 *
 * DA DOVE ARRIVANO I DATI: nessun dato dal server; la apre Navbar.tsx.
 */

import type { JSX } from 'react';
import { Modal } from './Modal';
import type { ModalAction } from './Modal';

// Gli indirizzi delle due pagine (come LOGIN_URL e REGISTER_URL di LoginPrompt.js)
export const LOGIN_URL = '/auth/login';
export const REGISTER_URL = '/auth/register';
// LICENSE_URL: la licenza delle immagini delle carte
export const LICENSE_URL = 'https://creativecommons.org/licenses/by-sa/3.0/deed.it';

// ACTIONS: i due pulsanti, il principale per ultimo
const ACTIONS: ModalAction[] = [
  { label: 'Registrati', value: REGISTER_URL, variant: 'ghost' },
  { label: 'Accedi', value: LOGIN_URL, variant: 'primary' },
];

// LoginPromptProps: cosa riceve il componente
interface LoginPromptProps {
  // la funzione da chiamare quando la finestra si è chiusa senza scegliere una
  // pagina: chi la usa la toglie. In C: void (*onDone)(void)
  onDone: () => void;
}

/**
 * La riga dei crediti delle immagini, la stessa del pannello statistiche.
 *
 * In parole semplici:
 *   <Credits />  →  "Immagini delle carte: Matsoftware, CC BY-SA 3.0, da Wikimedia Commons"
 */
export function Credits(): JSX.Element {
  return (
    <p className="sheet__credits" data-credits="">
      Immagini delle carte: Matsoftware,{' '}
      <a href={LICENSE_URL} target="_blank" rel="noopener">CC BY-SA 3.0</a>
      , da Wikimedia Commons
    </p>
  );
}

/**
 * La finestra.
 *
 * @param {LoginPromptProps} props
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <LoginPrompt onDone={handleDone} />
 *   Se si sceglie un pulsante, la pagina va a quell'indirizzo (un caricamento
 *   vero, come prima); altrimenti chiama props.onDone.
 */
export function LoginPrompt(props: LoginPromptProps): JSX.Element {
  /** La finestra si è chiusa: value è l'indirizzo scelto, oppure null. */
  function handleDone(value: string | null): void {
    if (value !== null) {
      window.location.assign(value);
      return;
    }
    props.onDone();
  }

  return (
    <Modal
      title="Accedi o registrati per giocare"
      message="Per giocare, vedere le tue statistiche e i tuoi amici serve un account."
      actions={ACTIONS}
      content={null}
      footer={<Credits />}
      onDone={handleDone}
    />
  );
}
