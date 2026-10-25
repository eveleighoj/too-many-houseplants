import { auth } from '../auth.svelte.ts';
import { API_URL } from '../config.ts';
import { goToLogin } from '../navigation.ts';
import type { Trip, TripList } from './types.ts';

export class ApiError extends Error {
	constructor(
		readonly status: number,
		message: string
	) {
		super(message);
	}
}

/** Thrown after a 401 has already sent the user to the login page — callers can ignore it. */
export class UnauthorizedError extends ApiError {
	constructor() {
		super(401, 'Please log in again');
	}
}

/** fetch() against the API, with the bearer token attached. A 401 logs the user out and sends
 * them to /login, coming back to the current page afterwards (see ARCHITECTURE.md → Auth). */
export async function authFetch(path: string, init: RequestInit = {}): Promise<Response> {
	const headers = new Headers(init.headers);
	if (auth.token) headers.set('Authorization', `Bearer ${auth.token}`);

	const response = await fetch(`${API_URL}${path}`, { ...init, headers });

	if (response.status === 401) {
		auth.clear();
		await goToLogin();
		throw new UnauthorizedError();
	}
	return response;
}

async function readJson<T>(response: Response): Promise<T> {
	if (!response.ok) {
		const body = await response.json().catch(() => null);
		const detail = typeof body?.detail === 'string' ? body.detail : response.statusText;
		throw new ApiError(response.status, detail || `Request failed (${response.status})`);
	}
	return response.json();
}

function jsonBody(body: unknown): RequestInit {
	return {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	};
}

export async function listTrips(): Promise<Trip[]> {
	return (await readJson<TripList>(await authFetch('/trips/'))).trips;
}

export async function getTrip(id: string): Promise<Trip> {
	return readJson<Trip>(await authFetch(`/trips/${encodeURIComponent(id)}`));
}

export async function createTrip(title: string): Promise<Trip> {
	return readJson<Trip>(await authFetch('/trips/', jsonBody({ title })));
}
