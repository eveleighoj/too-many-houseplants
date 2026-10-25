import type { AuthProvider } from './provider.ts';

/** No sign-in configured for this build: everyone is anonymous (public pages still work). */
export class NoAuth implements AuthProvider {
	readonly kind = 'none';
	readonly loaded = true;
	readonly signedIn = false;

	async getToken(): Promise<string | null> {
		return null;
	}

	async signOut(): Promise<void> {}
}
