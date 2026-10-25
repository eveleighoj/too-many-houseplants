/** What the rest of the app needs from sign-in, whichever provider is behind it (Clerk in
 * production, clerk-mock's dev users locally). Only src/lib/auth/ knows which one is in use,
 * so changing provider means writing one new implementation. See docs/frontend.md. */
export interface AuthProvider {
	/** Which implementation this is. */
	readonly kind: 'clerk' | 'mock' | 'none';
	/** False until the provider knows whether someone is signed in. Clerk loads
	 * asynchronously, so pages must wait for this before deciding to redirect to /login. */
	readonly loaded: boolean;
	readonly signedIn: boolean;
	/** A bearer token for the API, or null when signed out. Call it for every request:
	 * Clerk's tokens only last about a minute, and it returns a fresh one when needed. */
	getToken(): Promise<string | null>;
	signOut(): Promise<void>;
}
