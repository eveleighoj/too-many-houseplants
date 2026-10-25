<script lang="ts">
	import type { Place } from '#lib/api/types.ts';
	import { mapLinks } from '#lib/trips.ts';

	let { place }: { place: Place } = $props();

	const links = $derived(mapLinks(place));
</script>

<span class="place">
	<span class="name">{place.name}</span>
	{#if place.address}<span class="address">{place.address}</span>{/if}
	<span class="links">
		<!-- External sites, so there's no app route to resolve(). -->
		<!-- eslint-disable-next-line svelte/no-navigation-without-resolve -->
		<a href={links.google} target="_blank" rel="noopener noreferrer external">Google Maps</a>
		<!-- eslint-disable-next-line svelte/no-navigation-without-resolve -->
		<a href={links.apple} target="_blank" rel="noopener noreferrer external">Apple Maps</a>
	</span>
</span>

<style>
	.place {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 0.25rem 0.75rem;
	}
	.name {
		font-weight: 600;
	}
	.address {
		color: var(--muted);
		font-size: 0.9rem;
	}
	.links {
		display: inline-flex;
		gap: 0.5rem;
		font-size: 0.85rem;
	}
</style>
