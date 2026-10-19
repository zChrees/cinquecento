/**
 * Il pannello amici (P46, passo 5b della migrazione): si apre da "Amici" nella
 * navbar. Su telefono è a tutto schermo, su computer laterale (stile in
 * css/components/friends-panel.css). È la versione React di
 * app/static/js/components/FriendsPanel.js, con lo stesso HTML e gli stessi data-*.
 *
 * Cosa contiene:
 *   <FriendsPanel onBadge={setBadge} />   il pannello (un <dialog> sempre nella pagina, chiuso)
 *   useOpenFriendsPanel()                 la funzione che lo apre (la usa il pulsante della navbar)
 *
 * Dentro: cerca uno username (esatto, D33) e manda la richiesta; richieste
 * ricevute (accetta, rifiuta); amici online, in partita e offline con i messaggi
 * non letti, "Chatta" e "Altro" (rimuovi, blocca, con conferma); richieste mandate
 * (annulla); bloccati (sblocca). Gli inviti a partita stanno solo nella home (P46).
 * La chat arriva con il lotto 5c: per ora "Chatta" scrive solo un avviso (scelta
 * di Christian, 19/10/2026); i suoni del menu (P115) arrivano anche loro con il 5c.
 *
 * La lista si aggiorna da sola (P47): con friends:presence, friends:changed e
 * chat:message si rilegge GET /friends/, e conta solo la risposta dell'ultima
 * lettura partita (P63, P65). Anche al ritorno della connessione (P33).
 *
 * Si chiude con la X, con Esc, toccando fuori e con "indietro" del browser o del
 * telefono. Per "indietro" il pannello aperto è un passo della cronologia: aprirlo
 * aggiunge un passo con lo stato { friendsPanel: 'list' } (React Router, navigate),
 * e il pannello è aperto finché l'indirizzo attuale ha quello stato.
 *
 * DA DOVE ARRIVANO I DATI: la lista da GET /friends/ (api/friends.ts, contratto 2.2),
 * chi sei dalla sessione (useSession), gli avvisi dal tempo reale (socket/hooks.ts).
 */

import { useEffect, useRef, useState } from 'react';
import type { ChangeEvent, FormEvent, JSX, MouseEvent, RefObject, SyntheticEvent } from 'react';
import { useLocation, useNavigate } from 'react-router';
import type { Answer } from '../api/client';
import {
  acceptRequest,
  blockUser,
  cancelRequest,
  declineRequest,
  fetchFriends,
  removeFriend,
  sendFriendRequest,
  unblockUser,
} from '../api/friends';
import { useSession } from '../session/SessionContext';
import { useConnection, useSocketEvent } from '../socket/hooks';
import type { Friend, FriendRequest, FriendsList } from '../types/api';
import type { UserRef } from '../types/common';
import type { ChatMessage } from '../types/events';
import { newRequestId } from '../utils/requestId';
import { FriendsBody } from './FriendRows';
import type { FriendsHandlers } from './FriendRows';
import { Modal } from './Modal';
import type { ModalAction } from './Modal';
import { sheetControls } from './sheet';

// PAGE_ID: un codice diverso a ogni apertura della pagina, salvato insieme allo
// stato del pannello nella cronologia. Dopo un ricaricamento il browser tiene
// ancora lo stato { friendsPanel: 'list' } del passo in cui eravamo (P34), ma il
// codice è cambiato: così quello stato vecchio vale come "pannello chiuso", e il
// pannello non si riapre da solo né rovina "indietro".
const PAGE_ID: string = newRequestId();

// PanelLayer: cosa mostra il pannello aperto. Per ora solo la lista; con il lotto
// 5c anche 'chat' (dalla chat, "indietro" tornerà alla lista)
export type PanelLayer = 'list';

// PanelHistoryState: lo stato salvato nella cronologia quando il pannello è aperto
interface PanelHistoryState {
  // cosa mostra il pannello
  friendsPanel: PanelLayer;
  // il codice della pagina che l'ha aperto (PAGE_ID)
  page: string;
}

// Notice: l'avviso in cima alla lista, per esempio "Richiesta inviata a Giulia."
interface Notice {
  // il testo; '' per nessun avviso
  text: string;
  // 'ok' (verde) oppure 'error' (rosso), in data-kind (friends-panel.css)
  kind: 'ok' | 'error';
}

