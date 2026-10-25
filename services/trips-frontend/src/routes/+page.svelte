<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { ApiError, UnauthorizedError, createTrip, listTrips } from '#lib/api/client.ts';
	import type { Trip } from '#lib/api/types.ts';
	import { pluralise, tripDateRange } from '#lib/trips.ts';

	let trips = $state<Trip[] | null>(null);
	let loadError = $state<string | null>(null);

	let title = $state('');
	let createError = $state<string | null>(null);
	let creating = $state(false);

	$effect(() => {
		listTrips()
			.then((result) => (trips = result))
			.catch((e) => {
				if (!(e instanceof UnauthorizedError)) {
					loadError = e instanceof ApiError ? e.message : 'Could not reach the server';
				}
			});
	});

	async function create(event: SubmitEvent) {
		event.preventDefault();
		creating = true;
		createError = null;
		try {
			const trip = await createTrip(title);
			await goto(resolve('/trips/[id]', { id: trip.id }));
		} catch (e) {
			if (!(e instanceof UnauthorizedError)) {
				createError = e instanceof ApiError ? e.message : 'Could not reach the server';
			}
		} finally {
			creating = false;
		}
	}
</script>

<svelte:head><title>Trips</title></svelte:head>

<h1>Trips</h1>

{#if loadError}
	<p class="error" role="alert">{loadError}</p>
{:else if trips === null}
	<p class="muted">Loading…</p>
{:else if trips.length === 0}
	<p class="muted">No trips yet — create one below.</p>
{:else}
	<ul class="trips">
		{#each trips as trip (trip.id)}
			<li>
				<a href={resolve('/trips/[id]', { id: trip.id })}>
					<span class="title">{trip.title}</span>
					<span class="meta">
						{tripDateRange(trip) ?? 'No dates yet'} · {pluralise(trip.days.length, 'day')}
					</span>
				</a>
			</li>
		{/each}
	</ul>
{/if}

<form onsubmit={create}>
	<h2>New trip</h2>
	<div class="row">
		<input
			bind:value={title}
			placeholder="e.g. Cornwall in June"
			aria-label="Trip title"
			required
		/>
		<button type="submit" disabled={creating}>{creating ? 'Creating…' : 'Create'}</button>
	</div>
	{#if createError}<p class="error" role="alert">{createError}</p>{/if}
</form>

<style>
	.muted {
		color: var(--muted);
	}
	.trips {
		list-style: none;
		padding: 0;
		display: grid;
		gap: 0.75rem;
	}
	.trips a {
		display: grid;
		gap: 0.15rem;
		padding: 1rem;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 8px;
		text-decoration: none;
		color: var(--text);
	}
	.trips a:hover {
		border-color: var(--accent);
	}
	.title {
		font-weight: 600;
	}
	.meta {
		color: var(--muted);
		font-size: 0.9rem;
	}
	form {
		margin-top: 2rem;
	}
	h2 {
		font-size: 1.1rem;
	}
	.row {
		display: flex;
		gap: 0.5rem;
	}
	.row input {
		flex: 1;
		min-width: 0;
	}
</style>
