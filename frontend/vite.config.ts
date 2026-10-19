/**
 * Configurazione di Vite (docs/MIGRAZIONE-FRONTEND.md, sezione 6).
 *
 * Vite fa due lavori:
 *
 *   npm run dev    accende il server di sviluppo su http://localhost:5173. Le
 *                  pagine della SPA (SPA_PATHS) le serve lui, e le aggiorna a ogni
 *                  salvataggio senza ricaricare; tutto il resto (pagine Jinja, rotte
 *                  di Flask, /static, Socket.IO) lo gira a Flask su
 *                  http://localhost:5000. Questo "girare" si chiama proxy: il
 *                  browser vede un solo indirizzo, quindi il cookie del login e il
 *                  CSRF funzionano come in produzione.
 *   npm run build  traduce TypeScript e React in JavaScript normale e scrive il
 *                  risultato in app/static/dist/, che Flask serve come ogni file
 *                  statico (D54: la cartella non va nel repository).
 *
 * DA DOVE ARRIVANO I DATI: Vite legge questo file quando parte (npm run dev o
 * npm run build, comandi scritti in package.json).
 */

import { defineConfig } from 'vite';
import type { ConfigEnv, UserConfig } from 'vite';
import react from '@vitejs/plugin-react';

// FLASK: l'indirizzo del server Flask acceso con python run.py
const FLASK = 'http://localhost:5000';

// SPA_PATHS: gli indirizzi che sono pagine della SPA. Deve restare uguale a
// SPA_PATHS di app/blueprints/spa/routes.py (lo controlla tests/frontend/test_spa.py):
// una pagina nuova della SPA si aggiunge in tutti e due i posti.
const SPA_PATHS: string[] = ['/prova-react', '/auth/login', '/auth/register'];

/**
 * Costruisce l'espressione regolare degli indirizzi da girare a Flask.
 *
 * @returns {string} l'espressione, per esempio '^/(?!@|src/|node_modules/|prova-react(?:[/?]|$))'
 *
 * In parole semplici:
 *   flaskPattern()
 *   Dice "tutti gli indirizzi tranne questi": tranne quelli che usa Vite per sé
 *   (/@vite/client, /@react-refresh, /src/..., /node_modules/...) e tranne le
 *   pagine della SPA. Gli indirizzi che restano fuori li serve Vite.
 *
 *   (?!...) vuol dire "qui NON deve esserci...": per esempio /prova-react non
 *   va a Flask, /api/auth/login sì. Dopo il nome di una pagina può venire solo /, ?
 *   o la fine dell'indirizzo ([/?]|$), così /prova-reactx andrebbe a Flask.
 *
 *   Restituisce: il testo dell'espressione; Vite la riconosce come espressione
 *   regolare perché comincia con ^.
 */
function flaskPattern(): string {
  // excluded: i pezzi esclusi, uniti dopo con | (che vuol dire "oppure")
  const excluded: string[] = ['@', 'src/', 'node_modules/'];
  for (let i = 0; i < SPA_PATHS.length; i++) {
    // la pagina senza la / iniziale, per esempio 'prova-react'
    const name = SPA_PATHS[i].slice(1);
    excluded.push(`${name}(?:[/?]|$)`);
  }
  return `^/(?!${excluded.join('|')})`;
}

/**
 * La configurazione vera e propria.
 *
 * @param {ConfigEnv} env cosa sta facendo Vite: env.command è 'serve' (npm run dev) o 'build'
 * @returns {UserConfig}
 *
 * In parole semplici:
 *   viteConfig(env)
 *   Restituisce le impostazioni. L'unica che cambia tra sviluppo e build è base,
 *   il pezzo di indirizzo davanti ai file: in sviluppo i file li serve Vite dalla
 *   radice (/src/main.tsx); dopo il build li serve Flask da /static/dist/.
 */
function viteConfig(env: ConfigEnv): UserConfig {
  // base: davanti a ogni file prodotto, per esempio /static/dist/assets/index-3f9a1c.js
  let base = '/';
  if (env.command === 'build') {
    base = '/static/dist/';
  }

  // proxy: indirizzo (o espressione regolare) → dove girarlo. Vite prova le voci
  // in ordine. Socket.IO va per primo perché vuole anche il WebSocket (ws: true,
  // il collegamento sempre aperto del tempo reale); la seconda voce prende tutto
  // il resto, senza WebSocket, così non tocca quello che Vite usa per aggiornare
  // la pagina mentre si sviluppa.
  const proxy: Record<string, { target: string; ws: boolean }> = {};
  proxy['/socket.io'] = { target: FLASK, ws: true };
  proxy[flaskPattern()] = { target: FLASK, ws: false };

  return {
    base: base,
    plugins: [react()],
    server: {
      port: 5173,
      // se la porta è occupata Vite si ferma, invece di sceglierne un'altra
      strictPort: true,
      proxy: proxy,
    },
    build: {
      // la cartella che Flask serve come /static/dist/ (fuori da frontend/, quindi
      // va detto esplicitamente che si può svuotare prima di ogni build)
      outDir: '../app/static/dist',
      emptyOutDir: true,
    },
  };
}

export default defineConfig(viteConfig);