// ModalStep: la finestra aperta sopra il pannello per un amico:
// 'more' (rimuovi o blocca?), 'remove' e 'block' (le conferme, rosse)
interface ModalStep {
  kind: 'more' | 'remove' | 'block';
  friend: Friend;
}

// I testi delle finestre e degli avvisi (gli stessi di FriendsPanel.js)
const NOT_AVAILABLE = 'Amici non disponibili. Riprova tra poco.';
const CHAT_LATER = 'La chat arriva con il prossimo lotto della migrazione (5c).';
const NO_NOTICE: Notice = { text: '', kind: 'ok' };

/**
 * Dice cosa mostra il pannello, dallo stato della cronologia.
 *
 * @param {unknown} state lo stato del passo attuale (location.state di React Router)
 * @returns {PanelLayer | null} 'list', oppure null se il pannello è chiuso
 *
 * In parole semplici:
 *   panelLayer({ friendsPanel: 'list', page: PAGE_ID })  →  'list'
 *   panelLayer(null)                                      →  null
 *   Lo stato arriva dal browser e può essere qualunque cosa (unknown): si
 *   controlla campo per campo prima di usarlo.
 */
function panelLayer(state: unknown): PanelLayer | null {
  if (typeof state !== 'object' || state === null) {
    return null;
  }
  // "'page' in state": l'oggetto ha il campo page (dopo il controllo TypeScript lo sa)
  if (!('page' in state) || !('friendsPanel' in state)) {
    return null;
  }
  if (state.page !== PAGE_ID) {
    return null;
  }
  if (state.friendsPanel === 'list') {
    return 'list';
  }
  return null;
}

/**
 * La funzione che apre il pannello amici: la usa il pulsante "Amici" della navbar.
 *
 * @returns {() => void} la funzione da chiamare al clic
 *
 * In parole semplici:
 *   const openFriends = useOpenFriendsPanel();
 *   <button onClick={openFriends}>
 *   Aggiunge un passo alla cronologia, con lo stesso indirizzo e lo stato del
 *   pannello: FriendsPanel lo vede (useLocation) e si apre. È un hook (usa gli hook
 *   del router), quindi si chiama in cima al componente.
 */
export function useOpenFriendsPanel(): () => void {
  // navigate: la funzione di React Router per cambiare passo nella cronologia;
  // location: il passo attuale (indirizzo e stato)
  const navigate = useNavigate();
  const location = useLocation();

  /** Apre il pannello; un secondo clic mentre è aperto non fa niente. */
  function open(): void {
    if (panelLayer(location.state) !== null) {
      return;
    }
    const state: PanelHistoryState = { friendsPanel: 'list', page: PAGE_ID };
    navigate(
      { pathname: location.pathname, search: location.search, hash: location.hash },
      { state: state, replace: false },
    );
  }

  return open;
}

/**
 * Adatta il pannello aperto alla parte visibile sopra la tastiera del telefono (P128).
 *
 * @param {HTMLDialogElement | null} dialog il pannello
 * @returns {void}
 *
 * In parole semplici:
 *   fitToVisible(dialog)
 *   Su iPhone la tastiera non accorcia la pagina, Safari la sposta in su: il
 *   pannello si mette alto quanto la parte visibile (visualViewport). Non con lo
 *   zoom delle due dita (scale diverso da 1), e non da chiuso: lì tornano le
 *   misure del CSS. element.style.x è permesso dalla CSP (CLAUDE.md, P32).
 */
function fitToVisible(dialog: HTMLDialogElement | null): void {
  if (dialog === null) {
    return;
  }
  const visible = window.visualViewport;
  if (visible !== null && dialog.open && Math.abs(visible.scale - 1) < 0.01) {
    dialog.style.top = `${visible.offsetTop}px`;
    dialog.style.height = `${visible.height}px`;
  } else {
    dialog.style.top = '';
    dialog.style.height = '';
  }
}

/**
 * Dice se un trascinamento partito da target può scorrere un elenco del pannello.
 *
 * @param {Element} target l'elemento toccato
 * @param {HTMLDialogElement} dialog il pannello
 * @returns {boolean}
 *
 * In parole semplici:
 *   scrollsInside(elementoToccato, dialog)
 *   Risale da target fino al pannello e cerca un elemento con overflow-y auto o
 *   scroll che abbia davvero qualcosa da scorrere (P128).
 */
