/**
 * Suoni al tavolo (P103): creati nel browser con Web Audio, nessun file da scaricare.
 *
 *   playSound('throw')          // subito
 *   playSound('draw', 500)      // tra 500 ms (per i suoni in fila con le animazioni)
 *   soundsEnabled() / setSoundsEnabled(false)
 *
 * Suoni: shuffle (mescolata), deal (una carta distribuita), throw (lancio: fruscio
 * e, alla fine del volo, la carta che si posa: opzione `land` in ms), draw (pescata),
 * trick (presa raccolta), sing (canto), lay_down (calata), turn (tocca a te),
 * tick e last_tick (tempo che scade), hand_end (fine mano), win, lose, tie (fine partita).
 *
 * La scelta acceso/spento si ricorda nel browser (localStorage, chiave SOUNDS_KEY);
 * all'inizio i suoni sono accesi. La cambia l'interruttore della pagina delle
 * impostazioni. Se il browser blocca l'audio (per esempio prima di un tocco nella
 * pagina) o non ha Web Audio, non suona niente e la pagina funziona lo stesso.
 *
 * Per i test: ogni suono che parte manda sul documento l'evento "cinquecento:sound"
 * con { name }, anche quando il browser non lo fa sentire; con i suoni spenti niente.
 */

export const SOUNDS_KEY = 'cinquecento.sounds';
const VOLUME = 0.35;

let context = null;
let master = null;
let noise = null;

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

/** Il contesto audio, creato alla prima richiesta; null se il browser non ha Web Audio. */
function audio() {
  if (context) return context;
  const Context = window.AudioContext || window.webkitAudioContext;
  if (!Context) return null;
  try {
    context = new Context();
    master = context.createGain();
    master.gain.value = VOLUME;
    master.connect(context.destination);
    // Un secondo di rumore bianco, per fruscii e carte
    noise = context.createBuffer(1, context.sampleRate, context.sampleRate);
    const data = noise.getChannelData(0);
    for (let i = 0; i < data.length; i += 1) data[i] = Math.random() * 2 - 1;
  } catch {
    context = null;
  }
  return context;
}

// Il browser fa partire l'audio solo dopo un gesto dell'utente: al primo tocco o tasto
// il contesto (se c'è già) riparte
for (const type of ['pointerdown', 'keydown']) {
  window.addEventListener(type, () => {
    if (context && context.state === 'suspended') context.resume().catch(() => {});
  }, { capture: true, passive: true });
}

/** Una nota: onda `type` alla frequenza `freq`, da `at` secondi per `length`, con un attacco breve. */
function tone(ctx, at, freq, length, { type = 'sine', gain = 0.5, to = null } = {}) {
  const osc = ctx.createOscillator();
  const env = ctx.createGain();
  osc.type = type;
  osc.frequency.setValueAtTime(freq, at);
  if (to) osc.frequency.exponentialRampToValueAtTime(to, at + length);
  env.gain.setValueAtTime(0.0001, at);
  env.gain.exponentialRampToValueAtTime(gain, at + 0.01);
  env.gain.exponentialRampToValueAtTime(0.0001, at + length);
  osc.connect(env).connect(master);
  osc.start(at);
  osc.stop(at + length + 0.02);
}

/** Un fruscio: rumore filtrato intorno a `freq` (che può scorrere fino a `to`). */
function hiss(ctx, at, length, { freq = 2500, to = null, q = 1, gain = 0.4 } = {}) {
  const src = ctx.createBufferSource();
  src.buffer = noise;
  const filter = ctx.createBiquadFilter();
  filter.type = 'bandpass';
  filter.Q.value = q;
  filter.frequency.setValueAtTime(freq, at);
  if (to) filter.frequency.exponentialRampToValueAtTime(to, at + length);
  const env = ctx.createGain();
  env.gain.setValueAtTime(0.0001, at);
  env.gain.exponentialRampToValueAtTime(gain, at + Math.min(0.02, length / 3));
  env.gain.exponentialRampToValueAtTime(0.0001, at + length);
  src.connect(filter).connect(env).connect(master);
  src.start(at, Math.random() * 0.5);
  src.stop(at + length + 0.02);
}

/** La carta che tocca il panno: un colpo sordo e un po' di fruscio. */
function tap(ctx, at, gain = 0.5) {
  tone(ctx, at, 180, 0.08, { gain, to: 90 });
  hiss(ctx, at, 0.05, { freq: 1200, gain: gain * 0.5 });
}

