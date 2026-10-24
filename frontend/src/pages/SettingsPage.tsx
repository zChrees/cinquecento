/**
 * La pagina delle impostazioni (P17, passo 6 della migrazione): /profile/settings.
 * (Stile in css/pages/profile.css, più layout.css, form.css e button.css).
 *
 * Cosa contiene:
 *   <SettingsPage />   tre parti:
 *   - Avatar: la griglia con "Iniziale" e gli avatar del set; "Salva l'avatar" lo
 *     salva e ricarica la pagina con "Avatar salvato." (come prima);
 *   - Suoni (P103, P115): l'interruttore, che salva subito la scelta nel browser
 *     (utils/sounds.ts) e non passa dal server;
 *   - Cancella l'account: una finestra nella pagina chiede la password; se il server
 *     la accetta l'utente esce e va alla home con "Account cancellato...".
 * Senza connessione niente parte: compare la finestra "Nessuna connessione". Gli
 * errori del server compaiono in basso, come i messaggi di prima. I pulsanti si
 * spengono finché non arriva la risposta (niente doppio clic).
 *
 * DA DOVE ARRIVANO I DATI: chi sei (nome e avatar attuale) dalla sessione
 * (useSession); gli avatar da GET /api/profile/avatars; salvataggio e cancellazione
 * con le rotte di api/profile.ts.
 */

import { useEffect, useState } from 'react';
import type { ChangeEvent, FormEvent, JSX, KeyboardEvent } from 'react';
import { deleteAccount, fetchAvatars, saveAvatar } from '../api/profile';
import { Avatar } from '../components/Avatar';
import { Modal } from '../components/Modal';
import type { ModalAction } from '../components/Modal';
import { OfflineModal } from '../components/OfflineModal';
import { useSession } from '../session/SessionContext';
import type { AvatarChoice } from '../types/api';
import { setSoundsEnabled, soundsEnabled } from '../utils/sounds';
import { FormPage, useSessionFlashes } from './FormPage';

// AVATARS_NOT_AVAILABLE: il messaggio se l'elenco degli avatar non arriva
const AVATARS_NOT_AVAILABLE = 'Avatar non disponibili. Riprova tra poco.';

// DELETE_ACTIONS: i pulsanti della finestra di conferma (la scelta rossa per ultima)
const DELETE_ACTIONS: ModalAction[] = [
  { label: 'Annulla', value: 'cancel', variant: 'ghost' },
  { label: "Cancella l'account", value: 'confirm', variant: 'danger' },
];

/**
 * La pagina delle impostazioni.
 *
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <SettingsPage />   (routes.tsx, indirizzo /profile/settings)
 *   Flask la manda solo con il login; in sviluppo (Vite) senza login rimanda
 *   all'accesso da sé.
 */