function scrollsInside(target: Element, dialog: HTMLDialogElement): boolean {
  let node: Element | null = target;
  while (node !== null && node !== dialog) {
    const overflowY = getComputedStyle(node).overflowY;
    if ((overflowY === 'auto' || overflowY === 'scroll') && node.scrollHeight > node.clientHeight) {
      return true;
    }
    node = node.parentElement;
  }
  return false;
}

/**
 * Aggiunge un numero a un elenco, se non c'è già, in un elenco nuovo.
 *
 * In parole semplici:
 *   withId([31], 44)  →  [31, 44]
 *   React vuole un elenco nuovo per accorgersi che lo stato è cambiato.
 */
function withId(list: number[], id: number): number[] {
  const result: number[] = [];
  for (let i = 0; i < list.length; i++) {
    if (list[i] !== id) {
      result.push(list[i]);
    }
  }
  result.push(id);
  return result;
}

/**
 * Toglie un numero da un elenco, in un elenco nuovo.
 *
 * In parole semplici:
 *   withoutId([31, 44], 31)  →  [44]
 */
function withoutId(list: number[], id: number): number[] {
  const result: number[] = [];
  for (let i = 0; i < list.length; i++) {
    if (list[i] !== id) {
      result.push(list[i]);
    }
  }
  return result;
}

// FriendsPanelProps: cosa riceve il pannello
interface FriendsPanelProps {
  // la funzione che riceve il numero per il contatore sull'icona "Amici" (richieste
  // ricevute + messaggi non letti, contratto 2.2); la navbar lo disegna.
  // In C: void (*onBadge)(int totale)
  onBadge: (total: number) => void;
}

/**
 * Il pannello amici.
 *
 * @param {FriendsPanelProps} props
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <FriendsPanel onBadge={setBadge} />   (in Navbar.tsx, solo con il login)
 *   Il <dialog> resta sempre nella pagina, chiuso: appena la pagina si apre legge
 *   la lista (per il contatore), e la rilegge a ogni apertura e a ogni avviso.
 */
