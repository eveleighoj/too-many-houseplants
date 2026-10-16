/** Pure helpers for the bearer token and post-login redirects (no storage, no Svelte). */

/** The token's `exp` claim in milliseconds, or null if it can't be read. Only the payload is
 * decoded — the signature is the backend's business. */
export function tokenExpiry(token: string): number | null {
	try {
		const payload = token.split('.')[1];
		const json = atob(payload.replace(/-/g, '+').replace(/_/g, '/'));
		const exp = JSON.parse(json).exp;
		return typeof exp === 'number' ? exp * 1000 : null;
	} catch {
		return null;
	}
}

export function isExpired(token: string, now: number = Date.now()): boolean {
	const expiry = tokenExpiry(token);
	return expiry === null || expiry <= now;
}

/** Where to go after logging in: `next` if it's a path on this site, otherwise home. Rejects
 * absolute and protocol-relative URLs so `?next=` can't send people to another site. */
export function safeNext(next: string | null): string {
	if (next && next.startsWith('/') && !next.startsWith('//') && !next.startsWith('/\\')) {
		return next;
	}
	return '/';
}
