<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { fetchDevUsers, type DevUser } from '#lib/api/devUsers.ts';
	import { auth } from '#lib/auth.svelte.ts';
	import DevLogin from '#lib/components/DevLogin.svelte';
	import { MOCK_AUTH_URL } from '#lib/config.ts';
	import { safeNext } from '#lib/token.ts';

	let users = $state<DevUser[] | null>(null);
	let error = $state<string | null>(null);

	$effect(() => {
		if (!MOCK_AUTH_URL) return;
		fetchDevUsers(MOCK_AUTH_URL)
			.then((result) => (users = result))
			.catch(() => (error = `Can't reach clerk-mock at ${MOCK_AUTH_URL} — is the stack up?`));
	});

	async function pick(user: DevUser) {
		auth.set(user.token);
		// eslint-disable-next-line svelte/no-navigation-without-resolve -- safeNext only returns paths on this site
		await goto(safeNext(page.url.searchParams.get('next')));
	}
</script>

<svelte:head><title>Log in · Trips</title></svelte:head>

<h1>Log in</h1>

{#if !MOCK_AUTH_URL}
	<!-- Replaced by Clerk's sign-in once a Clerk application is configured. -->
	<p>Sign-in isn't configured for this build.</p>
{:else if error}
	<p class="error" role="alert">{error}</p>
{:else if users === null}
	<p>Loading…</p>
{:else}
	<DevLogin {users} onpick={pick} />
{/if}
