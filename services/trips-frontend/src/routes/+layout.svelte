<script lang="ts">
	import '../app.css';
	import favicon from '#lib/assets/favicon.svg';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { auth } from '#lib/auth.svelte.ts';
	import type { LayoutProps } from './$types';

	let { children }: LayoutProps = $props();

	async function logOut() {
		auth.clear();
		await goto(resolve('/login'));
	}
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<header>
	<nav>
		<a class="brand" href={resolve('/')}>Trips</a>
		{#if auth.loggedIn}
			<button class="link" onclick={logOut}>Log out</button>
		{:else}
			<a href={resolve('/login')}>Log in</a>
		{/if}
	</nav>
</header>

<main>
	{@render children()}
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
</style>
