/**
 * L'invito a partita ricevuto (P47; contratto 5.3; scelta di Giuseppe: solo nella
 * home): la versione React di app/static/js/components/InviteDialog.js, con lo
 * stesso HTML (stile di Modal: css/components/modal.css). Chi invita, modalità e
 * punti, il conto alla rovescia, "Rifiuta" e "Accetta". Dopo "Accetta" aspetta che
 * chi ha invitato avvii la partita ("Rifiuta" diventa "Esci", per uscire). X ed Esc
 * valgono come "Rifiuta".
 *
 * Cosa contiene:
 *   <InviteDialog key={invite.invite_id} invite={...} status={...} online={...}
 *                 onAccept={...} onDecline={...} onClosed={...} />
 *   InviteDialogStatus   gli stati della finestra: quelli dell'invito più 'connection_lost'
 *
 * onAccept e onDecline mandano la richiesta e restituiscono la risposta del server:
 * finché non arriva i pulsanti sono spenti (doppio clic). Con lo stato 'started' o
 * 'declined' la finestra si chiude subito (la pagina va al tavolo o in coda); con
 * gli altri stati finali mostra il motivo e si chiude dopo CLOSE_AFTER_MS.
 * 'connection_lost' non viene dal server: quando la connessione cade il server
 * annulla gli inviti di chi resta senza schede, ma l'avviso non può arrivare (P83).
 * Senza connessione (online false) "Accetta" e "Rifiuta" sono spenti (P33).
 *
 * DA DOVE ARRIVANO I DATI: l'invito da invite:received, lo stato da invite:update
 * (HomePage.tsx, con socket/); i nomi entrano sempre come testo, mai come HTML.
 */

import { useEffect, useRef, useState } from 'react';
import type { JSX, RefObject, SyntheticEvent } from 'react';
import type { ErrorResponse, NoConnection, OkEmpty } from '../types/common';
import type { Invite, InviteStatus } from '../types/events';
import { formatWait } from './QueueOverlay';

// CLOSE_AFTER_MS: quanto resta il motivo di un invito finito (scaduto, annullato, ...)
const CLOSE_AFTER_MS = 4000;

// TICK_MS: ogni quanto si aggiorna il conto alla rovescia
const TICK_MS = 1000;

// InviteDialogStatus: lo stato della finestra. La | vuol dire "uno di questi
// valori": quelli dell'invito del contratto, più 'connection_lost' (solo della pagina)
export type InviteDialogStatus = InviteStatus | 'connection_lost';

// Reply: la risposta del server ad "Accetta" o "Rifiuta" (o "niente connessione")
export type Reply = OkEmpty | ErrorResponse | NoConnection;

// NOTES: il testo sotto, per ogni stato (con il nome di chi invita dove serve)
const FIXED_NOTES: Record<string, string> = {
  expired: "L'invito è scaduto.",
  declined: "Hai rifiutato l'invito.",
  connection_lost: "La connessione è caduta: l'invito è stato annullato.",
};

// InviteDialogProps: cosa riceve il componente
interface InviteDialogProps {
  // l'invito ricevuto: { invite_id, from, mode, target_score, seconds_left, status }
  invite: Invite;
  // lo stato attuale (all'inizio quello dell'invito, poi da invite:update)
  status: InviteDialogStatus;
  // P33: false senza connessione
  online: boolean;
  // "Accetta": manda invite:accept e restituisce la risposta. In C: un puntatore a
  // funzione che restituisce una "promessa" di risposta
  onAccept: () => Promise<Reply>;
  // "Rifiuta" (anche X ed Esc): manda invite:decline e restituisce la risposta
  onDecline: () => Promise<Reply>;
  // la finestra si è chiusa: la pagina la toglie. In C: void (*onClosed)(void)
  onClosed: () => void;
}

/**
 * La frase con chi invita, la modalità e i punti.
 *
 * @param {Invite} invite
 * @returns {string} per esempio 'Giulia ti invita a giocare contro di te nel 1v1, a 500 punti.'
 *
 * In parole semplici:
 *   Nel 2v2 chi invita può chiamare fino a tre amici (P59): le squadre si sanno solo
 *   quando si entra in coda o comincia la partita, quindi non dice "in squadra con te".
 */
