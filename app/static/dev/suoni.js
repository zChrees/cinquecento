/**
 * Pagina per confrontare i suoni (P113 per il tavolo, P115 per il menu): solo per sviluppo.
 *
 * Legge suoni.json (momenti, suono di oggi e alternative) e per ogni scelta disegna
 * "Ascolta" e "Mi piace". Un suono alla volta: ogni "Ascolta" ferma quello di prima.
 * Le scelte si ricordano nel browser (solo comodità: la pagina funziona anche
 * senza) e finiscono nel riepilogo in fondo, da copiare.
 *
 * Marcatori per i test: [data-moment] (id del momento), [data-option] (id della
 * scelta), [data-play], [data-choose], [data-play-all]; [data-playing] sulla scelta
 * che suona e [data-chosen] su quella scelta; [data-summary] con il riepilogo.
 */

const VOLUME = 0.8; // come VOLUME di js/core/sounds.js
const ALL_GAP_MS = 900; // pausa tra una scelta e l'altra in "Ascolta tutte"
const STORE_KEY = 'cinquecento.dev.suoni';

const list = document.querySelector('[data-moments]');
const summary = document.querySelector('[data-summary]');
const status = document.querySelector('[data-status]');

let moments = [];
let choices = loadChoices(); // id del momento → id della scelta
let timers = [];
let playing = []; // elementi <audio> in corso
let playingRow = null;

function loadChoices() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORE_KEY) || '{}');
    return saved && typeof saved === 'object' ? saved : {};
  } catch {
    return {};
  }
}

function saveChoices() {
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify(choices));
  } catch {
    // Memoria del browser bloccata: le scelte restano solo finché la pagina è aperta
  }
}

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [name, value] of Object.entries(attrs)) {
    if (name === 'text') node.textContent = value;
    else if (name === 'data') Object.assign(node.dataset, value);
    else node.setAttribute(name, value);
  }
  node.append(...children);
  return node;
}

function optionName(option) {
  return option.id === 'oggi' ? 'Oggi' : `Alternativa ${option.id}`;
}

// --- Ascolto ---------------------------------------------------------------

function stop() {
  for (const timer of timers) clearTimeout(timer);
  timers = [];
  for (const audio of playing) audio.pause();
  playing = [];
  if (playingRow) delete playingRow.dataset.playing;
  playingRow = null;
}

function markPlaying(row) {
  if (playingRow) delete playingRow.dataset.playing;
  playingRow = row;
  row.dataset.playing = '';
}

/** Programma i file di una scelta a partire da `start` ms; restituisce quando finisce. */
function schedule(option, row, start) {
  const gap = option.gap_ms || 0;
  timers.push(setTimeout(() => markPlaying(row), start));
  option.files.forEach((file, i) => {
    timers.push(setTimeout(() => {
      const audio = new Audio(file);
      audio.volume = VOLUME;
      playing.push(audio);
      audio.play().catch(() => {}); // senza audio (o senza gesto) la pagina va avanti lo stesso
    }, start + i * gap));
  });
  const end = start + Math.max(0, option.files.length - 1) * gap + 700;
  timers.push(setTimeout(() => {
    if (playingRow === row) {
      delete row.dataset.playing;
      playingRow = null;
    }
  }, end));
  return end;
}

function play(option, row) {
  stop();
  schedule(option, row, 0);
}

function playAll(moment, section) {
  stop();
  let start = 0;
  for (const option of moment.options) {
    if (!option.files.length) continue;
    const row = section.querySelector(`[data-option="${option.id}"]`);
    start = schedule(option, row, start) + ALL_GAP_MS;
  }
}

// --- Disegno ---------------------------------------------------------------

function choose(moment, option) {
  choices[moment.id] = option.id;
  saveChoices();
  render();
}

function optionRow(moment, option) {
  const name = optionName(option);
  const silent = option.files.length === 0;
  const playButton = el('button', {
    type: 'button',
    class: 'dev-sounds__button',
    'aria-label': `Ascolta ${name.toLowerCase()}: ${moment.title}`,
    text: silent ? 'Silenzio' : 'Ascolta',
    data: { play: '' },
  });
  playButton.disabled = silent;
  const radio = el('input', { type: 'radio', name: `choice-${moment.id}`, value: option.id, data: { choose: '' } });
  radio.checked = choices[moment.id] === option.id;
  radio.addEventListener('change', () => choose(moment, option));
  const row = el('li', { class: 'option', data: { option: option.id } }, [
    playButton,
    el('span', { class: 'option__name', text: name }),
    el('label', { class: 'option__choose' }, [radio, el('span', { text: 'Mi piace' })]),
    el('span', { class: 'option__source', text: option.source }),
  ]);
  if (radio.checked) row.dataset.chosen = '';
  playButton.addEventListener('click', () => play(option, row));
  return row;
}

function momentSection(moment) {
  const titleId = `moment-${moment.id}`;
  const section = el('section', { class: 'moment', 'aria-labelledby': titleId, data: { moment: moment.id } });
  const all = el('button', {
    type: 'button',
    class: 'dev-sounds__button dev-sounds__button--ghost moment__all',
    'aria-label': `Ascolta tutte le scelte: ${moment.title}`,
    text: 'Ascolta tutte in fila',
    data: { playAll: '' },
  });
  all.addEventListener('click', () => playAll(moment, section));
  section.append(
    el('h2', { id: titleId, text: moment.title }),
    el('p', { class: 'moment__when', text: moment.when }),
    all,
    el('ul', { class: 'moment__options' }, moment.options.map((option) => optionRow(moment, option))),
  );
  return section;
}

function summaryText() {
  const lines = moments.map((moment) => {
    const option = moment.options.find((o) => o.id === choices[moment.id]);
    const picked = option ? `${optionName(option)} (${option.source})` : 'non ancora scelto';
    return `- ${moment.title} [${moment.id}]: ${picked}`;
  });
  return `Suoni del menu scelti (P115):\n${lines.join('\n')}`;
}

function render() {
  stop();
  list.replaceChildren(...moments.map(momentSection));
  summary.textContent = summaryText();
}

// --- Riepilogo -------------------------------------------------------------

document.querySelector('[data-copy]').addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(summary.textContent);
    status.textContent = 'Copiato.';
  } catch {
    // Senza https (per esempio dal telefono in rete locale) il browser non permette di copiare
    const range = document.createRange();
    range.selectNodeContents(summary);
    getSelection().removeAllRanges();
    getSelection().addRange(range);
    status.textContent = 'Testo selezionato: copialo a mano.';
  }
});

document.querySelector('[data-reset]').addEventListener('click', () => {
  choices = {};
  saveChoices();
  status.textContent = '';
  render();
});

fetch('suoni.json')
  .then((response) => response.json())
  .then((data) => {
    moments = data.moments;
    render();
    document.body.dataset.ready = '';
  })
  .catch(() => {
    status.textContent = 'Non riesco a leggere suoni.json.';
  });
