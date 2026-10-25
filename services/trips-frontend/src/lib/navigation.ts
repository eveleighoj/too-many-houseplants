import { goto } from '$app/navigation';
import { resolve } from '$app/paths';

/** Sends the user to /login, returning to `next` (default: the current page) afterwards. */
export function goToLogin(next: string = location.pathname + location.search): Promise<void> {
	const url = `${resolve('/login')}?next=${encodeURIComponent(next)}`;
	// eslint-disable-next-line svelte/no-navigation-without-resolve -- resolved above; only the query string is appended
	return goto(url);
}
