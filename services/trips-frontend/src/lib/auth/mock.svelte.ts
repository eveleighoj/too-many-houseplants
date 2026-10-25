import { isExpired } from '../token.ts';
import type { AuthProvider } from './provider.ts';

const STORAGE_KEY = 'trips.token';

// localStorage can throw (private mode, blocked storage) — treat that as "not signed in".
function load(): string | null {
	try {
		const token = localStorage.getItem(STORAGE_KEY);
		return token && !isExpired(token) ? token : null;
	} catch {
		return null;
	}
}

function save(token: string | null): void {
	try {
		if (token) localStorage.setItem(STORAGE_KEY, token);
		else localStorage.removeItem(STORAGE_KEY);
	} catch {
		// Not persisted; the session still works until the page is reloaded.
	}
}

/** Local development only: sign in as one of clerk-mock's dev users, whose ready-made tokens
 * the login page lists (docker/wiremock/clerk/). The token is kept in localStorage. */
export class MockAuth implements AuthProvider {
	readonly kind = 'mock';
	readonly loaded = true;
	token = $state<string | null>(load());

	get signedIn(): boolean {
		return this.token !== null && !isExpired(this.token);
	}

	async getToken(): Promise<string | null> {
		return this.signedIn ? this.token : null;
	}

	/** Sign in with a dev user's token from clerk-mock. */
	signInAs(token: string): void {
		this.token = token;
		save(token);
	}

	async signOut(): Promise<void> {
		this.token = null;
		save(null);
	}
}
