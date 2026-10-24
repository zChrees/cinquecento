/**
 * Gli indirizzi della SPA: indirizzo → pagina (React Router).
 *
 * Cosa contiene:
 *   router   l'oggetto che main.tsx passa a <RouterProvider>
 *
 * Flask manda la SPA per ogni indirizzo senza rotta
 * fuori da /api/, /static/ e /socket.io (spa_fallback di app/blueprints/spa/routes.py),
 * e Vite fa lo stesso in sviluppo: un indirizzo che non è qui sotto lo disegna
 * NotFoundPage ("Pagina non trovata"). Una pagina nuova della SPA si aggiunge qui;
 * se il server deve controllare qualcosa prima di mandarla (per esempio il login,
 * come /profile/settings), le serve anche la sua rotta Flask con spa_page().
 * Ogni voce ha caseSensitive: true (maiuscole e minuscole contano, come per le
 * rotte di Flask): senza, /Profile/Settings aprirebbe le impostazioni senza
 * passare dal controllo del login della rotta /profile/settings.
 * Il tavolo React è GamePage su /game/:gameId (":gameId" vuol dire "qui un pezzo
 * variabile, che la pagina legge con useParams"); dalla home al tavolo e ritorno si
 * va senza ricaricare la pagina (navigate).
 *
 * DA DOVE ARRIVANO I DATI: React Router legge l'indirizzo della barra del
 * browser (window.location) e sceglie la voce di routes con lo stesso path.
 */

import { createBrowserRouter } from 'react-router';
import type { DataRouter, RouteObject } from 'react-router';
import { GamePage } from './game/GamePage';
import { HomePage } from './pages/HomePage';
import { LoginPage } from './pages/LoginPage';
import { NotFoundPage } from './pages/NotFoundPage';
import { RegisterPage } from './pages/RegisterPage';
import { SettingsPage } from './pages/SettingsPage';

// routes: l'elenco delle pagine. path è l'indirizzo, element il componente da
// disegnare (<LoginPage /> vuol dire "il componente LoginPage, senza dati").
// L'ultima voce, path '*', vuol dire "ogni altro indirizzo": React Router la
// sceglie solo se nessuna delle altre va bene.
const routes: RouteObject[] = [
  { path: '/', element: <HomePage />, caseSensitive: true },
  { path: '/auth/login', element: <LoginPage />, caseSensitive: true },
  { path: '/auth/register', element: <RegisterPage />, caseSensitive: true },
  { path: '/profile/settings', element: <SettingsPage />, caseSensitive: true },
  { path: '/game/:gameId', element: <GamePage />, caseSensitive: true },
  { path: '*', element: <NotFoundPage /> },
];

// router: chi segue la barra degli indirizzi e cambia pagina senza ricaricare
// ("Browser" perché usa gli indirizzi veri, /auth/login, e la cronologia del
// browser, quindi anche il tasto "indietro")
export const router: DataRouter = createBrowserRouter(routes);
