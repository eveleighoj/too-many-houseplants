import { describe, expect, test } from 'vitest';
import { NoAuth, chooseAuthKind } from 'trips-frontend/src/lib/auth/index.ts';

describe('chooseAuthKind', () => {
	const clerkPublishableKey = 'pk_test_ZXhhbXBsZS5jbGVyay5hY2NvdW50cy5kZXYk';

	test('uses Clerk when its publishable key is configured', () => {
		expect(chooseAuthKind({ clerkPublishableKey, mockAuthUrl: null })).toBe('clerk');
	});

	test('prefers Clerk over clerk-mock when both are configured', () => {
		expect(chooseAuthKind({ clerkPublishableKey, mockAuthUrl: 'http://localhost:8082' })).toBe(
			'clerk'
		);
	});

	test('uses clerk-mock when only its URL is configured', () => {
		expect(
			chooseAuthKind({ clerkPublishableKey: null, mockAuthUrl: 'http://localhost:8082' })
		).toBe('mock');
	});

	test('has no sign-in when nothing is configured', () => {
		expect(chooseAuthKind({ clerkPublishableKey: null, mockAuthUrl: null })).toBe('none');
	});
});

describe('NoAuth', () => {
	test('is never signed in and has no token', async () => {
		const auth = new NoAuth();

		expect(auth.loaded).toBe(true);
		expect(auth.signedIn).toBe(false);
		expect(await auth.getToken()).toBeNull();
	});
});
