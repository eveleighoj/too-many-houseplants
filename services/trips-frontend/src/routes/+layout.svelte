<script lang="ts">
	import '../app.css';
	import favicon from '#lib/assets/favicon.svg';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { auth } from '#lib/auth/index.ts';
	import { goToLogin } from '#lib/navigation.ts';
	import type { LayoutProps } from './$types';

	let { children }: LayoutProps = $props();

	// Every page except /login needs a signed-in user (see docs/trips.md → Access). Pages
	// aren't rendered until then, so they never fetch anything for a signed-out visitor.
	const onLoginPage = $derived(page.url.pathname === resolve('/login'));
	const canShowPage = $derived(onLoginPage || (auth.loaded && auth.signedIn));

	$effect(() => {
		if (auth.loaded && !auth.signedIn && !onLoginPage) goToLogin();
	});

	async function logOut() {
		await auth.signOut();
		await goto(resolve('/login'));
	}
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<header>
	<nav>
		<a class="brand" href={resolve('/')}>Trips</a>
		{#if auth.signedIn}
			<button class="link" onclick={logOut}>Log out</button>
		{/if}
	</nav>
</header>

<main>
	{#if canShowPage}
		{@render children()}
	{:else}
		<p class="muted">Loading…</p>
	{/if}
</main>

<style>
	header {
		background: var(--surface);
		border-bottom: 1px solid var(--border);
	}
	nav,
	main {
		max-width: 48rem;
		margin: 0 auto;
		padding: 0.75rem 1rem;
	}
	nav {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}
	.brand {
		font-weight: 700;
		font-size: 1.15rem;
		text-decoration: none;
		color: var(--text);
	}
	main {
		padding-top: 1.5rem;
	}
	.muted {
		color: var(--muted);
	}
</style>
