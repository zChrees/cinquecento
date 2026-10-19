/**
 * Pagina di accesso, /auth/login (P16, P96, P125; passo 4 della migrazione): la
 * versione React di app/templates/auth/login.html e js/pages/auth.js, con lo
 * stesso HTML e gli stessi data-* (stile in css/pages/auth.css e components/form.css).
 *
 * Cosa contiene:
 *   <LoginPage />
 *
 * Come funziona l'invio:
 *   - senza rete il modulo non parte: compare "Nessuna connessione";
 *   - al primo invio il pulsante si spegne, così un doppio clic non manda due
 *     richieste; si riaccende se il server rifiuta, o se si torna indietro alla pagina;
 *   - se il server accetta, la pagina va all'indirizzo che risponde (la pagina
 *     chiesta prima, ?next=, o la home);
 *   - un errore di un campo va sotto il campo, gli altri (credenziali sbagliate,
 *     troppi tentativi) in basso, come i messaggi di prima.
 *
 * DA DOVE ARRIVANO I DATI: quello che scrive l'utente; la risposta da
 * POST /api/auth/login (app/blueprints/auth/api.py).
 */

import { useEffect, useState } from 'react';
import type { FormEvent, JSX } from 'react';
import { Link } from 'react-router';
import { postJson } from '../api/client';
import { Field } from '../components/Field';
import { OfflineModal } from '../components/OfflineModal';
import type { AuthDone, LoginBody } from '../types/api';
import { FormPage, useSessionFlashes } from './FormPage';

// FieldErrors: gli errori di ogni campo, per esempio { password: ['Scrivi la password.'] }
type FieldErrors = Record<string, string[]>;

// NO_ERRORS: un elenco vuoto, per i campi senza errori
const NO_ERRORS: string[] = [];

/**
 * Gli errori di un campo.
 *
 * In parole semplici:
 *   errorsOf(errors, 'password')  →  ['Scrivi la password.'] oppure [] se non ce ne sono
 */
export function errorsOf(errors: FieldErrors, name: string): string[] {
  const found = errors[name];
  if (found === undefined) {
    return NO_ERRORS;
  }
  return found;
}

/**
 * Riaccende il pulsante quando si torna alla pagina con "indietro".
 *
 * @param {(sending: boolean) => void} setSending la funzione che accende o spegne il pulsante
 * @returns {void}
 *
 * In parole semplici:
 *   useBackReset(setSending);
 *   Il browser può rimettere la pagina com'era (con il pulsante spento) quando si
 *   torna indietro: l'evento pageshow avvisa, e il pulsante si riaccende (P125).
 */
export function useBackReset(setSending: (sending: boolean) => void): void {
  /** Effetto: ascolta pageshow finché la pagina c'è. */
  function listen(): () => void {
    function handlePageShow(): void {
      setSending(false);
    }

    window.addEventListener('pageshow', handlePageShow);

    function stop(): void {
      window.removeEventListener('pageshow', handlePageShow);
    }

    return stop;
  }

  // []: una volta sola
  useEffect(listen, []);
}

/**
 * La pagina di accesso.
 *
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <LoginPage />
 *   Il modulo con "Nome utente o email" e "Password", il pulsante "Accedi" e il
 *   link alla registrazione. Lo usa routes.tsx per /auth/login.
 */
export function LoginPage(): JSX.Element {
  // useState restituisce due cose: il valore attuale e la funzione per cambiarlo,
  // che fa ridisegnare il componente (regole-codice.md, sezione 6). Gli hook si
  // chiamano sempre in cima al componente, mai dentro un if.
  // username e password: il testo scritto nelle due caselle
  const [username, setUsername] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  // errors: gli errori di ogni campo, dall'ultima risposta del server
  const [errors, setErrors] = useState<FieldErrors>({});
  // sending: true dal primo invio alla risposta (pulsante spento)
  const [sending, setSending] = useState<boolean>(false);
  // offline: true mentre è aperta la finestra "Nessuna connessione"
  const [offline, setOffline] = useState<boolean>(false);
  // flashes: i messaggi in basso (quelli lasciati da un'altra pagina, poi gli errori)
  const [flashes, setFlashes] = useSessionFlashes();
  useBackReset(setSending);

  /**
   * Invio del modulo. preventDefault: il browser non lo manda da solo
   * (ricaricherebbe la pagina); lo manda postJson. async: può aspettare la
   * risposta con await senza bloccare la pagina.
   */
  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!navigator.onLine) {
      setOffline(true);
      return;
    }
    if (sending) {
      return;
    }
    setSending(true);

    // next: la pagina chiesta prima del login (?next=/game/abc), '' se non c'è
    let next = new URLSearchParams(window.location.search).get('next');
    if (next === null) {
      next = '';
    }
    const body: LoginBody = { username: username, password: password, next: next };
    const answer = await postJson<LoginBody, AuthDone>('/api/auth/login', body);
    if (answer.ok) {
      // il pulsante resta spento: la pagina sta per cambiare
      window.location.assign(answer.data.redirect);
      return;
    }

    setSending(false);
    if (answer.error.code === 'invalid_data' && answer.error.fields !== undefined) {
      setErrors(answer.error.fields);
      setFlashes([]);
    } else {
      setErrors({});
      setFlashes([{ kind: 'error', message: answer.error.message }]);
    }
  }

  /** La finestra "Nessuna connessione" si è chiusa. */
  function handleOfflineDone(): void {
    setOffline(false);
  }

  // offlineModal: la finestra, solo quando serve
  let offlineModal: JSX.Element | null = null;
  if (offline) {
    offlineModal = <OfflineModal onDone={handleOfflineDone} />;
  }

  return (
    <FormPage name="login" title="Accedi · Cinquecento" flashes={flashes}>
      <section className="panel auth" data-auth="login">
        <h1 className="auth__title">Accedi</h1>
        <p className="auth__subtitle">Entra per giocare a Cinquecento.</p>

        <form className="form" method="post" noValidate data-login-form="" onSubmit={handleSubmit}>
          <Field
            name="username"
            label="Nome utente o email"
            type="text"
            autoComplete="username"
            value={username}
            onChange={setUsername}
            hint=""
            errors={errorsOf(errors, 'username')}
          />
          <Field
            name="password"
            label="Password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={setPassword}
            hint=""
            errors={errorsOf(errors, 'password')}
          />
          <div className="form__actions">
            <button className="btn btn--primary btn--big" type="submit" disabled={sending} data-login-submit="">
              Accedi
            </button>
          </div>
        </form>

        <p className="auth__switch">
          Non hai un account? <Link to="/auth/register">Registrati</Link>
        </p>
      </section>
      {offlineModal}
    </FormPage>
  );
}