function describe(invite: Invite): string {
  let role = 'a giocare contro di te nel 1v1';
  if (invite.mode === '2v2') {
    role = 'a una partita 2v2 tra amici';
  }
  return `${invite.from.username} ti invita ${role}, a ${invite.target_score} punti.`;
}

/**
 * Dice se l'invito è ancora aperto (si può ancora rispondere).
 *
 * @param {InviteDialogStatus} status
 * @returns {boolean} true per 'pending' (da rispondere) e 'accepted' (in attesa di chi invita)
 */
function isOpen(status: InviteDialogStatus): boolean {
  return status === 'pending' || status === 'accepted';
}

/**
 * La finestra dell'invito.
 *
 * @param {InviteDialogProps} props
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <InviteDialog key={id} invite={invite} status="pending" ... />
 *   Si apre (showModal) appena compare, con il fuoco su "Accetta". Il key è l'id
 *   dell'invito: un invito nuovo è una finestra nuova.
 */
export function InviteDialog(props: InviteDialogProps): JSX.Element {
  // Gli hook si chiamano sempre in cima al componente, mai dentro un if.
  // dialogRef e acceptRef: il <dialog> e il pulsante "Accetta" veri della pagina
  const dialogRef: RefObject<HTMLDialogElement | null> = useRef<HTMLDialogElement>(null);
  const acceptRef: RefObject<HTMLButtonElement | null> = useRef<HTMLButtonElement>(null);
  // closed: true dopo la chiusura (onClosed parte una volta sola)
  const closed: RefObject<boolean> = useRef<boolean>(false);
  // useState restituisce due cose: il valore attuale e la funzione per cambiarlo,
  // che fa ridisegnare il componente (regole-codice.md, sezione 6).
  // waiting: true mentre "Accetta" o "Rifiuta" aspettano la risposta del server
  const [waiting, setWaiting] = useState<boolean>(false);
  // accepted: true dopo la risposta positiva ad "Accetta" (prima che arrivi invite:update)
  const [accepted, setAccepted] = useState<boolean>(false);
  // errorNote: un errore del server o "Sei offline", al posto della nota dello stato; '' = nessuno
  const [errorNote, setErrorNote] = useState<string>('');
  // secondsLeft: i secondi rimasti, contati dalla pagina (contratto 1.1)
  const [secondsLeft, setSecondsLeft] = useState<number>(props.invite.seconds_left);

  // status: lo stato da mostrare. Dopo "Accetta" riuscito vale 'accepted' anche se
  // invite:update non è ancora arrivato
  let status: InviteDialogStatus = props.status;
  if (accepted && status === 'pending') {
    status = 'accepted';
  }

  /** Chiude la finestra (una volta sola) e lo dice alla pagina. */
  function close(): void {
    if (closed.current) {
      return;
    }
    closed.current = true;
    const dialog = dialogRef.current;
    if (dialog !== null && dialog.open) {
      dialog.close();
    }
    props.onClosed();
  }

  /** Effetto: apre la finestra con il fuoco su "Accetta" e fa partire il conto alla rovescia. */
  function open(): () => void {
    const dialog = dialogRef.current;
    if (dialog !== null && !dialog.open) {
      dialog.showModal();
    }
    if (acceptRef.current !== null) {
      acceptRef.current.focus();
    }
    // deadline: quando scade l'invito (millisecondi)
    const deadline = Date.now() + props.invite.seconds_left * 1000;

    function tick(): void {
      setSecondsLeft(Math.max(0, (deadline - Date.now()) / 1000));
    }

    function stop(): void {
      window.clearInterval(timer);
      if (dialog !== null && dialog.open) {
        dialog.close();
      }
    }

    const timer = window.setInterval(tick, TICK_MS);
    return stop;
  }

  // []: una volta sola, quando la finestra compare
  useEffect(open, []);

  /**
   * Effetto a ogni stato nuovo: 'started' e 'declined' chiudono subito; gli altri
   * stati finali mostrano il motivo e chiudono dopo CLOSE_AFTER_MS.
   */
  function followStatus(): () => void {
    // timer: la chiusura in attesa (0 = nessuna)
    let timer = 0;

    function stop(): void {
      window.clearTimeout(timer);
    }

    if (props.status === 'started' || props.status === 'declined') {
      close();
    } else if (!isOpen(props.status)) {
      setErrorNote('');
      timer = window.setTimeout(close, CLOSE_AFTER_MS);
    }
    return stop;
  }

  // [props.status]: si rifà quando lo stato cambia
  useEffect(followStatus, [props.status]);

  /**
   * "Accetta" o "Rifiuta": manda la richiesta e aspetta la risposta.
   *
   * @param {'accept' | 'decline'} kind quale dei due
   */
  async function answer(kind: 'accept' | 'decline'): Promise<void> {
    if (waiting || closed.current || !isOpen(status)) {
      return;
    }
    if (kind === 'accept' && status !== 'pending') {
      return;
    }
    if (!navigator.onLine) {
      setErrorNote('Sei offline: rispondi appena torna la connessione.');
      return;
    }
    setWaiting(true);
    setErrorNote('');
    let reply: Reply;
    if (kind === 'accept') {
      reply = await props.onAccept();
    } else {
      reply = await props.onDecline();
    }
    setWaiting(false);
    if (closed.current) {
      return;
    }
    if (!reply.ok) {
      setErrorNote(reply.error.message);
      return;
    }
    if (kind === 'decline') {
      close();
      return;
    }
    setAccepted(true);
  }

  function handleAccept(): void {
    answer('accept');
  }

  function handleDecline(): void {
    answer('decline');
  }

  /** X ed Esc: "Rifiuta" finché l'invito è aperto, poi chiudono e basta. */
  function dismiss(): void {
    if (isOpen(status)) {
      answer('decline');
    } else {
      close();
    }
  }

  /** Esc: il browser chiuderebbe da solo; vale invece come la X. */
  function handleEscape(event: SyntheticEvent<HTMLDialogElement>): void {
    event.preventDefault();
    dismiss();
  }

  // note: il testo sotto, deciso con un if prima del return
  const from = props.invite.from.username;
  let note = '';
  if (status === 'accepted') {
    note = `Hai accettato: aspettiamo che ${from} avvii la partita…`;
  } else if (status === 'cancelled') {
    note = `${from} ha annullato l'invito.`;
  } else if (status in FIXED_NOTES) {
    note = FIXED_NOTES[status];
  }
  if (errorNote !== '') {
    note = errorNote;
  }

  // declineText: "Esci" dopo l'accettazione; buttonsOff: pulsanti spenti
  let declineText = 'Rifiuta';
  if (status === 'accepted') {
    declineText = 'Esci';
  }
  const buttonsOff = waiting || !isOpen(status) || !props.online;

  return (
    <dialog
      className="dialog"
      aria-labelledby="invite-title"
      data-invite-dialog={props.invite.invite_id}
      data-invite-status={status}
      ref={dialogRef}
      onCancel={handleEscape}
    >
      <div className="dialog__head">
        <h2 className="dialog__title" id="invite-title">Invito a partita</h2>
        <button className="icon-btn" type="button" aria-label="Rifiuta e chiudi" disabled={waiting} onClick={dismiss}>
          <span className="icon" aria-hidden="true">close</span>
        </button>
      </div>
      <p className="dialog__body">{describe(props.invite)}</p>
      <p className="dialog__body" hidden={status !== 'pending'}>
        Rispondi entro <span data-invite-seconds="">{formatWait(secondsLeft)}</span>
      </p>
      <p className="dialog__body" role="status" data-invite-note="">{note}</p>
      <div className="dialog__actions">
        <button className="btn btn--ghost" type="button" data-invite-decline="" disabled={buttonsOff} onClick={handleDecline}>
          {declineText}
        </button>
        <button
          className="btn btn--primary"
          type="button"
          data-invite-accept=""
          hidden={status !== 'pending'}
          disabled={buttonsOff}
          ref={acceptRef}
          onClick={handleAccept}
        >
          Accetta
        </button>
      </div>
    </dialog>
  );
}