export function SettingsPage(): JSX.Element {
  // Gli hook si chiamano sempre in cima al componente, mai dentro un if.
  // session: chi è collegato (nome per l'iniziale, avatar attuale)
  const session = useSession();
  // useState restituisce due cose: il valore attuale e la funzione per cambiarlo,
  // che fa ridisegnare il componente (regole-codice.md, sezione 6).
  // flashes: i messaggi in basso (quelli lasciati dal server, poi gli errori)
  const [flashes, setFlashes] = useSessionFlashes();
  // choices: gli avatar del set, oppure null finché non arrivano
  const [choices, setChoices] = useState<AvatarChoice[] | null>(null);
  // selected: il codice scelto nella griglia ('' = l'iniziale)
  const [selected, setSelected] = useState<string>('');
  // savingAvatar e deleting: true mentre la richiesta è in viaggio (pulsante spento)
  const [savingAvatar, setSavingAvatar] = useState<boolean>(false);
  const [deleting, setDeleting] = useState<boolean>(false);
  // soundsOn: l'interruttore dei suoni
  const [soundsOn, setSoundsOn] = useState<boolean>(soundsEnabled());
  // confirming: true mentre è aperta la finestra con la password
  const [confirming, setConfirming] = useState<boolean>(false);
  // password: quello che è scritto nella finestra di conferma
  const [password, setPassword] = useState<string>('');
  // offline: true mentre è aperta la finestra "Nessuna connessione"
  const [offline, setOffline] = useState<boolean>(false);

  /** Effetto: chiede l'elenco degli avatar, una volta. */
  function loadAvatars(): () => void {
    // active: false se la pagina sparisce prima della risposta
    let active = true;

    async function read(): Promise<void> {
      const answer = await fetchAvatars();
      if (!active) {
        return;
      }
      if (answer.ok) {
        setChoices(answer.data.avatars);
      } else {
        setFlashes([{ kind: 'error', message: AVATARS_NOT_AVAILABLE }]);
      }
    }

    function stop(): void {
      active = false;
    }

    read();
    return stop;
  }

  // []: una volta sola, all'apertura della pagina
  useEffect(loadAvatars, []);

  /**
   * Effetto quando arriva la sessione: la griglia parte dall'avatar attuale. Senza
   * login (solo in sviluppo, con Vite: Flask non manda la pagina) si va all'accesso.
   */
  function followSession(): void {
    if (!session.loaded) {
      return;
    }
    if (session.user === null) {
      window.location.assign('/auth/login?next=/profile/settings');
      return;
    }
    let current = '';
    if (session.user.avatar !== null) {
      current = session.user.avatar;
    }
    setSelected(current);
  }

  // [session.loaded]: si rifà quando la sessione arriva
  useEffect(followSession, [session.loaded]);

  /**
   * Effetto: tornando indietro a questa pagina (copia del browser, "pageshow") i
   * pulsanti si riaccendono, la password si dimentica e l'interruttore rilegge la scelta.
   */
  function listenPageShow(): () => void {
    function handlePageShow(): void {
      setSavingAvatar(false);
      setDeleting(false);
      setPassword('');
      setSoundsOn(soundsEnabled());
    }

    window.addEventListener('pageshow', handlePageShow);

    function stop(): void {
      window.removeEventListener('pageshow', handlePageShow);
    }

    return stop;
  }

  // []: una volta sola
  useEffect(listenPageShow, []);

  /** Una scelta della griglia. */
  function handleAvatarChange(event: ChangeEvent<HTMLInputElement>): void {
    setSelected(event.target.value);
  }

  /**
   * "Salva l'avatar": senza rete la finestra "Nessuna connessione"; se va bene la
   * pagina si ricarica e mostra "Avatar salvato." (la navbar ha l'avatar nuovo).
   */
  async function handleAvatarSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!navigator.onLine) {
      setOffline(true);
      return;
    }
    if (savingAvatar) {
      return;
    }
    setSavingAvatar(true);
    const answer = await saveAvatar(selected);
    if (answer.ok) {
      window.location.assign(answer.data.redirect);
      return;
    }
    setSavingAvatar(false);
    setFlashes([{ kind: 'error', message: answer.error.message }]);
  }

  /** L'interruttore dei suoni: la scelta si salva subito nel browser. */
  function handleSoundsChange(event: ChangeEvent<HTMLInputElement>): void {
    setSoundsOn(event.target.checked);
    setSoundsEnabled(event.target.checked);
  }

  /** "Cancella l'account": apre la finestra che chiede la password. */
  function handleDeleteOpen(): void {
    setPassword('');
    setConfirming(true);
  }

  /** La casella della password nella finestra. */
  function handlePasswordChange(event: ChangeEvent<HTMLInputElement>): void {
    setPassword(event.target.value);
  }

  /**
   * Invio nella casella della password = "Cancella l'account" (come prima).
   * Il pulsante rosso lo trova nella finestra che contiene la casella.
   */
  function handlePasswordKeyDown(event: KeyboardEvent<HTMLInputElement>): void {
    if (event.key !== 'Enter') {
      return;
    }
    event.preventDefault();
    const dialog = event.currentTarget.closest('dialog');
    if (dialog === null) {
      return;
    }
    const confirm = dialog.querySelector('.btn--danger');
    if (confirm instanceof HTMLButtonElement) {
      confirm.click();
    }
  }

  /**
   * La finestra di conferma si è chiusa: con "Cancella l'account" manda la
   * password al server. Se va bene si va alla home (l'utente è uscito).
   */
  async function handleDeleteDone(value: string | null): Promise<void> {
    setConfirming(false);
    if (value !== 'confirm') {
      return;
    }
    if (!navigator.onLine) {
      setOffline(true);
      return;
    }
    setDeleting(true);
    const answer = await deleteAccount(password);
    setPassword('');
    if (answer.ok) {
      window.location.assign(answer.data.redirect);
      return;
    }
    setDeleting(false);
    setFlashes([{ kind: 'error', message: answer.error.message }]);
  }

  /** La finestra "Nessuna connessione" si è chiusa. */
  function handleOfflineDone(): void {
    setOffline(false);
  }

  // username: il nome per l'iniziale ('' finché la sessione non arriva)
  let username = '';
  if (session.user !== null) {
    username = session.user.username;
  }

  // items: le scelte della griglia, costruite con un for prima del return.
  // key: il "nome" con cui React riconosce la stessa scelta tra un disegno e l'altro
  const items: JSX.Element[] = [
    <label key="" className="avatar-choice" data-avatar="">
      <input
        className="avatar-choice__input"
        type="radio"
        name="avatar"
        value=""
        checked={selected === ''}
        onChange={handleAvatarChange}
      />
      <span className="avatar-choice__face" aria-hidden="true">{username.charAt(0).toUpperCase()}</span>
      <span className="avatar-choice__name">Iniziale</span>
    </label>,
  ];
  if (choices !== null) {
    for (let i = 0; i < choices.length; i++) {
      const choice = choices[i];
      items.push(
        <label key={choice.code} className="avatar-choice" data-avatar={choice.code}>
          <input
            className="avatar-choice__input"
            type="radio"
            name="avatar"
            value={choice.code}
            checked={selected === choice.code}
            onChange={handleAvatarChange}
          />
          <Avatar username={username} avatar={choice.code} className="avatar-choice__face" />
          <span className="avatar-choice__name">{choice.name}</span>
        </label>,
      );
    }
  }

  // confirmModal e offlineModal: le finestre aperte sopra la pagina, decise con un if prima del return
  let confirmModal: JSX.Element | null = null;
  if (confirming) {
    const field = (
      <div className="field">
        <label className="field__label" htmlFor="delete-password">Password</label>
        <input
          className="input"
          type="password"
          id="delete-password"
          autoComplete="current-password"
          required
          value={password}
          onChange={handlePasswordChange}
          onKeyDown={handlePasswordKeyDown}
          data-autofocus=""
        />
      </div>
    );
    confirmModal = (
      <Modal
        title="Cancellare l'account?"
        message="Non si può annullare. Per confermare scrivi la tua password."
        content={field}
        actions={DELETE_ACTIONS}
        footer={null}
        onDone={handleDeleteDone}
      />
    );
  }
  let offlineModal: JSX.Element | null = null;
  if (offline) {
    offlineModal = <OfflineModal onDone={handleOfflineDone} />;
  }

  return (
    <FormPage name="settings" title="Impostazioni · Cinquecento" flashes={flashes}>
      <section className="panel settings" data-settings="">
        <h1 className="settings__title">Impostazioni</h1>

        <form className="form" method="post" noValidate data-avatar-form="" onSubmit={handleAvatarSubmit}>
          <fieldset className="settings__group">
            <legend className="settings__subtitle">Avatar</legend>
            <div className="avatar-grid">{items}</div>
          </fieldset>
          <div className="form__actions">
            <button className="btn btn--primary" type="submit" disabled={savingAvatar} data-avatar-submit="">
              Salva l'avatar
            </button>
          </div>
        </form>

        <section className="settings__group" data-sounds="">
          <h2 className="settings__subtitle">Suoni</h2>
          <label className="switch">
            <span className="switch__text">Suoni</span>
            <input
              className="switch__input"
              type="checkbox"
              role="switch"
              checked={soundsOn}
              onChange={handleSoundsChange}
              data-sounds-toggle=""
            />
            <span className="switch__track" aria-hidden="true"></span>
          </label>
          <p className="settings__text">
            Al tavolo carte, mescolata, canti, frasi, il tuo turno e la fine della partita; nel menu richieste
            di amicizia, messaggi e inviti. La scelta vale per questo browser.
          </p>
        </section>

        <section className="settings__group settings__danger" data-delete="">
          <h2 className="settings__subtitle">Cancella l'account</h2>
          <p className="settings__text">
            Rating, amici e messaggi spariscono per sempre. Le partite giocate restano, con "utente eliminato" al
            posto del tuo nome.
          </p>
          {/* Il contenitore (prima un <form>) tiene il pulsante largo quanto il suo testo:
              la sezione è una griglia, e una griglia allarga i suoi figli diretti */}
          <div data-delete-form="">
            <button className="btn btn--danger" type="button" disabled={deleting} onClick={handleDeleteOpen} data-delete-open="">
              Cancella l'account
            </button>
          </div>
        </section>

        <p className="settings__back"><a href="/">Torna alla home</a></p>
      </section>
      {confirmModal}
      {offlineModal}
    </FormPage>
  );
}
