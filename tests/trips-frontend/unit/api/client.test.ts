import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';

// The real navigation needs a browser; record redirects instead.
vi.mock('trips-frontend/src/lib/navigation.ts', () => ({ goToLogin: vi.fn() }));
// A mock-provider session the tests control, whatever this build is configured for.
vi.mock('trips-frontend/src/lib/auth/index.ts', async () => {
	const { MockAuth } = await import('trips-frontend/src/lib/auth/mock.svelte.ts');
	return { auth: new MockAuth() };
});

import {
	ApiError,
	UnauthorizedError,
	authFetch,
	createTrip,
	getTrip,
	listTrips
} from 'trips-frontend/src/lib/api/client.ts';
import { auth as configuredAuth } from 'trips-frontend/src/lib/auth/index.ts';
import type { MockAuth } from 'trips-frontend/src/lib/auth/mock.svelte.ts';
import { goToLogin } from 'trips-frontend/src/lib/navigation.ts';
import { makeTrip } from '../../fixtures.ts';

const auth = configuredAuth as MockAuth;

/** A token MockAuth accepts: any JWT-shaped string with an `exp` in the future. */
function validToken(): string {
	const payload = btoa(JSON.stringify({ sub: 'user_test', exp: 4102444800 })).replace(/=+$/, '');
	return `header.${payload}.signature`;
}

const fetchMock = vi.fn<typeof fetch>();

function respond(status: number, body?: unknown) {
	fetchMock.mockResolvedValueOnce(
		new Response(body === undefined ? null : JSON.stringify(body), {
			status,
			headers: { 'Content-Type': 'application/json' }
		})
	);
}

function lastRequest(): { url: string; init: RequestInit; headers: Headers } {
	const [url, init = {}] = fetchMock.mock.lastCall!;
	return { url: String(url), init, headers: new Headers(init.headers) };
}

beforeEach(() => {
	vi.stubGlobal('fetch', fetchMock);
	auth.signOut();
});

afterEach(() => {
	vi.unstubAllGlobals();
	vi.clearAllMocks();
});

describe('authFetch', () => {
	test('attaches the bearer token when logged in', async () => {
		auth.signInAs(validToken());
		respond(200, {});

		await authFetch('/trips/');

		expect(lastRequest().url).toBe('http://localhost:8000/trips/');
		expect(lastRequest().headers.get('Authorization')).toBe(`Bearer ${validToken()}`);
	});

	test('sends no Authorization header when logged out', async () => {
		respond(200, {});

		await authFetch('/trips/');

		expect(lastRequest().headers.has('Authorization')).toBe(false);
	});

	test('on 401 logs out, redirects to login, and throws UnauthorizedError', async () => {
		auth.signInAs(validToken());
		respond(401, { detail: 'authentication required' });

		await expect(authFetch('/trips/')).rejects.toBeInstanceOf(UnauthorizedError);

		expect(auth.signedIn).toBe(false);
		expect(goToLogin).toHaveBeenCalledOnce();
	});

	test('returns other error responses for the caller to handle', async () => {
		respond(404, { detail: 'trip not found' });

		expect((await authFetch('/trips/x')).status).toBe(404);
		expect(goToLogin).not.toHaveBeenCalled();
	});
});

describe('listTrips', () => {
	test('returns the trips array', async () => {
		const trip = makeTrip();
		respond(200, { trips: [trip] });

		expect(await listTrips()).toEqual([trip]);
	});
});

describe('getTrip', () => {
	test('fetches the trip by id', async () => {
		respond(200, makeTrip({ id: 'abc' }));

		expect((await getTrip('abc')).id).toBe('abc');
		expect(lastRequest().url).toBe('http://localhost:8000/trips/abc');
	});

	test('throws ApiError with the API’s detail on failure', async () => {
		respond(404, { detail: 'trip not found' });

		const error = await getTrip('missing').catch((e) => e);

		expect(error).toBeInstanceOf(ApiError);
		expect(error.status).toBe(404);
		expect(error.message).toBe('trip not found');
	});
});

describe('createTrip', () => {
	test('posts the title as JSON', async () => {
		respond(201, makeTrip({ title: 'Wales' }));

		expect((await createTrip('Wales')).title).toBe('Wales');
		expect(lastRequest().init.method).toBe('POST');
		expect(lastRequest().headers.get('Content-Type')).toBe('application/json');
		expect(JSON.parse(lastRequest().init.body as string)).toEqual({ title: 'Wales' });
	});
});
