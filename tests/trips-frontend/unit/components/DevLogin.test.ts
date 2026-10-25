import { describe, expect, test, vi } from 'vitest';
import { render } from 'vitest-browser-svelte';
import DevLogin from 'trips-frontend/src/lib/components/DevLogin.svelte';

const users = [
	{ id: 'user_demo', name: 'Demo', email: 'demo@example.com', token: 'demo-token' },
	{ id: 'user_friend', name: 'Friend', email: 'friend@example.com', token: 'friend-token' }
];

describe('DevLogin', () => {
	test('lists every dev user with their id', async () => {
		const screen = await render(DevLogin, { users, onpick: () => {} });

		await expect.element(screen.getByRole('button', { name: 'Log in as Demo' })).toBeVisible();
		await expect.element(screen.getByRole('button', { name: 'Log in as Friend' })).toBeVisible();
		await expect.element(screen.getByText('user_friend')).toBeVisible();
	});

	test('passes the picked user to onpick', async () => {
		const onpick = vi.fn();
		const screen = await render(DevLogin, { users, onpick });

		await screen.getByRole('button', { name: 'Log in as Friend' }).click();

		expect(onpick).toHaveBeenCalledWith(users[1]);
	});
});
