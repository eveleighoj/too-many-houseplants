<script lang="ts">
	import type { Booking } from '#lib/api/types.ts';
	import PlaceInfo from './PlaceInfo.svelte';

	/** showPlace: false when the booking sits under its own stop/stay, which already shows it. */
	let { booking, showPlace = true }: { booking: Booking; showPlace?: boolean } = $props();
</script>

<div class="booking">
	<span class="label">Booking</span>
	{#if booking.reference}<code class="reference">{booking.reference}</code>{/if}
	{#if booking.notes}<span class="notes">{booking.notes}</span>{/if}
	{#if showPlace}<div class="place"><PlaceInfo place={booking.place} /></div>{/if}
</div>

<style>
	.booking {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 0.25rem 0.6rem;
		padding: 0.4rem 0.6rem;
		border-left: 3px solid var(--accent);
		background: var(--accent-soft);
		border-radius: 4px;
		font-size: 0.9rem;
	}
	.label {
		font-weight: 600;
		color: var(--accent);
		text-transform: uppercase;
		font-size: 0.7rem;
		letter-spacing: 0.05em;
	}
	.reference {
		font-family: ui-monospace, monospace;
	}
	.place {
		width: 100%;
	}
</style>
