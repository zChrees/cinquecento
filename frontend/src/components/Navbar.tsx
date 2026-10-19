/**
 * La navbar delle pagine della SPA (P40), per ora solo per chi NON ha fatto il
 * login (passo 4 della migrazione: accesso e registrazione). Ha lo stesso HTML
 * della parte "senza login" di app/templates/partials/navbar.html: icona
 * generica e "Accedi", il logo, "Amici". Avatar e amici aprono la finestra
 * "Accedi o registrati per giocare". La versione con il login (statistiche,
 * pannello amici) arriva al passo 5.
 *
 * Cosa contiene:
 *   <Navbar />
 *
 * DA DOVE ARRIVANO I DATI: nessuno, per ora (stile in components/navbar.css).
 */

import { useState } from 'react';
import type { JSX } from 'react';
import { LoginPrompt } from './LoginPrompt';
import { Logo } from './Logo';

/**
 * La navbar.
 *
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <Navbar />
 *   Disegna la barra in alto e, quando serve, la finestra "Accedi o registrati".
 *   Un secondo clic mentre la finestra è aperta non ne apre un'altra.
 */
export function Navbar(): JSX.Element {
  // useState restituisce il valore attuale e la funzione per cambiarlo, che fa
  // ridisegnare il componente (regole-codice.md, sezione 6).
  // promptOpen: true mentre la finestra "Accedi o registrati" è aperta
  const [promptOpen, setPromptOpen] = useState<boolean>(false);

  /** Clic su avatar o amici: apre la finestra. */
  function handleOpenPrompt(): void {
    setPromptOpen(true);
  }

  /** La finestra si è chiusa senza scegliere: si toglie. */
  function handlePromptDone(): void {
    setPromptOpen(false);
  }

  // prompt: la finestra, solo quando è aperta (deciso con un if prima del return)
  let prompt: JSX.Element | null = null;
  if (promptOpen) {
    prompt = <LoginPrompt onDone={handlePromptDone} />;
  }

  // <> ... </>: un contenitore che non diventa un elemento della pagina; serve
  // perché un componente restituisce un solo pezzo (qui: barra più finestra)
  return (
    <>
      <header className="navbar" data-part="navbar">
        <div className="navbar__inner">
          <button
            className="navbar__account felt-text"
            type="button"
            data-login-prompt=""
            aria-haspopup="dialog"
            aria-label="Accedi o registrati"
            onClick={handleOpenPrompt}
          >
            <span className="avatar" aria-hidden="true"><span className="icon">person</span></span>
            <span className="navbar__label" aria-hidden="true">Accedi</span>
          </button>

          <Logo />

          <button
            className="navbar__friends felt-text"
            type="button"
            data-login-prompt=""
            aria-haspopup="dialog"
            aria-label="Amici: accedi per vederli"
            onClick={handleOpenPrompt}
          >
            <span className="icon" aria-hidden="true">group</span>
            <span className="navbar__label" aria-hidden="true">Amici</span>
            <span className="badge" aria-hidden="true" data-friends-badge="" hidden></span>
          </button>
        </div>
      </header>
      {prompt}
    </>
  );
}
