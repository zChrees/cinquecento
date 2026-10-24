/**
 * La chat con un amico (P46, P48): si apre dentro il
 * pannello amici, al posto della lista (stile in
 * css/components/chat.css).
 *
 * Cosa contiene:
 *   <ChatWindow friend={...} meId={12} history={...} onBack={...} onClose={...} />
 *   MAX_LENGTH, CHAT_CLOSED    il limite di un messaggio e i motivi per non poter scrivere
 *
 * Dentro: i messaggi (i tuoi a destra), "Messaggi precedenti", la casella con "Invia".
 * La finestra parla da sola con il server, sempre attraverso socket/ (contratto 5.4):
 * chat:send per mandare, chat:history per i messaggi precedenti e al ritorno della
 * connessione, chat:read quando arriva un messaggio dell'amico mentre la chat è aperta,
 * e ascolta chat:message. Con un blocco o senza più amicizia si legge ma non si
 * scrive, e la chat lo dice in cima (D24, D41). Senza connessione "Invia" è spento (P33).
 * Il testo dei messaggi entra sempre come testo, mai come HTML.
 *
 * DA DOVE ARRIVANO I DATI: la prima pagina di messaggi (history) la chiede
 * FriendsPanel.tsx con chat:history prima di aprire la chat; l'amico dalla lista
 * (GET /api/friends/); il tuo user_id dalla sessione.
 */

import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import type { ChangeEvent, FormEvent, JSX, MouseEvent, RefObject } from 'react';
import { send } from '../socket/client';
import { useConnection, useSocketEvent } from '../socket/hooks';
import type { Friend } from '../types/api';
import type { ChatHistory, ChatMessage } from '../types/events';
import { newRequestId } from '../utils/requestId';
import { PRESENCE_LABEL } from './FriendRows';

// MAX_LENGTH: il massimo di caratteri di un messaggio (D26), come CHAT_MAX_LENGTH di
// config.py (lo controlla tests/frontend/test_finestra_chat.py)
export const MAX_LENGTH = 1000;

// CHAT_CLOSED: perché non si può più scrivere (cannot_write di chat:history) → la
// frase in cima alla chat
export const CHAT_CLOSED: Record<'blocked' | 'not_friends', string> = {
  blocked: 'Bloccato: non potete più scrivervi.',
  not_friends: 'Non siete più amici: puoi leggere la conversazione, ma non scrivere.',
};

// CLOSED_DEFAULT: la frase quando il motivo non si sa
const CLOSED_DEFAULT = 'Non puoi più scrivere a questo utente.';

// ScrollAfter: cosa fare con lo scorrimento dell'elenco dopo il prossimo disegno:
// 'bottom' (in fondo, sull'ultimo messaggio), 'keep' (resta sul messaggio che si
// stava leggendo, dopo "Messaggi precedenti"), 'none' (niente)
interface ScrollAfter {
  mode: 'bottom' | 'keep' | 'none';
  // con 'keep': l'altezza dell'elenco prima di aggiungere i messaggi in cima
  height: number;
}

/**
 * L'ora di un messaggio, per esempio '14:03'.
 *
 * @param {string} sentAt la data in ISO 8601 UTC, per esempio '2026-09-28T12:03:12.000Z'
 * @returns {string} l'ora italiana, oppure '' se la data non è valida
 */
function timeOf(sentAt: string): string {
  const date = new Date(sentAt);
  if (Number.isNaN(date.getTime())) {
    return '';
  }
  return date.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' });
}

/**
 * Dice se un messaggio è già nell'elenco (stesso id).
 */
function hasMessage(list: ChatMessage[], id: number): boolean {
  for (let i = 0; i < list.length; i++) {
    if (list[i].id === id) {
      return true;
    }
  }
  return false;
}

/**
 * Aggiunge in fondo i messaggi nuovi, saltando quelli che ci sono già.
 *
 * @returns {ChatMessage[]} un elenco nuovo, oppure lo stesso se non c'era niente di nuovo
 *
 * In parole semplici:
 *   appendNew([m1, m2], [m2, m3])  →  [m1, m2, m3]
 *   Lo stesso messaggio può arrivare due volte (la risposta di chat:send e
 *   chat:message, o dopo un ricollegamento): si mostra una volta sola. Restituendo
 *   lo stesso elenco quando non cambia niente, React non ridisegna.
 */
