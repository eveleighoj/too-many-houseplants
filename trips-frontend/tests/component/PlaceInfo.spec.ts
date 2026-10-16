import { describe, expect, test } from 'vitest';
import { render } from 'vitest-browser-svelte';
import PlaceInfo from '#lib/components/PlaceInfo.svelte';
import { makePlace } from '../fixtures.ts';

describe('PlaceInfo', () => {
	test('shows the name and address', async () => {
		const screen = await render(PlaceInfo, {
			place: makePlace({ name: 'Portree Hotel', address: 'Somerled Square' })
		});

		await expect.element(screen.getByText('Portree Hotel')).toBeVisible();
		await expect.element(screen.getByText('Somerled Square')).toBeVisible();
	});

	test('links to the exact place when it has map ids', async () => {
		const screen = await render(PlaceInfo, {
			place: makePlace({
				googleMapsUrl: 'https://www.google.com/maps/place/?q=place_id:G',
				appleMapsUrl: 'https://maps.apple.com/place?place-id=A'
			})
		});

		await expect
			.element(screen.getByRole('link', { name: 'Google Maps' }))
			.toHaveAttribute('href', 'https://www.google.com/maps/place/?q=place_id:G');
		await expect
			.element(screen.getByRole('link', { name: 'Apple Maps' }))
			.toHaveAttribute('href', 'https://maps.apple.com/place?place-id=A');
	});

	test('opens map links in a new tab without leaking the opener', async () => {
		const screen = await render(PlaceInfo, { place: makePlace() });

		const link = screen.getByRole('link', { name: 'Google Maps' });
		await expect.element(link).toHaveAttribute('target', '_blank');
		await expect.element(link).toHaveAttribute('rel', expect.stringContaining('noopener'));
	});
});
