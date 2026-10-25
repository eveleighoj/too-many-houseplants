import { describe, expect, test } from 'vitest';
import { frontendApiHost } from 'trips-frontend/src/lib/auth/clerk.svelte.ts';

describe('frontendApiHost', () => {
	test('decodes a development key to its clerk.accounts.dev host', () => {
		const key = `pk_test_${btoa('endless-yak-8528.clerk.accounts.dev$')}`;

		expect(frontendApiHost(key)).toBe('endless-yak-8528.clerk.accounts.dev');
	});

	test('decodes a production key to its custom domain', () => {
		const key = `pk_live_${btoa('clerk.example.com$')}`;

		expect(frontendApiHost(key)).toBe('clerk.example.com');
	});
});
