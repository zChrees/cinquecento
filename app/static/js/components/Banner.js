/**
 * Avviso in cima alla pagina (P33), sotto la navbar: uno solo per pagina, finché
 * non lo si toglie. Lo usa core/socket.js per lo stato della connessione.
 * Stile in css/components/banner.css.
 *
 *   import { showBanner, hideBanner } from '../components/Banner.js';
 *   showBanner({ text: 'Connessione persa: riprovo a collegarmi…' });
 *   showBanner({ text: 'Sei stato scollegato…', kind: 'error',
 *                action: { label: 'Ricarica', onClick: () => location.reload() } });
 *   hideBanner();
 *
 * - kind "waiting" (predefinito): icona che gira, role="status" (i lettori di schermo
 *   lo leggono senza interrompere); kind "error": role="alert".
 * - Sta nel "top layer" (popover) quando il browser lo permette, così resta sopra le
 *   finestre già aperte (pannello amici, carta-modal, schermata di coda).
 * - Lo stesso avviso mostrato di nuovo non si ridisegna (non si rilegge ogni volta).
 * - Il testo entra sempre come testo, mai come HTML.
 */

import { el, icon } from '../utils/dom.js';

let current = null;   // { element, key }

export function showBanner({ text, kind = 'waiting', action = null }) {
  const key = `${kind}|${text}|${action?.label ?? ''}`;
  if (current?.key === key) return current.element;
  hideBanner();
  const element = el('div', {
    class: `banner banner--${kind}`,
    attrs: { role: kind === 'error' ? 'alert' : 'status' },
    data: { banner: kind },
  }, [
    kind === 'error' ? icon('error') : icon('progress_activity', 'banner__spin'),
    el('span', { class: 'banner__text', text }),
    action ? el('button', {
      class: 'btn btn--small banner__action', text: action.label, attrs: { type: 'button' },
      data: { bannerAction: '' }, on: { click: action.onClick },
    }) : null,
  ]);
  document.body.append(element);
  if (element.showPopover) {
    element.popover = 'manual';
    element.showPopover();
  }
  current = { element, key };
  return element;
}

export function hideBanner() {
  if (!current) return;
  current.element.remove();
  current = null;
}
