/** Pure helpers for displaying trips. No I/O, no Svelte — unit tested in tests/unit/. */
import type { Booking, Place, Stay, Trip } from './api/types';

const dateFormat = new Intl.DateTimeFormat('en-GB', {
	weekday: 'short',
	day: 'numeric',
	month: 'short',
	year: 'numeric',
	timeZone: 'UTC'
});

/** "2026-11-14" → "Sat 14 Nov 2026". Dates have no time zone, so format them as UTC. Built
 * from parts because Intl's punctuation (e.g. a comma after the weekday) varies by runtime. */
export function formatDate(isoDate: string): string {
	const parts = Object.fromEntries(
		dateFormat
			.formatToParts(new Date(`${isoDate}T00:00:00Z`))
			.map((part) => [part.type, part.value])
	);
	return `${parts.weekday} ${parts.day} ${parts.month} ${parts.year}`;
}

/** "14 Nov 2026 – 17 Nov 2026", or null when no day has a date (e.g. the redacted view). */
export function tripDateRange(trip: Trip): string | null {
	const dates = trip.days.map((day) => day.date).filter((date): date is string => !!date);
	if (dates.length === 0) return null;
	const [first, last] = [dates[0], dates[dates.length - 1]];
	return first === last ? formatDate(first) : `${formatDate(first)} – ${formatDate(last)}`;
}

export function pluralise(count: number, word: string): string {
	return `${count} ${word}${count === 1 ? '' : 's'}`;
}

/** "Night 3" or "Nights 3–4". */
export function nightsLabel(stay: Stay): string {
	const last = stay.firstNight + stay.nights - 1;
	return stay.nights === 1 ? `Night ${stay.firstNight}` : `Nights ${stay.firstNight}–${last}`;
}

/** The stays covering the night of a given day. */
export function staysForNight(stays: Stay[], dayNumber: number): Stay[] {
	return stays.filter(
		(stay) => stay.firstNight <= dayNumber && dayNumber < stay.firstNight + stay.nights
	);
}

export function bookingsForStop(bookings: Booking[], stopId: string): Booking[] {
	return bookings.filter((booking) => booking.stopId === stopId);
}

export function bookingsForStay(bookings: Booking[], stayId: string): Booking[] {
	return bookings.filter((booking) => booking.stayId === stayId);
}

/** Bookings for neither a stop nor a stay, e.g. a ferry between two days. */
export function unattachedBookings(bookings: Booking[]): Booking[] {
	return bookings.filter((booking) => !booking.stopId && !booking.stayId);
}

/** Links to open a place in Google Maps and Apple Maps — by the place's own id when we have
 * one (exact match), otherwise by its coordinates and name. */
export function mapLinks(place: Place): { google: string; apple: string } {
	const coords = `${place.lat},${place.lng}`;
	return {
		google:
			place.googleMapsUrl ??
			`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(coords)}`,
		apple:
			place.appleMapsUrl ??
			`https://maps.apple.com/?ll=${encodeURIComponent(coords)}&q=${encodeURIComponent(place.name)}`
	};
}
