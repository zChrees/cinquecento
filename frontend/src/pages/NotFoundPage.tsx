/**
 * Pagina "non trovata" (lotto 9d della migrazione): la disegna React per ogni
 * indirizzo che non è una sua pagina. Flask manda la SPA per ogni indirizzo senza
 * rotta fuori da /api/, /static/ e /socket.io (regola unica, spa_fallback di
 * app/blueprints/spa/routes.py), quindi chi sbaglia indirizzo arriva qui.
 * Stesso riquadro e stesso testo di app/templates/errors/404.html, che resta per
 * i file statici che mancano e per i 404 decisi dal server; in più ha la navbar
 * (scelta di Christian, 24/10/2026). Stile in css/pages/auth.css e components/form.css.
 *
 * Cosa contiene:
 *   <NotFoundPage />
 *
 * DA DOVE ARRIVANO I DATI: nessun dato; i messaggi lasciati da un'altra pagina
 * arrivano da GET /api/auth/session (useSessionFlashes di FormPage.tsx).
 */

import type { JSX } from 'react';
import { Link } from 'react-router';
import { FormPage, useSessionFlashes } from './FormPage';

/**
 * La pagina.
 *
 * @returns {JSX.Element}
 *
 * In parole semplici:
 *   <NotFoundPage />
 *   Disegna la cornice (navbar e messaggi) con il riquadro "Pagina non trovata"
 *   e il pulsante "Torna alla home", che porta alla home senza ricaricare.
 */
export function NotFoundPage(): JSX.Element {
  // flashes: i messaggi da mostrare in basso (di solito nessuno)
  const [flashes] = useSessionFlashes();

  return (
    <FormPage name="error" title="Pagina non trovata · Cinquecento" flashes={flashes}>
      <section className="panel auth" data-error="404">
        <h1 className="auth__title">Pagina non trovata</h1>
        <p className="auth__subtitle">Questa pagina non esiste o non esiste più.</p>
        <div className="form__actions">
          <Link className="btn btn--primary btn--big" to="/">
            Torna alla home
          </Link>
        </div>
      </section>
    </FormPage>
  );
}