function appendNew(current: ChatMessage[], incoming: ChatMessage[]): ChatMessage[] {
  const result: ChatMessage[] = [];
  for (let i = 0; i < current.length; i++) {
    result.push(current[i]);
  }
  let added = false;
  for (let i = 0; i < incoming.length; i++) {
    if (!hasMessage(result, incoming[i].id)) {
      result.push(incoming[i]);
      added = true;
    }
  }
  if (!added) {
    return current;
  }
  return result;
}

/**
 * Mette in cima i messaggi più vecchi (quelli di "Messaggi precedenti").
 *
 * In parole semplici:
 *   prependOld([m3, m4], [m1, m2])  →  [m1, m2, m3, m4]
 */
function prependOld(current: ChatMessage[], older: ChatMessage[]): ChatMessage[] {
  const result: ChatMessage[] = [];
  for (let i = 0; i < older.length; i++) {
    if (!hasMessage(current, older[i].id)) {
      result.push(older[i]);
    }
  }
  for (let i = 0; i < current.length; i++) {
    result.push(current[i]);
  }
  return result;
}

/**
 * La frase in cima alla chat per un motivo di cannot_write.
 *
 * In parole semplici:
 *   closedText('blocked')  →  'Bloccato: non potete più scrivervi.'
 *   closedText(null)       →  ''   (si può scrivere)
 */
function closedText(reason: 'blocked' | 'not_friends' | null): string {
  if (reason === null) {
    return '';
  }
  return CHAT_CLOSED[reason];
}

// ChatWindowProps: cosa riceve la chat
interface ChatWindowProps {
  // l'amico (nome, stato e user_id), dalla lista del pannello
  friend: Friend;
  // il tuo user_id, per riconoscere i tuoi messaggi
  meId: number;
  // la prima pagina di messaggi, la risposta di chat:history chiesta da FriendsPanel
  history: ChatHistory;
  // la freccia "Torna agli amici" e la X; in C: void (*onBack)(void)
  onBack: () => void;
  onClose: () => void;
}

/**
 * La chat.
 *
 * @param {ChatWindowProps} props
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <ChatWindow key={amico.user_id} friend={amico} ... />
 *   La key cambia con l'amico: per un'altra chat React crea una finestra nuova, con
 *   lo stato da capo, invece di riusare quella di prima.
 */
