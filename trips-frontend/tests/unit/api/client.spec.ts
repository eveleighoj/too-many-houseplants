import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';

// The real navigation needs a browser; record redirects instead.
vi.mock('#lib/navigation.ts', () => ({ goToLogin: vi.fn() }));

import {
	ApiError,
	UnauthorizedError,
	authFetch,
	createTrip,
	getTrip,
	listTrips
} from '#lib/api/client.ts';
import { auth } from '#lib/auth.svelte.ts';
import { goToLogin } from '#lib/navigation.ts';
import { makeTrip } from '../../fixtures.ts';

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
	auth.clear();
});

afterEach(() => {
	vi.unstubAllGlobals();
	vi.clearAllMocks();
});

describe('authFetch', () => {
	test('attaches the bearer token when logged in', async () => {
		auth.set('a-token');
		respond(200, {});

		await authFetch('/trips/');

		expect(lastRequest().url).toBe('http://localhost:8000/trips/');
		expect(lastRequest().headers.get('Authorization')).toBe('Bearer a-token');
	});

	test('sends no Authorization header when logged out', async () => {
		respond(200, {});

		await authFetch('/trips/');

		expect(lastRequest().headers.has('Authorization')).toBe(false);
	});

	test('on 401 logs out, redirects to login, and throws UnauthorizedError', async () => {
		auth.set('expired-token');
		respond(401, { detail: 'authentication required' });

		await expect(authFetch('/trips/')).rejects.toBeInstanceOf(UnauthorizedError);

		expect(auth.token).toBeNull();
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
