import { describe, expect, test } from 'vitest';
import { render } from 'vitest-browser-svelte';
import TripDetails from 'trips-frontend/src/lib/components/TripDetails.svelte';
import { makeBooking, makeDay, makePlace, makeStay, makeStop, makeTrip } from '../../fixtures.ts';

function scotland() {
	const glenfinnan = makeStop({ place: makePlace({ name: 'Glenfinnan Viaduct' }) });
	const inn = makeStay({ place: makePlace({ name: 'Clachaig Inn' }), firstNight: 1, nights: 2 });
	return makeTrip({
		title: 'Scottish Highlands',
		days: [
			makeDay({ dayNumber: 1, date: '2026-11-14', stops: [glenfinnan] }),
			makeDay({ dayNumber: 2, date: '2026-11-15' }),
			makeDay({ dayNumber: 3, date: '2026-11-16' })
		],
		stays: [inn],
		bookings: [
			makeBooking({ stopId: glenfinnan.id, reference: 'JAC-3301' }),
			makeBooking({ stayId: inn.id, reference: 'CLA-48213' }),
			makeBooking({ place: makePlace({ name: 'Mallaig Ferry Terminal' }), reference: 'FERRY-1' })
		]
	});
}

describe('TripDetails', () => {
	test('shows the title, date range and each day', async () => {
		const screen = await render(TripDetails, { trip: scotland() });

		await expect
			.element(screen.getByRole('heading', { level: 1 }))
			.toHaveTextContent('Scottish Highlands');
		await expect.element(screen.getByText('Sat 14 Nov 2026 – Mon 16 Nov 2026')).toBeVisible();
		await expect.element(screen.getByRole('heading', { name: /Day 3/ })).toBeVisible();
	});

	test('shows stops with links to both map apps', async () => {
		const screen = await render(TripDetails, { trip: scotland() });

		await expect.element(screen.getByText('Glenfinnan Viaduct')).toBeVisible();
		await expect
			.element(screen.getByRole('link', { name: 'Google Maps' }).first())
			.toHaveAttribute('target', '_blank');
		await expect.element(screen.getByRole('link', { name: 'Apple Maps' }).first()).toBeVisible();
	});

	test('shows the stay under every night it covers, with its booking once', async () => {
		const screen = await render(TripDetails, { trip: scotland() });

		await expect.element(screen.getByText('Nights 1–2').nth(1)).toBeVisible();
		expect(screen.getByText('Nights 1–2').elements()).toHaveLength(2);
		expect(screen.getByText('CLA-48213').elements()).toHaveLength(1);
	});

	test('shows stop bookings and unattached bookings', async () => {
		const screen = await render(TripDetails, { trip: scotland() });

		await expect.element(screen.getByText('JAC-3301')).toBeVisible();
		await expect.element(screen.getByRole('heading', { name: 'Other bookings' })).toBeVisible();
		await expect.element(screen.getByText('FERRY-1')).toBeVisible();
	});

	test('says when nothing is planned yet', async () => {
		const screen = await render(TripDetails, { trip: makeTrip({ title: 'Japan' }) });

		await expect.element(screen.getByText('Nothing planned yet.')).toBeVisible();
	});
});
