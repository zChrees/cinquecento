/**
 * Pagina di registrazione, /auth/register (P16, P61, P125; stile in
 * css/pages/auth.css e components/form.css).
 *
 * Cosa contiene:
 *   <RegisterPage />   PASSWORD_HINT
 *
 * L'invio funziona come in LoginPage.tsx (niente rete, doppio clic, "indietro").
 * Se il server accetta, l'account è creato, il login è fatto e la pagina va alla
 * home, dove compare "Benvenuto, ...!". Gli errori vanno sotto il campo giusto,
 * anche "username già usato" ed "email già usata", che decide il database.
 *
 * DA DOVE ARRIVANO I DATI: quello che scrive l'utente; la risposta da
 * POST /api/auth/register (app/blueprints/auth/api.py).
 */

import { useState } from 'react';
import type { FormEvent, JSX } from 'react';
import { Link } from 'react-router';
import { postJson } from '../api/client';
import { Field } from '../components/Field';
import { OfflineModal } from '../components/OfflineModal';
import type { AuthDone, RegisterBody } from '../types/api';
import { FormPage, useSessionFlashes } from './FormPage';
import { errorsOf, useBackReset } from './LoginPage';

// PASSWORD_HINT: le regole della password da leggere prima dell'invio (P61, D8).
// Deve restare uguale a PASSWORD_HINT di app/blueprints/auth/forms.py, che le
// controlla davvero (lo confronta tests/frontend/test_pagine_accesso.py).
export const PASSWORD_HINT =
  'Almeno 8 caratteri, con almeno una lettera maiuscola, un numero e un simbolo (per esempio ! ? @ # - _).';

/**
 * La pagina di registrazione.
 *
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <RegisterPage />
 *   Il modulo con Username, Email, Password (con le regole sotto) e "Ripeti la
 *   password", il pulsante "Registrati" e il link all'accesso. Lo usa routes.tsx
 *   per /auth/register.
 */
export function RegisterPage(): JSX.Element {
  // useState restituisce due cose: il valore attuale e la funzione per cambiarlo,
  // che fa ridisegnare il componente (regole-codice.md, sezione 6). Gli hook si
  // chiamano sempre in cima al componente, mai dentro un if.
  // username, email, password, confirm: il testo scritto nelle quattro caselle
  const [username, setUsername] = useState<string>('');
  const [email, setEmail] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [confirm, setConfirm] = useState<string>('');
  // errors: gli errori di ogni campo, dall'ultima risposta del server
  const [errors, setErrors] = useState<Record<string, string[]>>({});
  // sending: true dal primo invio alla risposta (pulsante spento)
  const [sending, setSending] = useState<boolean>(false);
  // offline: true mentre è aperta la finestra "Nessuna connessione"
  const [offline, setOffline] = useState<boolean>(false);
  // flashes: i messaggi in basso
  const [flashes, setFlashes] = useSessionFlashes();
  useBackReset(setSending);

  /**
   * Invio del modulo (come handleSubmit di LoginPage.tsx): preventDefault perché
   * lo manda postJson, non il browser.
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

    const body: RegisterBody = { username: username, email: email, password: password, confirm: confirm };
    const answer = await postJson<RegisterBody, AuthDone>('/api/auth/register', body);
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
    <FormPage name="register" title="Registrati · Cinquecento" flashes={flashes}>
      <section className="panel auth" data-auth="register">
        <h1 className="auth__title">Registrati</h1>
        <p className="auth__subtitle">Crea un account per giocare a Cinquecento.</p>

        <form className="form" method="post" noValidate data-register-form="" onSubmit={handleSubmit}>
          <Field
            name="username"
            label="Username"
            type="text"
            autoComplete="username"
            value={username}
            onChange={setUsername}
            hint=""
            errors={errorsOf(errors, 'username')}
          />
          <Field
            name="email"
            label="Email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={setEmail}
            hint=""
            errors={errorsOf(errors, 'email')}
          />
          <Field
            name="password"
            label="Password"
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={setPassword}
            hint={PASSWORD_HINT}
            errors={errorsOf(errors, 'password')}
          />
          <Field
            name="confirm"
            label="Ripeti la password"
            type="password"
            autoComplete="new-password"
            value={confirm}
            onChange={setConfirm}
            hint=""
            errors={errorsOf(errors, 'confirm')}
          />
          <div className="form__actions">
            <button className="btn btn--primary btn--big" type="submit" disabled={sending} data-register-submit="">
              Registrati
            </button>
          </div>
        </form>

        <p className="auth__switch">
          Hai già un account? <Link to="/auth/login">Accedi</Link>
        </p>
      </section>
      {offlineModal}
    </FormPage>
  );
}
