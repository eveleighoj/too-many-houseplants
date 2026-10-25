import { describe, expect, test } from 'vitest';
import {
	bookingsForStay,
	bookingsForStop,
	formatDate,
	mapLinks,
	nightsLabel,
	pluralise,
	staysForNight,
	tripDateRange,
	unattachedBookings
} from 'trips-frontend/src/lib/trips.ts';
import { makeBooking, makeDay, makePlace, makeStay, makeTrip } from '../fixtures.ts';

describe('formatDate', () => {
	test('formats an ISO date in British style', () => {
		expect(formatDate('2026-11-14')).toBe('Sat 14 Nov 2026');
	});
});

describe('tripDateRange', () => {
	test('spans the first to the last day', () => {
		const trip = makeTrip({
			days: [makeDay({ date: '2026-11-14' }), makeDay({ dayNumber: 2, date: '2026-11-15' })]
		});

		expect(tripDateRange(trip)).toBe('Sat 14 Nov 2026 – Sun 15 Nov 2026');
	});

	test('is a single date for a one-day trip', () => {
		expect(tripDateRange(makeTrip({ days: [makeDay({ date: '2026-11-14' })] }))).toBe(
			'Sat 14 Nov 2026'
		);
	});

	test('is null for a trip with no days yet', () => {
		expect(tripDateRange(makeTrip())).toBeNull();
	});
});

describe('pluralise', () => {
	test.each([
		[0, '0 days'],
		[1, '1 day'],
		[4, '4 days']
	])('pluralises %i', (count, expected) => {
		expect(pluralise(count, 'day')).toBe(expected);
	});
});

describe('nightsLabel', () => {
	test('names a single night', () => {
		expect(nightsLabel(makeStay({ firstNight: 3, nights: 1 }))).toBe('Night 3');
	});

	test('names a range of nights', () => {
		expect(nightsLabel(makeStay({ firstNight: 3, nights: 2 }))).toBe('Nights 3–4');
	});
});

describe('staysForNight', () => {
	const stay = makeStay({ firstNight: 3, nights: 2 });

	test.each([
		[2, false],
		[3, true],
		[4, true],
		[5, false]
	])('night %i covered: %s', (night, covered) => {
		expect(staysForNight([stay], night)).toEqual(covered ? [stay] : []);
	});
});

describe('bookings filters', () => {
	const forStop = makeBooking({ stopId: 'stop-1' });
	const forStay = makeBooking({ stayId: 'stay-1' });
	const unattached = makeBooking();
	const all = [forStop, forStay, unattached];

	test('bookingsForStop returns the stop’s bookings', () => {
		expect(bookingsForStop(all, 'stop-1')).toEqual([forStop]);
	});

	test('bookingsForStay returns the stay’s bookings', () => {
		expect(bookingsForStay(all, 'stay-1')).toEqual([forStay]);
	});

	test('unattachedBookings returns bookings for neither', () => {
		expect(unattachedBookings(all)).toEqual([unattached]);
	});
});

describe('mapLinks', () => {
	test('uses the place-id links when the API provides them', () => {
		const place = makePlace({
			googleMapsUrl: 'https://www.google.com/maps/place/?q=place_id:G',
			appleMapsUrl: 'https://maps.apple.com/place?place-id=A'
		});

		expect(mapLinks(place)).toEqual({
			google: 'https://www.google.com/maps/place/?q=place_id:G',
			apple: 'https://maps.apple.com/place?place-id=A'
		});
	});

	test('falls back to coordinates and name', () => {
		const links = mapLinks(makePlace({ name: 'Old Man of Storr', lat: 57.5, lng: -6.18 }));

		expect(links.google).toBe('https://www.google.com/maps/search/?api=1&query=57.5%2C-6.18');
		expect(links.apple).toBe('https://maps.apple.com/?ll=57.5%2C-6.18&q=Old%20Man%20of%20Storr');
	});
});
