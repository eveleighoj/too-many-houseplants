// The app's sign-in, whichever provider this build is configured for. Import `auth` from here;
// nothing outside src/lib/auth/ should know which provider is behind it.
import { CLERK_PUBLISHABLE_KEY, MOCK_AUTH_URL } from '../config.ts';
import { ClerkAuth } from './clerk.svelte.ts';
import { MockAuth } from './mock.svelte.ts';
import { NoAuth } from './none.ts';

export type { AuthProvider } from './provider.ts';
export { ClerkAuth } from './clerk.svelte.ts';
export { MockAuth } from './mock.svelte.ts';
export { NoAuth } from './none.ts';

export type AuthKind = 'clerk' | 'mock' | 'none';

type AuthConfig = { clerkPublishableKey: string | null; mockAuthUrl: string | null };

/** Clerk whenever its key is configured (production, or locally against a Clerk development
 * instance); otherwise clerk-mock's dev users if configured (local); otherwise no sign-in. */
export function chooseAuthKind(config: AuthConfig): AuthKind {
	if (config.clerkPublishableKey) return 'clerk';
	if (config.mockAuthUrl) return 'mock';
	return 'none';
}

function createAuth(config: AuthConfig): ClerkAuth | MockAuth | NoAuth {
	switch (chooseAuthKind(config)) {
		case 'clerk':
			return new ClerkAuth(config.clerkPublishableKey!);
		case 'mock':
			return new MockAuth();
		case 'none':
			return new NoAuth();
	}
}

export const auth = createAuth({
	clerkPublishableKey: CLERK_PUBLISHABLE_KEY,
	mockAuthUrl: MOCK_AUTH_URL
});
