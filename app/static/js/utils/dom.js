/**
 * Piccoli aiuti per creare elementi della pagina (P19).
 *
 * Tutto il testo entra con textContent o come nodo di testo, MAI come HTML:
 * così un nome utente o un messaggio con "<script>" resta testo (CLAUDE.md,
 * "Pagine web"). In questo file e nei componenti non si usa innerHTML.
 */

/**
 * Crea un elemento.
 *
 *   el('button', { class: 'btn btn--primary', text: 'Gioca', attrs: { type: 'button' },
 *                  data: { play: '' }, on: { click: onPlay } })
 *
 * @param {string} tag            nome del tag ('div', 'button', ...)
 * @param {object} [options]
 * @param {string} [options.class] classi CSS
 * @param {string|number} [options.text] testo (inserito come testo, mai come HTML)
 * @param {object} [options.attrs] attributi: true = attributo senza valore, false/null = assente
 * @param {object} [options.data]  attributi data-* (chiavi in camelCase: { friendId: 3 } → data-friend-id="3")
 * @param {object} [options.on]    gestori degli eventi ({ click: fn })
 * @param {Array|Node|string} [children] figli: elementi o testi (i testi restano testo)
 * @returns {HTMLElement}
 */
export function el(tag, options = {}, children = []) {
  const node = document.createElement(tag);
  const { class: className, text, attrs = {}, data = {}, on = {} } = options;

  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = String(text);

  for (const [name, value] of Object.entries(attrs)) {
    // I gestori si passano con "on", mai come attributo di testo (onclick="...")
    if (/^on/i.test(name)) throw new Error(`Attributo non ammesso: ${name}`);
    if (value === false || value === null || value === undefined) continue;
    node.setAttribute(name, value === true ? '' : String(value));
  }
  for (const [name, value] of Object.entries(data)) {
    node.dataset[name] = String(value);
  }
  for (const [type, handler] of Object.entries(on)) {
    node.addEventListener(type, handler);
  }
  for (const child of [].concat(children)) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child instanceof Node ? child : String(child));
  }
  return node;
}

/**
 * Icona di Material Symbols, nascosta ai lettori di schermo: il testo accessibile
 * lo dà il pulsante che la contiene (aria-label o testo visibile).
 *
 * @param {string} name nome dell'icona (es. 'close', 'group')
 * @param {string} [className] classi in più
 */
export function icon(name, className = '') {
  return el('span', { class: `icon ${className}`.trim(), text: name, attrs: { 'aria-hidden': 'true' } });
}

/** Toglie tutti i figli di un elemento. */
export function clear(node) {
  node.replaceChildren();
}
