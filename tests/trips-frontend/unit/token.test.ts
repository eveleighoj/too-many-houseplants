import { describe, expect, test } from 'vitest';
import { isExpired, safeNext, tokenExpiry } from 'trips-frontend/src/lib/token.ts';

function tokenWith(payload: object): string {
	const encode = (value: object) => btoa(JSON.stringify(value)).replace(/=+$/, '');
	return `${encode({ alg: 'HS256' })}.${encode(payload)}.signature`;
}

describe('tokenExpiry', () => {
	test('reads the exp claim in milliseconds', () => {
		expect(tokenExpiry(tokenWith({ exp: 1_800_000_000 }))).toBe(1_800_000_000_000);
	});

	test('is null without an exp claim', () => {
		expect(tokenExpiry(tokenWith({ sub: 'x' }))).toBeNull();
	});

	test('is null for something that is not a JWT', () => {
		expect(tokenExpiry('not-a-token')).toBeNull();
	});
});

describe('isExpired', () => {
	const token = tokenWith({ exp: 1_000 });

	test('is false before exp', () => {
		expect(isExpired(token, 999_999)).toBe(false);
	});

	test('is true at or after exp', () => {
		expect(isExpired(token, 1_000_000)).toBe(true);
	});

	test('treats an unreadable token as expired', () => {
		expect(isExpired('garbage')).toBe(true);
	});
});

describe('safeNext', () => {
	test('returns a path on this site', () => {
		expect(safeNext('/trips/abc?x=1')).toBe('/trips/abc?x=1');
	});

	test.each([null, '', 'https://evil.example', '//evil.example', '/\\evil.example', 'trips'])(
		'falls back to home for %j',
		(next) => {
			expect(safeNext(next)).toBe('/');
		}
	);
});