const NOTES = { C5: 523.25, D5: 587.33, E5: 659.25, G5: 783.99, A4: 440, C6: 1046.5, E6: 1318.5, G4: 392 };

const SYNTHS = {
  shuffle: (ctx, t) => {
    // Due mazzetti che si intrecciano: tanti piccoli scatti, due volte (0,6 s come deck-riffle)
    for (let round = 0; round < 2; round += 1) {
      for (let i = 0; i < 9; i += 1) hiss(ctx, t + round * 0.3 + i * 0.025, 0.03, { freq: 3500, q: 2, gain: 0.25 });
    }
  },
  deal: (ctx, t) => hiss(ctx, t, 0.06, { freq: 3000, to: 1500, gain: 0.18 }),
  throw: (ctx, t, { land = 400 } = {}) => {
    hiss(ctx, t, Math.max(0.12, land / 1000 * 0.6), { freq: 1800, to: 4500, gain: 0.22 });
    tap(ctx, t + land / 1000);
  },
  draw: (ctx, t) => hiss(ctx, t, 0.16, { freq: 4000, to: 1800, gain: 0.22 }),
  trick: (ctx, t) => {
    hiss(ctx, t, 0.2, { freq: 2200, to: 900, gain: 0.3 });
    tap(ctx, t + 0.2, 0.3);
  },
  sing: (ctx, t) => {
    tone(ctx, t, NOTES.E5, 0.25, { gain: 0.35 });
    tone(ctx, t + 0.12, NOTES.G5, 0.25, { gain: 0.35 });
    tone(ctx, t + 0.24, NOTES.C6, 0.45, { gain: 0.35 });
  },
  lay_down: (ctx, t) => {
    for (let i = 0; i < 5; i += 1) tap(ctx, t + i * 0.06, 0.3);
    tone(ctx, t + 0.3, NOTES.C5, 0.3, { gain: 0.3 });
    tone(ctx, t + 0.42, NOTES.G5, 0.5, { gain: 0.3 });
  },
  turn: (ctx, t) => {
    tone(ctx, t, NOTES.A4 * 2, 0.35, { gain: 0.3 });
    tone(ctx, t + 0.1, NOTES.E6, 0.4, { gain: 0.15 });
  },
  tick: (ctx, t) => tone(ctx, t, 1400, 0.04, { type: 'square', gain: 0.12 }),
  last_tick: (ctx, t) => tone(ctx, t, 1900, 0.06, { type: 'square', gain: 0.16 }),
  hand_end: (ctx, t) => {
    tone(ctx, t, NOTES.G5, 0.3, { gain: 0.3 });
    tone(ctx, t + 0.15, NOTES.C5, 0.45, { gain: 0.3 });
  },
  win: (ctx, t) => {
    [NOTES.C5, NOTES.E5, NOTES.G5, NOTES.C6].forEach((f, i) => tone(ctx, t + i * 0.13, f, i === 3 ? 0.7 : 0.25, { gain: 0.35 }));
  },
  lose: (ctx, t) => {
    [NOTES.E5, NOTES.C5, NOTES.A4].forEach((f, i) => tone(ctx, t + i * 0.2, f, i === 2 ? 0.7 : 0.3, { type: 'triangle', gain: 0.35 }));
  },
  tie: (ctx, t) => {
    tone(ctx, t, NOTES.G4 * 2, 0.3, { gain: 0.3 });
    tone(ctx, t + 0.25, NOTES.G4 * 2, 0.5, { gain: 0.3 });
  },
};

/**
 * Suona `name` tra `delay` millisecondi (subito con 0). Con i suoni spenti non fa niente.
 * @param {string} name uno dei nomi di SYNTHS
 * @param {number} [delay]
 * @param {object} [options] per throw: { land } millisecondi del volo
 */
export function playSound(name, delay = 0, options = {}) {
  if (!SYNTHS[name]) throw new Error(`Suono sconosciuto: ${name}`);
  if (delay > 0) {
    setTimeout(() => playSound(name, 0, options), delay);
    return;
  }
  if (!soundsEnabled()) return;
  document.dispatchEvent(new CustomEvent('cinquecento:sound', { detail: { name } }));
  const ctx = audio();
  if (!ctx) return;
  try {
    if (ctx.state === 'suspended') ctx.resume().catch(() => {});
    SYNTHS[name](ctx, ctx.currentTime + 0.01, options);
  } catch {
    // L'audio non è disponibile adesso: la pagina va avanti senza suono
  }
}
