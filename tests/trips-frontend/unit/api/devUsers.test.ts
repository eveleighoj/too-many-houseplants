import { afterEach, describe, expect, test, vi } from 'vitest';
import { fetchDevUsers } from 'trips-frontend/src/lib/api/devUsers.ts';

const fetchMock = vi.fn<typeof fetch>();

afterEach(() => {
	vi.unstubAllGlobals();
	vi.clearAllMocks();
});

describe('fetchDevUsers', () => {
	test("returns clerk-mock's users", async () => {
		const users = [{ id: 'user_demo', name: 'Demo', email: 'demo@example.com', token: 't' }];
		fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ users })));
		vi.stubGlobal('fetch', fetchMock);

		expect(await fetchDevUsers('http://localhost:8082')).toEqual(users);
		expect(String(fetchMock.mock.lastCall![0])).toBe('http://localhost:8082/dev/users');
	});

	test('throws when clerk-mock responds with an error', async () => {
		fetchMock.mockResolvedValueOnce(new Response(null, { status: 404 }));
		vi.stubGlobal('fetch', fetchMock);

		await expect(fetchDevUsers('http://localhost:8082')).rejects.toThrow('404');
	});
});
