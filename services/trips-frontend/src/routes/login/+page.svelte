<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { fetchDevUsers, type DevUser } from '#lib/api/devUsers.ts';
	import { auth } from '#lib/auth/index.ts';
	import DevLogin from '#lib/components/DevLogin.svelte';
	import { MOCK_AUTH_URL } from '#lib/config.ts';
	import { safeNext } from '#lib/token.ts';

	let users = $state<DevUser[] | null>(null);
	let error = $state<string | null>(null);
	let clerkSignIn = $state<HTMLDivElement>();

	const next = $derived(safeNext(page.url.searchParams.get('next')));

	// Clerk: render its sign-in form, which navigates to `next` once signed in.
	$effect(() => {
		const element = clerkSignIn;
		if (auth.kind !== 'clerk' || !element) return;
		const clerk = auth;
		clerk.mountSignIn(element, next);
		return () => clerk.unmountSignIn(element);
	});

	$effect(() => {
		if (auth.kind !== 'mock' || !MOCK_AUTH_URL) return;
		fetchDevUsers(MOCK_AUTH_URL)
			.then((result) => (users = result))
			.catch(() => (error = `Can't reach clerk-mock at ${MOCK_AUTH_URL} — is the stack up?`));
	});

	async function pick(user: DevUser) {
		if (auth.kind !== 'mock') return;
		auth.signInAs(user.token);
		// eslint-disable-next-line svelte/no-navigation-without-resolve -- safeNext only returns paths on this site
		await goto(next);
	}
</script>

<svelte:head><title>Log in · Trips</title></svelte:head>

<h1>Log in</h1>

{#if auth.kind === 'clerk'}
	<div bind:this={clerkSignIn}></div>
{:else if auth.kind === 'none'}
	<p>Sign-in isn't configured for this build.</p>
{:else if error}
	<p class="error" role="alert">{error}</p>
{:else if users === null}
	<p>Loading…</p>
{:else}
	<DevLogin {users} onpick={pick} />
{/if}
