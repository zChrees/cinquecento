/**
 * Un campo di un modulo (P16, P19): etichetta, casella, regole sotto la casella
 * ed errori. Ha lo stesso HTML della macro field() delle pagine Jinja di accesso
 * e registrazione di prima (stile in app/static/css/components/form.css).
 *
 * Cosa contiene:
 *   <Field name="username" label="Username" type="text" autoComplete="username"
 *          value={...} onChange={...} hint="" errors={[]} />
 *
 * DA DOVE ARRIVANO I DATI: dalla pagina che lo usa (LoginPage, RegisterPage), che
 * tiene il testo scritto e gli errori ricevuti dal server (error.fields).
 */

import type { ChangeEvent, JSX } from 'react';

// FieldProps: cosa riceve il componente
interface FieldProps {
  // il nome del campo, lo stesso del server: 'username', 'email', 'password', 'confirm'.
  // È anche l'id della casella, come nelle pagine di prima (i test lo usano)
  name: string;
  // l'etichetta, per esempio 'Nome utente o email'
  label: string;
  // il tipo della casella: 'text', 'email' o 'password'
  type: 'text' | 'email' | 'password';
  // il suggerimento del browser per il riempimento automatico, per esempio 'username'
  autoComplete: string;
  // il testo scritto adesso
  value: string;
  // la funzione da chiamare a ogni tasto, con il testo nuovo. In C: void (*onChange)(char *)
  onChange: (value: string) => void;
  // le regole da leggere prima dell'invio (oggi solo la password, P61); '' = niente
  hint: string;
  // gli errori di questo campo arrivati dal server; vuoto = nessun errore
  errors: string[];
}

/**
 * Il campo.
 *
 * @param {FieldProps} props
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <Field ... />
 *   Con degli errori il riquadro diventa rosso (field--error), la casella ha
 *   aria-invalid e ogni errore compare sotto con role="alert". Le regole
 *   (hint) sono collegate alla casella con aria-describedby, così il lettore di
 *   schermo le legge insieme all'etichetta.
 */
export function Field(props: FieldProps): JSX.Element {
  /** Un tasto nella casella: passa il testo nuovo alla pagina. */
  function handleChange(event: ChangeEvent<HTMLInputElement>): void {
    props.onChange(event.target.value);
  }

  // hintId: l'id della riga delle regole, per esempio 'password-hint'
  const hintId = `${props.name}-hint`;

  // hint e describedBy: la riga delle regole, solo se c'è
  let hint: JSX.Element | null = null;
  let describedBy: string | undefined = undefined;
  if (props.hint !== '') {
    hint = <p className="field__hint" id={hintId} data-field-hint={props.name}>{props.hint}</p>;
    describedBy = hintId;
  }

  // errors: un <p> per errore. key: il testo, unico per un campo
  const errors: JSX.Element[] = [];
  for (let i = 0; i < props.errors.length; i++) {
    errors.push(<p key={props.errors[i]} className="field__error" role="alert">{props.errors[i]}</p>);
  }

  // className e invalid: l'aspetto e l'attributo per chi ha un errore
  let className = 'field';
  let invalid: 'true' | undefined = undefined;
  if (props.errors.length > 0) {
    className = 'field field--error';
    invalid = 'true';
  }

  return (
    <div className={className}>
      <label className="field__label" htmlFor={props.name}>{props.label}</label>
      <input
        className="input"
        id={props.name}
        name={props.name}
        type={props.type}
        autoComplete={props.autoComplete}
        required
        aria-invalid={invalid}
        aria-describedby={describedBy}
        value={props.value}
        onChange={handleChange}
      />
      {hint}
      {errors}
    </div>
  );
}
