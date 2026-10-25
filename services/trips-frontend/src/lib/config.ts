/** Where the backend lives. Set VITE_API_URL at build time (see .env.example). */
export const API_URL = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(
	/\/+$/,
	''
);

/** The clerk-mock service (local development only). When set, the login page lists its dev
 * users instead of asking for a real sign-in. Never set it in a production build. */
export const MOCK_AUTH_URL = import.meta.env.VITE_MOCK_AUTH_URL?.replace(/\/+$/, '') || null;
