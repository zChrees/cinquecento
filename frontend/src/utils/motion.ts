/**
 * Piccoli aiuti per le animazioni.
 *
 * Cosa contiene:
 *   reduceMotion()   true se l'utente ha chiesto di ridurre i movimenti
 *
 * DA DOVE ARRIVANO I DATI: dalle impostazioni del sistema (telefono o computer),
 * che il browser espone come "prefers-reduced-motion".
 */

/**
 * Dice se l'utente ha chiesto di ridurre le animazioni.
 *
 * @returns {boolean}
 *
 * In parole semplici:
 *   reduceMotion()  →  true con "Riduci movimento" acceso: allora finestre e
 *   logo non si animano (come reduceMotion() di core/layout.js e Modal.js).
 */
export function reduceMotion(): boolean {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}
