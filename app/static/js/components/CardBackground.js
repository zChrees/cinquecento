/**
 * Sfondo della home (P22): una cascata di carte che cade dall'alto senza fermarsi,
 * dal prototipo (P52, prototipo.js "Sfondo"). Carte di dorso e, di faccia, Assi,
 * Tre (i carichi) e coppie Cavallo + Re a ventaglio (cantare 40), dalle immagini
 * di app/static/img/cards-bg/ (P40). Stile in css/components/card-background.css.
 *
 *   import { initCardBackground } from '../components/CardBackground.js';
 *   initCardBackground(document.querySelector('[data-bg-cards]'));
 *
 * Il contenitore porta data-img-base (indirizzo della cartella delle immagini).
 * Le carte sono sempre le stesse a ogni apertura (numeri "casuali" fissi) e si
 * ricreano solo quando cambia la misura della finestra.
 */

import { el } from '../utils/dom.js';

// Carte di faccia, a turno: ogni tanto una coppia Cavallo + Re, poi Assi e Tre
const FACES = [
  'pair:coppe', 'asso-denari', 'tre-spade',
  'pair:bastoni', 'asso-coppe', 'tre-denari',
  'pair:spade', 'asso-bastoni', 'tre-coppe',
  'pair:denari', 'asso-spade', 'tre-bastoni',
];

/** Numero "casuale" ma sempre uguale per la stessa carta, così lo sfondo non cambia a ogni apertura. */
function pseudoRandom(i, k) {
  const x = Math.sin(i * 12.9898 + k * 78.233) * 43758.5453;
  return x - Math.floor(x);
}

function image(base, name) {
  return el('img', { attrs: { src: `${base}${name}.webp`, alt: '' } });
}

function card(base, kind) {
  if (kind.startsWith('pair:')) {
    const suit = kind.slice(5);
    return el('span', { class: 'bg-fall bg-pair' }, [image(base, `cavallo-${suit}`), image(base, `re-${suit}`)]);
  }
  const node = image(base, kind);
  node.className = 'bg-fall';
  return node;
}

/**
 * Carte sparse su tutta la larghezza, di misure diverse. Le più piccole sembrano
 * più lontane: cadono più lente, sono più scure e passano dietro alle grandi
 * (sono piene, non trasparenti: chi sta davanti copre chi sta dietro).
 */
function render(container) {
  const base = container.dataset.imgBase;
  const cardW = parseFloat(getComputedStyle(container).getPropertyValue('--bg-card-w'));
  const area = container.getBoundingClientRect();
  if (!cardW || !area.width) return;
  const count = Math.max(8, Math.min(26, Math.round((area.width / cardW) * 1.3)));
  const cards = [];
  let faces = 0;
  for (let i = 0; i < count; i += 1) {
    const rnd = (k) => pseudoRandom(i + 1, k + 20);
    const depth = 0.55 + rnd(1) * 0.45;
    // Due carte su cinque cadono di dorso, alternate a quelle di faccia
    const back = i % 5 === 1 || i % 5 === 3;
    const node = back ? card(base, 'dorso') : card(base, FACES[faces % FACES.length]);
    if (!back) faces += 1;
    const dur = (9 + rnd(4) * 5) / depth;
    const r0 = (rnd(6) * 2 - 1) * 40;
    const r1 = r0 + (rnd(7) < 0.5 ? -1 : 1) * (90 + rnd(8) * 180);
    const props = {
      '--bg-card-w': `${(cardW * depth).toFixed(1)}px`,
      '--x': `${(((i + 0.2 + rnd(3) * 0.6) / count) * area.width).toFixed(1)}px`,
      '--y': `${(rnd(10) * area.height).toFixed(1)}px`,   // posizione da ferma, senza animazioni
      '--dur': `${dur.toFixed(2)}s`,
      '--delay': `${(-rnd(5) * dur).toFixed(2)}s`,
      '--r0': `${r0.toFixed(1)}deg`,
      '--r1': `${r1.toFixed(1)}deg`,
      '--drift': `${((rnd(9) * 2 - 1) * cardW * 1.2).toFixed(1)}px`,
      '--shade': (0.45 + depth * 0.4).toFixed(2),   // luce: 0,67 per le lontane, 0,85 per le vicine
    };
    for (const [name, value] of Object.entries(props)) node.style.setProperty(name, value);
    cards.push({ depth, node });
  }
  // Prima le lontane, poi le vicine: nella pagina chi viene dopo sta davanti
  cards.sort((a, b) => a.depth - b.depth);
  container.replaceChildren(...cards.map((c) => c.node));
}

/** Riempie il contenitore con la cascata e la ricrea quando cambia la misura della finestra. */
export function initCardBackground(container) {
  if (!container) return;
  render(container);
  let timer = null;
  window.addEventListener('resize', () => {
    clearTimeout(timer);
    timer = setTimeout(() => render(container), 120);
  });
}
