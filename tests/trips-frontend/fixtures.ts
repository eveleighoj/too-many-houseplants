// Builders for API response shapes, typed against the generated API types so fixtures break
// when the API changes. Override any field per test.
import type {
	Booking,
	Place,
	Stay,
	Stop,
	Trip,
	TripDay
} from 'trips-frontend/src/lib/api/types.ts';

let counter = 0;
const id = () => `00000000-0000-4000-8000-${String(++counter).padStart(12, '0')}`;

export function makePlace(overrides: Partial<Place> = {}): Place {
	return {
		id: id(),
		name: 'Glencoe',
		lat: 56.68,
		lng: -5.1,
		address: null,
		googlePlaceId: null,
		applePlaceId: null,
		googleMapsUrl: null,
		appleMapsUrl: null,
		...overrides
	};
}

export function makeStop(overrides: Partial<Stop> = {}): Stop {
	return { id: id(), place: makePlace(), ...overrides };
}

export function makeDay(overrides: Partial<TripDay> = {}): TripDay {
	return { dayNumber: 1, date: '2026-06-01', stops: [], ...overrides };
}

export function makeStay(overrides: Partial<Stay> = {}): Stay {
	return {
		id: id(),
		place: makePlace({ name: 'Clachaig Inn' }),
		firstNight: 1,
		nights: 1,
		...overrides
	};
}

export function makeBooking(overrides: Partial<Booking> = {}): Booking {
	return {
		id: id(),
		place: makePlace(),
		stopId: null,
		stayId: null,
		reference: 'REF-1',
		notes: null,
		...overrides
	};
}

export function makeTrip(overrides: Partial<Trip> = {}): Trip {
	return { id: id(), title: 'Scotland', days: [], stays: [], bookings: [], ...overrides };
}