export function FriendsPanel(props: FriendsPanelProps): JSX.Element {
  // Gli hook si chiamano sempre in cima al componente, mai dentro un if.
  // session: chi è collegato (per riconoscere i propri messaggi)
  const session = useSession();
  // navigate e location: la cronologia (per "indietro" e per sapere se il pannello è aperto)
  const navigate = useNavigate();
  const location = useLocation();
  // status: lo stato della connessione al tempo reale, per esempio 'connected'
  const status = useConnection();

  // useState restituisce due cose: il valore attuale e la funzione per cambiarlo,
  // che fa ridisegnare il componente (regole-codice.md, sezione 6).
  // overview: l'ultima lista arrivata da GET /friends/, oppure null
  const [overview, setOverview] = useState<FriendsList | null>(null);
  // loadError: il messaggio dell'ultima lettura fallita, oppure ''
  const [loadError, setLoadError] = useState<string>('');
  // notice: l'avviso in cima alla lista
  const [notice, setNotice] = useState<Notice>(NO_NOTICE);
  // addValue: il testo scritto nella casella "Cerca uno username"
  const [addValue, setAddValue] = useState<string>('');
  // addError: l'errore sotto la casella, oppure ''
  const [addError, setAddError] = useState<string>('');
  // adding: true mentre la richiesta di amicizia è in viaggio (pulsante spento)
  const [adding, setAdding] = useState<boolean>(false);
  // busy: gli user_id delle righe con un'azione in corso (i loro pulsanti sono spenti)
  const [busy, setBusy] = useState<number[]>([]);
  // modal: la finestra aperta sopra il pannello (rimuovi o blocca), oppure null
  const [modal, setModal] = useState<ModalStep | null>(null);

  // Le ref tengono un valore tra un disegno e l'altro senza far ridisegnare.
  // dialogRef: il <dialog> vero della pagina; inputRef: la casella dello username
  const dialogRef: RefObject<HTMLDialogElement | null> = useRef<HTMLDialogElement>(null);
  const inputRef: RefObject<HTMLInputElement | null> = useRef<HTMLInputElement>(null);
  // loadSeq: il numero dell'ultima lettura partita; solo quella può cambiare la lista
  const loadSeq: RefObject<number> = useRef<number>(0);
  // addingNow: come adding, ma subito (lo stato cambia solo al disegno dopo, e un
  // doppio invio velocissimo lo troverebbe ancora false)
  const addingNow: RefObject<boolean> = useRef<boolean>(false);
  // wasOnline: true dopo il primo collegamento; al ritorno della connessione si rilegge la lista
  const wasOnline: RefObject<boolean> = useRef<boolean>(false);

  const sheet = sheetControls(dialogRef);
  // layer: cosa mostra il pannello secondo la cronologia, oppure null se è chiuso
  const layer = panelLayer(location.state);
  // meId: il tuo user_id; 0 finché la sessione non è arrivata
  let meId = 0;
  if (session.user !== null) {
    meId = session.user.user_id;
  }

  /**
   * Rilegge la lista degli amici.
   *
   * In parole semplici:
   *   await load();
   *   Conta solo la risposta dell'ultima lettura partita (P63): una risposta più
   *   vecchia arrivata dopo non sovrascrive quella nuova. Se la lettura fallisce a
   *   pannello chiuso, il contatore resta com'era; a pannello aperto la lista
   *   lascia il posto al messaggio d'errore con "Riprova".
   */
  async function load(): Promise<void> {
    loadSeq.current = loadSeq.current + 1;
    const seq = loadSeq.current;
    const answer = await fetchFriends();
    if (seq !== loadSeq.current) {
      return;
    }
    if (answer.ok) {
      setOverview(answer.data);
      setLoadError('');
      return;
    }
    let message = NOT_AVAILABLE;
    if (answer.error.code === 'no_connection') {
      message = answer.error.message;
    }
    setLoadError(message);
    const dialog = dialogRef.current;
    if (dialog !== null && dialog.open) {
      setOverview(null);
    }
  }

  /** Effetto all'apertura della pagina: la prima lettura, per il contatore. */
  function loadAtStart(): void {
    load();
  }

  // []: una volta sola, quando il pannello compare nella pagina
  useEffect(loadAtStart, []);

  /** Effetto: il contatore sull'icona segue l'ultima lista. */
  function updateBadge(): void {
    let total = 0;
    if (overview !== null) {
      total = overview.counters.requests_in + overview.counters.unread_messages;
    }
    props.onBadge(total);
  }

  // [overview]: si rifà ogni volta che arriva una lista nuova
  useEffect(updateBadge, [overview]);

  /**
   * Effetto: apre o chiude il <dialog> quando cambia la cronologia (clic su
   * "Amici", oppure "indietro"). All'apertura toglie gli avvisi vecchi e rilegge
   * la lista; la chiusura ha l'animazione di uscita (sheet.ts).
   */
  function followHistory(): void {
    const dialog = dialogRef.current;
    if (dialog === null) {
      return;
    }
    if (layer !== null && !dialog.open) {
      setNotice(NO_NOTICE);
      setAddError('');
      sheet.open();
      fitToVisible(dialog);
      load();
    } else if (layer === null && dialog.open) {
      sheet.close();
    }
  }

  // [layer]: si rifà quando il pannello passa da chiuso ad aperto o viceversa
  useEffect(followHistory, [layer]);

  /**
   * Effetto: le correzioni per il telefono (P128). Il pannello segue la parte
   * visibile quando la tastiera si apre o si chiude; un trascinamento con un dito
   * su una parte che non scorre non passa alla pagina dietro.
   */
  function followPhone(): () => void {
    const dialog = dialogRef.current;
    const visible = window.visualViewport;

    /** La parte visibile ha cambiato misura o posizione. */
    function handleViewport(): void {
      fitToVisible(dialogRef.current);
    }

    /** Un dito si muove sul pannello: con due dita è lo zoom, e si lascia fare. */
    function handleTouchMove(event: TouchEvent): void {
      if (dialog === null || event.touches.length !== 1 || !event.cancelable) {
        return;
      }
      if (!(event.target instanceof Element) || !scrollsInside(event.target, dialog)) {
        event.preventDefault();
      }
    }

    if (visible !== null) {
      visible.addEventListener('resize', handleViewport);
      visible.addEventListener('scroll', handleViewport);
    }
    // passive: false serve per poter chiamare preventDefault (React non lo permette
    // con onTouchMove, per questo l'ascolto si aggiunge a mano)
    if (dialog !== null) {
      dialog.addEventListener('touchmove', handleTouchMove, { passive: false });
    }

    /** Pulizia: toglie gli ascolti quando il pannello sparisce. */
    function stopFollowing(): void {
      if (visible !== null) {
        visible.removeEventListener('resize', handleViewport);
        visible.removeEventListener('scroll', handleViewport);
      }
      if (dialog !== null) {
        dialog.removeEventListener('touchmove', handleTouchMove);
      }
    }

    return stopFollowing;
  }

  // []: una volta sola
  useEffect(followPhone, []);

  /**
   * Effetto: al ritorno della connessione (non al primo collegamento) si rilegge
   * la lista, perché nel frattempo gli avvisi del tempo reale non sono arrivati (P33).
   */
  function followConnection(): void {
    if (status !== 'connected') {
      return;
    }
    if (wasOnline.current) {
      load();
    }
    wasOnline.current = true;
  }

  // [status]: si rifà a ogni cambio di stato della connessione
  useEffect(followConnection, [status]);

  /** Un amico entra, esce, comincia o finisce una partita (P47): si rilegge la lista. */
  function handlePresence(): void {
    load();
  }

  /** Richieste, amicizie o blocchi cambiati (P47): si rilegge la lista. */
  function handleFriendsChanged(): void {
    load();
  }

  /**
   * Arriva un messaggio della chat (P48): se è di un amico, cambia il numero dei
   * non letti e si rilegge la lista. I tuoi (mandati da un'altra scheda) no.
   */
  function handleChatMessage(data: { message: ChatMessage }): void {
    if (data.message.from_user_id !== meId) {
      load();
    }
  }

  useSocketEvent('friends:presence', handlePresence);
  useSocketEvent('friends:changed', handleFriendsChanged);
  useSocketEvent('chat:message', handleChatMessage);

  /**
   * Chiude il pannello: con il pannello nella cronologia si torna indietro di un
   * passo (e followHistory lo chiude), altrimenti si chiude e basta.
   */
  function requestClose(): void {
    if (layer !== null) {
      navigate(-1);
    } else {
      sheet.close();
    }
  }

  /** Esc: il browser chiuderebbe subito; si chiude come con la X. */
  function handleCancel(event: SyntheticEvent<HTMLDialogElement>): void {
    event.preventDefault();
    requestClose();
  }

  /**
   * Clic sul <dialog> stesso: se è fuori dal riquadro (sullo sfondo scuro) chiude.
   * Si misura il riquadro perché un clic sul bordo interno arriva anche lui al <dialog>.
   */
  function handleBackdropClick(event: MouseEvent<HTMLDialogElement>): void {
    const dialog = dialogRef.current;
    if (dialog === null || event.target !== dialog) {
      return;
    }
    const box = dialog.getBoundingClientRect();
    if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) {
      requestClose();
    }
  }

  /** Il <dialog> si è chiuso: tornano le misure del CSS (P128). */
  function handleClosed(): void {
    fitToVisible(dialogRef.current);
  }

  /**
   * Un'azione su una riga: spegne i pulsanti della riga, manda la richiesta,
   * scrive l'avviso e rilegge la lista.
   *
   * @param {number} userId l'utente della riga
   * @param {() => Promise<Answer<null>>} request la funzione che manda la richiesta
   * @param {string} okText l'avviso se va bene, per esempio 'Ora tu e Giulia siete amici.'
   *
   * In parole semplici:
   *   act(31, sendAccept, 'Ora tu e Giulia siete amici.');
   *   Se il server rifiuta, l'avviso è il suo messaggio, in rosso.
   */
  async function act(userId: number, request: () => Promise<Answer<null>>, okText: string): Promise<void> {
    // setBusy con una funzione: riceve l'elenco più recente (anche se nel
    // frattempo è partita un'altra azione) e restituisce quello nuovo
    function addBusy(current: number[]): number[] {
      return withId(current, userId);
    }

    function removeBusy(current: number[]): number[] {
      return withoutId(current, userId);
    }

    setBusy(addBusy);
    const answer = await request();
    if (answer.ok) {
      setNotice({ text: okText, kind: 'ok' });
    } else {
      setNotice({ text: answer.error.message, kind: 'error' });
    }
    await load();
    setBusy(removeBusy);
  }

  /** "Accetta" di una richiesta ricevuta. */
  function handleAccept(request: FriendRequest): void {
    function send(): Promise<Answer<null>> {
      return acceptRequest(request.user_id);
    }
    act(request.user_id, send, `Ora tu e ${request.username} siete amici.`);
  }

  /** "Rifiuta" di una richiesta ricevuta. */
  function handleDecline(request: FriendRequest): void {
    function send(): Promise<Answer<null>> {
      return declineRequest(request.user_id);
    }
    act(request.user_id, send, `Richiesta di ${request.username} rifiutata.`);
  }

  /** "Annulla" di una richiesta mandata. */
  function handleCancelRequest(request: FriendRequest): void {
    function send(): Promise<Answer<null>> {
      return cancelRequest(request.user_id);
    }
    act(request.user_id, send, `Richiesta a ${request.username} annullata.`);
  }

  /** "Sblocca" di un utente bloccato. */
  function handleUnblock(user: UserRef): void {
    function send(): Promise<Answer<null>> {
      return unblockUser(user.user_id);
    }
    act(user.user_id, send, `${user.username} non è più bloccato.`);
  }

  /** "Chatta": la chat arriva con il lotto 5c, per ora solo un avviso. */
  function handleChat(): void {
    setNotice({ text: CHAT_LATER, kind: 'ok' });
  }

  /** "Altro": la finestra con Rimuovi amico e Blocca. */
  function handleMore(friend: Friend): void {
    setModal({ kind: 'more', friend: friend });
  }

  /** "Riprova" quando la lista non è arrivata. */
  function handleRetry(): void {
    load();
  }

  /**
   * Una finestra sopra il pannello si è chiusa con la scelta value (null = chiusa
   * con la X, Esc o un tocco fuori).
   *
   * In parole semplici:
   *   Dalla prima finestra ("Cosa vuoi fare?") si passa alla conferma, rossa; dalla
   *   conferma, con "Rimuovi" o "Blocca", parte la richiesta.
   */
  function handleModalDone(value: string | null): void {
    if (modal === null) {
      return;
    }
    const step = modal;
    const friend = step.friend;
    setModal(null);

    if (step.kind === 'more') {
      if (value === 'remove') {
        setModal({ kind: 'remove', friend: friend });
      } else if (value === 'block') {
        setModal({ kind: 'block', friend: friend });
      }
      return;
    }
    if (value !== 'confirm') {
      return;
    }

    if (step.kind === 'remove') {
      function sendRemove(): Promise<Answer<null>> {
        return removeFriend(friend.user_id);
      }
      act(friend.user_id, sendRemove, `${friend.username} non è più tuo amico.`);
    } else {
      function sendBlock(): Promise<Answer<null>> {
        return blockUser(friend.user_id);
      }
      act(friend.user_id, sendBlock, `${friend.username} è bloccato.`);
    }
  }

  /** La casella dello username è cambiata. */
  function handleAddChange(event: ChangeEvent<HTMLInputElement>): void {
    setAddValue(event.target.value);
  }

  /**
   * Invio del modulo "Cerca uno username": manda la richiesta di amicizia.
   * Il pulsante resta spento finché il server non risponde (niente doppioni).
   */
  async function handleAddSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (addingNow.current) {
      return;
    }
    const username = addValue;
    if (username === '') {
      setAddError('Scrivi uno username.');
      if (inputRef.current !== null) {
        inputRef.current.focus();
      }
      return;
    }
    setAddError('');
    addingNow.current = true;
    setAdding(true);
    const answer = await sendFriendRequest(username);
    if (answer.ok) {
      setAddValue('');
      setNotice({ text: `Richiesta inviata a ${answer.data.username}.`, kind: 'ok' });
      await load();
    } else {
      setAddError(answer.error.message);
    }
    addingNow.current = false;
    setAdding(false);
  }

  /** La X in alto. */
  function handleCloseClick(): void {
    requestClose();
  }

  // handlers: le azioni dei pulsanti della lista (FriendRows.tsx)
  const handlers: FriendsHandlers = {
    onAccept: handleAccept,
    onDecline: handleDecline,
    onChat: handleChat,
    onMore: handleMore,
    onCancel: handleCancelRequest,
    onUnblock: handleUnblock,
    onRetry: handleRetry,
  };

  // modalElement: la finestra sopra il pannello, decisa con un if prima del return.
  // key: cambia a ogni finestra, così React ne crea una nuova (con il suo stato
  // da capo) invece di riusare quella appena chiusa
  let modalElement: JSX.Element | null = null;
  if (modal !== null) {
    const name = modal.friend.username;
    let title = name;
    let message = 'Cosa vuoi fare?';
    let actions: ModalAction[] = [
      { label: 'Rimuovi amico', value: 'remove', variant: 'ghost' },
      // la conferma, dopo, è rossa
      { label: 'Blocca', value: 'block', variant: 'ghost' },
    ];
    if (modal.kind === 'remove') {
      title = `Togliere ${name} dagli amici?`;
      message = 'Sparirà dalla tua lista e tu dalla sua. Potrete mandarvi di nuovo una richiesta.';
      actions = [
        { label: 'Annulla', value: 'cancel', variant: 'ghost' },
        { label: 'Rimuovi', value: 'confirm', variant: 'danger' },
      ];
    } else if (modal.kind === 'block') {
      title = `Bloccare ${name}?`;
      message = 'Non potrà mandarti richieste né messaggi, e non sarete più amici. Puoi sbloccarlo quando vuoi.';
      actions = [
        { label: 'Annulla', value: 'cancel', variant: 'ghost' },
        { label: 'Blocca', value: 'confirm', variant: 'danger' },
      ];
    }
    modalElement = (
      <Modal
        key={`${modal.kind}-${modal.friend.user_id}`}
        title={title}
        message={message}
        actions={actions}
        footer={null}
        onDone={handleModalDone}
      />
    );
  }

  // noticeHidden, addErrorHidden: l'avviso e l'errore si vedono solo con un testo
  let noticeHidden = true;
  if (notice.text !== '') {
    noticeHidden = false;
  }
  let addErrorHidden = true;
  if (addError !== '') {
    addErrorHidden = false;
  }

  // <> ... </>: un contenitore che non diventa un elemento della pagina
  return (
    <>
      <dialog
        className="drawer"
        id="friends"
        aria-labelledby="friends-title"
        data-animated=""
        data-friends-panel=""
        ref={dialogRef}
        onCancel={handleCancel}
        onClick={handleBackdropClick}
        onClose={handleClosed}
      >
        <div className="drawer__view" data-view="list">
          <div className="drawer__head">
            <h2 className="drawer__title" id="friends-title">Amici</h2>
            <button className="icon-btn" type="button" aria-label="Chiudi" onClick={handleCloseClick}>
              <span className="icon" aria-hidden="true">close</span>
            </button>
          </div>
          <p className="friends-notice" role="status" hidden={noticeHidden} data-friends-notice="" data-kind={notice.kind}>
            {notice.text}
          </p>
          <form className="add-friend" noValidate data-add-friend="" onSubmit={handleAddSubmit}>
            <label className="visually-hidden" htmlFor="add-friend-input">Username esatto dell'amico da aggiungere</label>
            <input
              className="input"
              id="add-friend-input"
              name="username"
              type="text"
              maxLength={20}
              placeholder="Cerca uno username"
              autoComplete="off"
              autoCapitalize="off"
              spellCheck={false}
              value={addValue}
              onChange={handleAddChange}
              ref={inputRef}
            />
            <button className="btn btn--primary btn--small" type="submit" disabled={adding}>
              <span className="icon" aria-hidden="true">person_add</span>Invia
            </button>
            <p className="add-friend__error" role="alert" hidden={addErrorHidden} data-add-friend-error="">
              {addError}
            </p>
          </form>
          <div data-friends-body="">
            <FriendsBody overview={overview} loadError={loadError} busy={busy} handlers={handlers} />
          </div>
        </div>
      </dialog>
      {modalElement}
    </>
  );
}