export function ChatWindow(props: ChatWindowProps): JSX.Element {
  const friendId = props.friend.user_id;

  // Gli hook si chiamano sempre in cima al componente, mai dentro un if.
  // useState restituisce due cose: il valore attuale e la funzione per cambiarlo,
  // che fa ridisegnare il componente (regole-codice.md, sezione 6).
  // messages: i messaggi, dal più vecchio al più nuovo
  const [messages, setMessages] = useState<ChatMessage[]>(props.history.messages);
  // hasMore: true se ci sono messaggi più vecchi da caricare
  const [hasMore, setHasMore] = useState<boolean>(props.history.has_more);
  // canWrite: false con un blocco o senza amicizia (si legge ma non si scrive)
  const [canWrite, setCanWrite] = useState<boolean>(props.history.can_write);
  // notice: la frase in cima (perché non si può scrivere), oppure ''
  const [notice, setNotice] = useState<string>(closedText(props.history.cannot_write));
  // text: quello che è scritto nella casella
  const [text, setText] = useState<string>('');
  // error: l'errore sotto la casella, oppure ''
  const [error, setError] = useState<string>('');
  // sending: true mentre il messaggio è in viaggio ("Invia" spento)
  const [sending, setSending] = useState<boolean>(false);
  // loadingMore: true mentre arrivano i messaggi precedenti
  const [loadingMore, setLoadingMore] = useState<boolean>(false);
  // status: lo stato della connessione al tempo reale
  const status = useConnection();

  // Le ref tengono un valore tra un disegno e l'altro senza far ridisegnare.
  // listRef: l'elenco dei messaggi; inputRef: la casella
  const listRef: RefObject<HTMLOListElement | null> = useRef<HTMLOListElement>(null);
  const inputRef: RefObject<HTMLInputElement | null> = useRef<HTMLInputElement>(null);
  // scrollAfter: cosa fare con lo scorrimento dopo il prossimo disegno (all'inizio: in fondo)
  const scrollAfter: RefObject<ScrollAfter> = useRef<ScrollAfter>({ mode: 'bottom', height: 0 });
  // atBottom: true se l'elenco è in fondo (P128)
  const atBottom: RefObject<boolean> = useRef<boolean>(true);
  // sendingNow: come sending, ma subito (un doppio clic velocissimo troverebbe lo stato vecchio)
  const sendingNow: RefObject<boolean> = useRef<boolean>(false);
  // wasOnline: true dopo il primo collegamento; al ritorno si riprendono i messaggi persi
  const wasOnline: RefObject<boolean> = useRef<boolean>(false);

  // offline: senza connessione "Invia" è spento e la chat ha data-offline (P33)
  let offline = false;
  if (status !== 'connected') {
    offline = true;
  }

  /**
   * Aggiunge dei messaggi in fondo (una volta sola per id) e scorre fino all'ultimo.
   */
  function addMessages(incoming: ChatMessage[]): void {
    scrollAfter.current = { mode: 'bottom', height: 0 };

    /** setMessages con una funzione: riceve l'elenco più recente. */
    function update(current: ChatMessage[]): ChatMessage[] {
      return appendNew(current, incoming);
    }

    setMessages(update);
  }

  /** Chiude la scrittura (amicizia finita o blocco, D24) e dice perché in cima. */
  function disableWriting(reason: string): void {
    setCanWrite(false);
    setNotice(reason);
  }

  /**
   * Effetto dopo ogni cambio dei messaggi, prima che il browser mostri la pagina
   * (useLayoutEffect: così lo scorrimento non "salta" davanti agli occhi).
   * Va in fondo per un messaggio nuovo, resta sul messaggio che si leggeva dopo
   * "Messaggi precedenti".
   */
  function placeScroll(): void {
    const list = listRef.current;
    const after = scrollAfter.current;
    if (list === null || after.mode === 'none') {
      return;
    }
    if (after.mode === 'bottom') {
      list.scrollTop = list.scrollHeight;
    } else {
      list.scrollTop = list.scrollTop + (list.scrollHeight - after.height);
    }
    scrollAfter.current = { mode: 'none', height: 0 };
  }

  // [messages]: si rifà quando l'elenco cambia (e la prima volta)
  useLayoutEffect(placeScroll, [messages]);

  /**
   * Effetto all'apertura: il fuoco nella casella, se si può scrivere; e (P128)
   * quando l'elenco si accorcia, per esempio la tastiera del telefono che si apre,
   * chi era in fondo resta in fondo, sugli ultimi messaggi.
   */
  function start(): () => void {
    if (inputRef.current !== null && !inputRef.current.disabled) {
      inputRef.current.focus();
    }
    const list = listRef.current;

    /** L'elenco ha cambiato misura. */
    function handleResize(): void {
      if (list !== null && atBottom.current) {
        list.scrollTop = list.scrollHeight;
      }
    }

    const observer = new ResizeObserver(handleResize);
    if (list !== null) {
      observer.observe(list);
    }

    /** Pulizia: smette di osservare quando la chat si chiude. */
    function stop(): void {
      observer.disconnect();
    }

    return stop;
  }

  // []: una volta sola, quando la chat compare
  useEffect(start, []);

  /** L'elenco è stato fatto scorrere: si ricorda se è in fondo (entro 4 px). */
  function handleScroll(): void {
    const list = listRef.current;
    if (list === null) {
      return;
    }
    atBottom.current = list.scrollHeight - list.scrollTop - list.clientHeight < 4;
  }

  /**
   * Arriva un messaggio (chat:message): se è di questa conversazione si aggiunge, e
   * se è dell'amico si segna come letto (la chat è aperta: l'hai visto).
   */
  function handleIncoming(data: { message: ChatMessage }): void {
    const message = data.message;
    let other = message.from_user_id;
    if (message.from_user_id === props.meId) {
      other = message.to_user_id;
    }
    if (other !== friendId) {
      return;
    }
    addMessages([message]);
    if (message.from_user_id !== props.meId) {
      send('chat:read', { user_id: friendId });
    }
  }

  useSocketEvent('chat:message', handleIncoming);

  /**
   * Al ritorno della connessione: i messaggi arrivati nel frattempo, e se intanto
   * l'amicizia è finita o c'è un blocco, la scrittura si chiude (P33).
   */
  async function refresh(): Promise<void> {
    const answer = await send('chat:history', { user_id: friendId, before_id: null });
    if (!answer.ok) {
      return;
    }
    addMessages(answer.data.messages);
    if (!answer.data.can_write) {
      let reason = closedText(answer.data.cannot_write);
      if (reason === '') {
        reason = CLOSED_DEFAULT;
      }
      disableWriting(reason);
    }
  }

  /** Effetto: a ogni cambio della connessione; al ritorno (non al primo collegamento) refresh. */
  function followConnection(): void {
    if (status !== 'connected') {
      return;
    }
    if (wasOnline.current) {
      refresh();
    }
    wasOnline.current = true;
  }

  // [status]: si rifà a ogni cambio di stato della connessione
  useEffect(followConnection, [status]);

  /**
   * "Messaggi precedenti": chiede quelli prima del più vecchio già caricato
   * (contratto 5.4, before_id) e li mette in cima, restando sul punto che si leggeva.
   */
  async function handleLoadMore(): Promise<void> {
    if (loadingMore || !hasMore) {
      return;
    }
    setLoadingMore(true);
    let oldest: number | null = null;
    if (messages.length > 0) {
      oldest = messages[0].id;
    }
    const answer = await send('chat:history', { user_id: friendId, before_id: oldest });
    if (answer.ok) {
      let height = 0;
      if (listRef.current !== null) {
        height = listRef.current.scrollHeight;
      }
      scrollAfter.current = { mode: 'keep', height: height };
      const older = answer.data.messages;

      /** setMessages con una funzione: riceve l'elenco più recente. */
      function update(current: ChatMessage[]): ChatMessage[] {
        return prependOld(current, older);
      }

      setMessages(update);
      setHasMore(answer.data.has_more);
    } else {
      setError(answer.error.message);
    }
    setLoadingMore(false);
  }

  /** La casella è cambiata. */
  function handleChange(event: ChangeEvent<HTMLInputElement>): void {
    setText(event.target.value);
  }

  /**
   * P81: toccando "Invia" il fuoco passava al pulsante e il telefono chiudeva la
   * tastiera. Il pulsante non prende il fuoco (il clic resta); vale su tutto il
   * modulo, così anche per un tocco sul pulsante spento durante l'invio.
   */
  function handleFormMouseDown(event: MouseEvent<HTMLFormElement>): void {
    if (event.target !== inputRef.current) {
      event.preventDefault();
    }
  }

  /**
   * Invio del modulo: controlla il testo come il server (niente messaggi vuoti o di
   * soli spazi, al massimo MAX_LENGTH caratteri), poi lo manda con chat:send.
   * "Invia" resta spento finché il server non risponde (niente doppio invio).
   */
  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (sendingNow.current || !canWrite || offline) {
      return;
    }
    const value = text;
    if (value.trim() === '') {
      setError('Scrivi un messaggio.');
      return;
    }
    if (value.length > MAX_LENGTH) {
      setError(`Al massimo ${MAX_LENGTH} caratteri.`);
      return;
    }
    if (!navigator.onLine) {
      setError('Sei offline: il messaggio partirà quando torna la connessione. Riprova tra poco.');
      return;
    }
    setError('');
    sendingNow.current = true;
    setSending(true);

    // closed: true se il server dice che non si può più scrivere
    let closed = false;
    const answer = await send('chat:send', { request_id: newRequestId(), user_id: friendId, text: value });
    if (answer.ok) {
      setText('');
      addMessages([answer.data.message]);
    } else {
      setError(answer.error.message);
      if (answer.error.code === 'blocked' || answer.error.code === 'not_friends') {
        closed = true;
        disableWriting(answer.error.message);
      }
    }
    sendingNow.current = false;
    setSending(false);
    if (!closed && inputRef.current !== null) {
      inputRef.current.focus();
    }
  }

  // items: i messaggi, costruiti con un for prima del return.
  // key: il "nome" con cui React riconosce lo stesso messaggio tra un disegno e
  // l'altro (il suo id), così non lo ricrea quando ne arriva uno nuovo
  const items: JSX.Element[] = [];
  for (let i = 0; i < messages.length; i++) {
    const message = messages[i];
    let className = 'chat__msg';
    if (message.from_user_id === props.meId) {
      className = 'chat__msg chat__msg--mine';
    }
    items.push(
      <li key={message.id} className={className} data-message-id={message.id}>
        {message.text}
        <span className="chat__time">{timeOf(message.sent_at)}</span>
      </li>,
    );
  }
  if (messages.length === 0) {
    items.push(<li key="empty" className="chat__empty" data-chat-empty="">Nessun messaggio: scrivi tu per primo.</li>);
  }

  // noticeElement: la frase in cima, solo se c'è
  let noticeElement: JSX.Element | null = null;
  if (notice !== '') {
    noticeElement = <p className="chat__notice" data-chat-notice="">{notice}</p>;
  }

  // placeholder e sendDisabled: la casella e "Invia" a seconda di cosa si può fare
  let placeholder = 'Scrivi un messaggio';
  if (!canWrite) {
    placeholder = 'Non puoi più scrivere a questo utente';
  }
  let sendDisabled = false;
  if (!canWrite || sending || offline) {
    sendDisabled = true;
  }

  // offlineAttribute: data-offline c'è solo senza connessione (undefined = niente attributo)
  let offlineAttribute: string | undefined = undefined;
  if (offline) {
    offlineAttribute = '';
  }

  let errorHidden = true;
  if (error !== '') {
    errorHidden = false;
  }

  return (
    <div
      className="drawer__view chat"
      data-view="chat"
      data-chat-with={friendId}
      data-offline={offlineAttribute}
      aria-labelledby="chat-title"
    >
      <div className="drawer__head">
        <button className="icon-btn" type="button" aria-label="Torna agli amici" data-chat-back="" onClick={props.onBack}>
          <span className="icon" aria-hidden="true">arrow_back</span>
        </button>
        <div className="chat__title">
          <h2 className="drawer__title" id="chat-title">{props.friend.username}</h2>
          <span className="chat__presence">{PRESENCE_LABEL[props.friend.presence]}</span>
        </div>
        <button className="icon-btn" type="button" aria-label="Chiudi" onClick={props.onClose}>
          <span className="icon" aria-hidden="true">close</span>
        </button>
      </div>
      {noticeElement}
      <ol className="chat__messages" aria-live="polite" data-chat-messages="" ref={listRef} onScroll={handleScroll}>
        <li className="chat__empty" hidden={!hasMore}>
          <button className="btn btn--ghost btn--small" type="button" data-chat-more="" disabled={loadingMore} onClick={handleLoadMore}>
            Messaggi precedenti
          </button>
        </li>
        {items}
      </ol>
      <form className="chat__form" noValidate data-chat-form="" onMouseDown={handleFormMouseDown} onSubmit={handleSubmit}>
        <label className="visually-hidden" htmlFor="chat-input">Scrivi un messaggio</label>
        <input
          className="input"
          id="chat-input"
          name="text"
          type="text"
          autoComplete="off"
          maxLength={MAX_LENGTH}
          placeholder={placeholder}
          disabled={!canWrite}
          value={text}
          onChange={handleChange}
          ref={inputRef}
        />
        <button className="icon-btn icon-btn--filled" type="submit" aria-label="Invia messaggio" disabled={sendDisabled}>
          <span className="icon" aria-hidden="true">send</span>
        </button>
        <p className="chat__error" role="alert" hidden={errorHidden} data-chat-error="">{error}</p>
      </form>
    </div>
  );
}
