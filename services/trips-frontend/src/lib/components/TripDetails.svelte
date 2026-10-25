<script lang="ts">
	import type { Trip } from '#lib/api/types.ts';
	import {
		bookingsForStay,
		bookingsForStop,
		formatDate,
		nightsLabel,
		staysForNight,
		tripDateRange,
		unattachedBookings
	} from '#lib/trips.ts';
	import BookingInfo from './BookingInfo.svelte';
	import PlaceInfo from './PlaceInfo.svelte';

	let { trip }: { trip: Trip } = $props();

	const stays = $derived(trip.stays);
	const bookings = $derived(trip.bookings);
	const otherBookings = $derived(unattachedBookings(bookings));
	const dateRange = $derived(tripDateRange(trip));
</script>

<article>
	<header>
		<h1>{trip.title}</h1>
		{#if dateRange}<p class="dates">{dateRange}</p>{/if}
	</header>

	{#if trip.days.length === 0}
		<p class="empty">Nothing planned yet.</p>
	{/if}

	<ol class="days">
		{#each trip.days as day (day.dayNumber)}
			<li class="day">
				<h2>
					Day {day.dayNumber}
					<span class="date">{formatDate(day.date)}</span>
				</h2>

				{#if day.stops.length > 0}
					<ol class="stops">
						{#each day.stops as stop (stop.id)}
							<li>
								<PlaceInfo place={stop.place} />
								{#each bookingsForStop(bookings, stop.id) as booking (booking.id)}
									<BookingInfo {booking} showPlace={false} />
								{/each}
							</li>
						{/each}
					</ol>
				{/if}

				{#each staysForNight(stays, day.dayNumber) as stay (stay.id)}
					<div class="stay">
						<span class="stay-label">Staying at</span>
						<PlaceInfo place={stay.place} />
						<span class="nights">{nightsLabel(stay)}</span>
						{#if stay.firstNight === day.dayNumber}
							{#each bookingsForStay(bookings, stay.id) as booking (booking.id)}
								<BookingInfo {booking} showPlace={false} />
							{/each}
						{/if}
					</div>
				{/each}
			</li>
		{/each}
	</ol>

	{#if otherBookings.length > 0}
		<section class="other-bookings">
			<h2>Other bookings</h2>
			{#each otherBookings as booking (booking.id)}
				<BookingInfo {booking} />
			{/each}
		</section>
	{/if}
</article>

<style>
	header {
		margin-bottom: 1rem;
	}
	h1 {
		margin: 0;
	}
	.dates {
		margin: 0.25rem 0 0;
		color: var(--muted);
	}
	.empty {
		color: var(--muted);
	}
	.days,
	.stops {
		list-style: none;
		padding: 0;
		margin: 0;
	}
	.day {
		padding: 1rem;
		margin-bottom: 1rem;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 8px;
	}
	.day h2 {
		margin: 0 0 0.75rem;
		font-size: 1.1rem;
		display: flex;
		gap: 0.75rem;
		align-items: baseline;
	}
	.date {
		font-weight: 400;
		color: var(--muted);
		font-size: 0.95rem;
	}
	.stops li {
		display: grid;
		gap: 0.4rem;
		padding: 0.5rem 0;
		border-top: 1px solid var(--border);
	}
	.stops li:first-child {
		border-top: none;
	}
	.stay {
		display: grid;
		gap: 0.4rem;
		margin-top: 0.75rem;
		padding: 0.6rem 0.75rem;
		border-radius: 6px;
		background: var(--surface-2);
	}
	.stay-label,
	.nights {
		font-size: 0.8rem;
		color: var(--muted);
	}
	.other-bookings {
		display: grid;
		gap: 0.5rem;
	}
	.other-bookings h2 {
		font-size: 1.1rem;
		margin: 0.5rem 0 0;
	}
</style>
