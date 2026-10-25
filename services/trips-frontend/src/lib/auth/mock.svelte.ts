import { isExpired } from './token';

const STORAGE_KEY = 'trips.token';

// localStorage can throw (private mode, blocked storage) — treat that as "not logged in".
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

/** The logged-in user's bearer token, kept in localStorage (see ARCHITECTURE.md → Auth). */
class Auth {
	token = $state<string | null>(load());

	get loggedIn(): boolean {
		return this.token !== null && !isExpired(this.token);
	}

	set(token: string): void {
		this.token = token;
		save(token);
	}

	clear(): void {
		this.token = null;
		save(null);
	}
}

export const auth = new Auth();
