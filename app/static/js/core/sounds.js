/**
 * Suoni al tavolo (P103, rifatti in P109 con suoni veri): file registrati dal vero,
 * del pacchetto Kenney "Casino Audio" (carte e fiches) e "Interface Sounds" (frasi,
 * ticchettio, fine partita), licenza CC0; dettagli in sounds/LICENZA.md.
 *
 *   preloadSounds()             // la pagina del tavolo, una volta
 *   playSound('card')           // subito
 *   playSound('draw', 500)      // tra 500 ms (in fila con le animazioni)
 *   soundsEnabled() / setSoundsEnabled(false)
 *
 * I file si scaricano dopo il caricamento della pagina (fetch, senza bloccarla). Il
 * contesto audio si crea solo al primo tocco o tasto: i browser (Safari soprattutto)
 * fanno suonare la pagina solo dopo un gesto, e crearlo durante un ridisegno del
 * tavolo lo bloccava per più di 100 ms (P109). Prima di allora, o se il browser non ha
 * Web Audio, non suona niente e la pagina funziona lo stesso.
 *
 * La scelta acceso/spento si ricorda nel browser (localStorage, chiave SOUNDS_KEY);
 * all'inizio i suoni sono accesi. La cambia l'interruttore della pagina delle
 * impostazioni.
 *
 * Per i test: ogni suono che parte manda sul documento l'evento "cinquecento:sound"
 * con { name }, anche quando il browser non lo fa sentire; con i suoni spenti niente.
 */

export const SOUNDS_KEY = 'cinquecento.sounds';
const BASE = new URL('../../sounds/', import.meta.url).href;
const VOLUME = 0.8;

// Nome del suono → file (più di uno: se ne sceglie uno a caso, così non sembra un disco)
export const SOUNDS = {
  card: ['card-place-1', 'card-place-2', 'card-place-3'], // una carta si posa sul tavolo
  draw: ['card-slide-1', 'card-slide-2', 'card-slide-3', 'card-slide-4'], // pescata
  shuffle: ['card-shuffle'], // mescolata a inizio mano
  deal: ['card-fan'], // distribuzione
  trick: ['card-gather'], // presa raccolta
  lay_down: ['cards-laid-down'], // calata
  sing: ['chips-stack'], // canto
  phrase: ['phrase'], // frase al tavolo
  tick: ['tick'], // ultimi secondi del tuo turno (nessun suono quando comincia: P109)
  last_tick: ['tick-last'],
  win: ['win'],
  lose: ['lose'],
  tie: ['tie'],
};

let context = null;
let master = null;
const raw = new Map(); // file → ArrayBuffer scaricato
const decoded = new Map(); // file → AudioBuffer pronto
let preloading = false;

/** true se i suoni sono accesi (anche quando il browser non permette di leggere la scelta). */
export function soundsEnabled() {
  try {
    return localStorage.getItem(SOUNDS_KEY) !== 'off';
  } catch {
    return true;
  }
}

export function setSoundsEnabled(on) {
  try {
    localStorage.setItem(SOUNDS_KEY, on ? 'on' : 'off');
  } catch {
    // Scelta non salvata (memoria del browser bloccata): resta quella di prima
  }
}

function decode(file) {
  const data = raw.get(file);
  if (!context || !data || decoded.has(file)) return;
  raw.delete(file); // decodeAudioData consuma il buffer
  context.decodeAudioData(data).then((buffer) => decoded.set(file, buffer), () => {});
}

/** Al primo gesto dell'utente: crea (o fa ripartire) il contesto audio e prepara i suoni. */
function unlock() {
  if (!context) {
    const Context = window.AudioContext || window.webkitAudioContext;
    if (!Context) return;
    try {
      context = new Context();
      master = context.createGain();
      master.gain.value = VOLUME;
      master.connect(context.destination);
    } catch {
      context = null;
      return;
    }
    for (const file of raw.keys()) decode(file);
  }
  if (context.state === 'suspended') context.resume().catch(() => {});
}

/** Scarica i file dei suoni (una volta) e prepara lo sblocco dell'audio al primo gesto. */
export function preloadSounds() {
  if (preloading) return;
  preloading = true;
  for (const type of ['pointerup', 'touchend', 'click', 'keydown']) {
    window.addEventListener(type, unlock, { capture: true, passive: true });
  }
  const files = [...new Set(Object.values(SOUNDS).flat())];
  for (const file of files) {
    fetch(`${BASE}${file}.mp3`)
      .then((response) => (response.ok ? response.arrayBuffer() : null))
      .then((data) => {
        if (!data) return;
        raw.set(file, data);
        decode(file);
      })
      .catch(() => {});
  }
}

/**
 * Suona `name` tra `delay` millisecondi (subito con 0). Con i suoni spenti non fa niente.
 * @param {string} name una delle chiavi di SOUNDS
 * @param {number} [delay]
 */
export function playSound(name, delay = 0) {
  const files = SOUNDS[name];
  if (!files) throw new Error(`Suono sconosciuto: ${name}`);
  if (delay > 0) {
    setTimeout(() => playSound(name, 0), delay);
    return;
  }
  if (!soundsEnabled()) return;
  document.dispatchEvent(new CustomEvent('cinquecento:sound', { detail: { name } }));
  const buffer = decoded.get(files[Math.floor(Math.random() * files.length)]);
  if (!context || context.state !== 'running' || !buffer) return;
  try {
    const source = context.createBufferSource();
    source.buffer = buffer;
    source.connect(master);
    source.start();
  } catch {
    // L'audio non è disponibile adesso: la pagina va avanti senza suono
  }
}
