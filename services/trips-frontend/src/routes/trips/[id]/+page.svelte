<script lang="ts">
	import { page } from '$app/state';
	import { resolve } from '$app/paths';
	import { ApiError, UnauthorizedError, getTrip } from '#lib/api/client.ts';
	import type { Trip } from '#lib/api/types.ts';
	import { auth } from '#lib/auth.svelte.ts';
	import TripDetails from '#lib/components/TripDetails.svelte';
	import { goToLogin } from '#lib/navigation.ts';

	let trip = $state<Trip | null>(null);
	let error = $state<string | null>(null);

	// Anyone can open a trip link: logged out (or not the owner), the API returns the redacted view.
	$effect(() => {
		const id = page.params.id!;
		trip = null;
		error = null;
		getTrip(id)
			.then((result) => (trip = result))
			.catch((e) => {
				if (e instanceof UnauthorizedError) return;
				if (e instanceof ApiError && (e.status === 404 || e.status === 422)) {
					error = "This trip doesn't exist.";
				} else {
					error = e instanceof ApiError ? e.message : 'Could not reach the server';
				}
			});
	});
</script>

<svelte:head><title>{trip?.title ?? 'Trip'} · Trips</title></svelte:head>

<p><a href={resolve('/')}>← Your trips</a></p>

{#if error}
	<p class="error" role="alert">{error}</p>
{:else if trip === null}
	<p class="muted">Loading…</p>
{:else}
	<TripDetails {trip} />
	{#if !auth.loggedIn && trip.stays === null}
		<p class="muted">
			Is this your trip?
			<button class="link" onclick={() => goToLogin()}>Log in</button> to see everything.
		</p>
	{/if}
{/if}

<style>
	.muted {
		color: var(--muted);
	}
</style>
