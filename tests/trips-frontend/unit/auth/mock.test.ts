import { afterEach, describe, expect, test, vi } from 'vitest';
import { MockAuth } from 'trips-frontend/src/lib/auth/mock.svelte.ts';

function tokenExpiringAt(exp: number): string {
	const payload = btoa(JSON.stringify({ sub: 'user_test', exp })).replace(/=+$/, '');
	return `header.${payload}.signature`;
}

const future = tokenExpiringAt(4102444800); // 2100
const past = tokenExpiringAt(1_000_000_000); // 2001

function fakeLocalStorage(initial: Record<string, string> = {}) {
	const store = new Map(Object.entries(initial));
	return {
		getItem: (key: string) => store.get(key) ?? null,
		setItem: (key: string, value: string) => void store.set(key, value),
		removeItem: (key: string) => void store.delete(key),
		store
	};
}

afterEach(() => vi.unstubAllGlobals());

describe('MockAuth', () => {
	test('is loaded straight away and starts signed out without a stored token', () => {
		vi.stubGlobal('localStorage', fakeLocalStorage());
		const auth = new MockAuth();

		expect(auth.loaded).toBe(true);
		expect(auth.signedIn).toBe(false);
	});

	test('signInAs signs in and getToken returns the token', async () => {
		vi.stubGlobal('localStorage', fakeLocalStorage());
		const auth = new MockAuth();

		auth.signInAs(future);

		expect(auth.signedIn).toBe(true);
		expect(await auth.getToken()).toBe(future);
	});

	test('signInAs remembers the token across page loads', () => {
		const storage = fakeLocalStorage();
		vi.stubGlobal('localStorage', storage);

		new MockAuth().signInAs(future);

		expect(new MockAuth().signedIn).toBe(true);
	});

	test('treats an expired token as signed out', async () => {
		vi.stubGlobal('localStorage', fakeLocalStorage({ 'trips.token': past }));
		const auth = new MockAuth();

		expect(auth.signedIn).toBe(false);
		expect(await auth.getToken()).toBeNull();
	});

	test('signOut forgets the token', async () => {
		const storage = fakeLocalStorage();
		vi.stubGlobal('localStorage', storage);
		const auth = new MockAuth();
		auth.signInAs(future);

		await auth.signOut();

		expect(auth.signedIn).toBe(false);
		expect(storage.store.has('trips.token')).toBe(false);
	});

	test('works without localStorage (e.g. blocked storage)', async () => {
		const auth = new MockAuth(); // no localStorage in Node

		auth.signInAs(future);

		expect(await auth.getToken()).toBe(future);
	});
});
