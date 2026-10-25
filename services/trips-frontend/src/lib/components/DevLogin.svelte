<script lang="ts">
	import type { DevUser } from '#lib/api/devUsers.ts';

	let { users, onpick }: { users: DevUser[]; onpick: (user: DevUser) => void } = $props();
</script>

<p class="hint">Local development: pick a dev user from clerk-mock.</p>

<ul>
	{#each users as user (user.id)}
		<li>
			<button onclick={() => onpick(user)}>Log in as {user.name}</button>
			<span class="detail">{user.email} · <code>{user.id}</code></span>
		</li>
	{/each}
</ul>

<style>
	.hint {
		color: var(--muted);
	}
	ul {
		list-style: none;
		padding: 0;
		display: grid;
		gap: 0.75rem;
	}
	li {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.5rem 1rem;
	}
	.detail {
		color: var(--muted);
		font-size: 0.9rem;
	}
</style>
