/**
 * Finestra "Nessuna connessione" (P125): compare se si prova a mandare un modulo
 * senza rete, al posto dell'invio (come showOffline() di js/pages/auth.js).
 *
 * Cosa contiene:
 *   <OfflineModal onDone={handleDone} />
 *
 * DA DOVE ARRIVANO I DATI: nessuno; la apre la pagina quando navigator.onLine è false.
 */

import type { JSX } from 'react';
import { Modal } from './Modal';
import type { ModalAction } from './Modal';

// ACTIONS: un solo pulsante
const ACTIONS: ModalAction[] = [{ label: 'Ok', value: 'ok', variant: 'primary' }];

// OfflineModalProps: cosa riceve il componente
interface OfflineModalProps {
  // la funzione da chiamare a finestra chiusa: chi la usa la toglie. In C: void (*onDone)(void)
  onDone: () => void;
}

/**
 * La finestra.
 *
 * In parole semplici:
 *   <OfflineModal onDone={handleDone} />
 *   Qualunque cosa si scelga (Ok, X, Esc, tocco fuori), chiama props.onDone.
 */
export function OfflineModal(props: OfflineModalProps): JSX.Element {
  /** La finestra si è chiusa: il valore non conta. */
  function handleDone(): void {
    props.onDone();
  }

  return (
    <Modal
      title="Nessuna connessione"
      message="Controlla la connessione a internet e riprova."
      actions={ACTIONS}
      content={null}
      footer={null}
      onDone={handleDone}
    />
  );
}
