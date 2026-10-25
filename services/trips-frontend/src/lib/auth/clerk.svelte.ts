import type { Clerk } from '@clerk/clerk-js';
import { goto } from '$app/navigation';
import type { AuthProvider } from './provider.ts';

// Clerk's SDK and its prebuilt UI (the sign-in form) both load at runtime from the instance's own
// Frontend API, as Clerk's script-tag setup does. Its browser build is ~85 KB and fetches the
// rest on demand; bundling @clerk/clerk-js from npm would add ~500 KB (compressed) to this app,
// and bundling @clerk/ui would pull in React. The npm package is only a dev dependency, for its
// types. Both are pinned to exact versions, so what runs only changes when these do: keep
// CLERK_JS_VERSION equal to @clerk/clerk-js's version in package.json.
export const CLERK_JS_VERSION = '6.40.1';
export const CLERK_UI_VERSION = '1.41.2';

type ClerkUIConstructor = NonNullable<
	NonNullable<NonNullable<Parameters<Clerk['load']>[0]>['ui']>['ClerkUI']
>;

declare global {
	interface Window {
		Clerk?: Clerk;
		__internal_ClerkUICtor?: Awaited<ClerkUIConstructor>;
	}
}

/** The Frontend API host a publishable key belongs to: the key is `pk_<env>_` + base64 of
 * `<host>$`. */
export function frontendApiHost(publishableKey: string): string {
	const encoded = publishableKey.split('_')[2] ?? '';
	return atob(encoded).replace(/\$$/, '');
}

function loadScript(src: string, attributes: Record<string, string> = {}): Promise<void> {
	return new Promise((resolve, reject) => {
		const script = document.createElement('script');
		script.src = src;
		script.async = true;
		script.crossOrigin = 'anonymous';
		for (const [name, value] of Object.entries(attributes)) script.setAttribute(name, value);
		script.onload = () => resolve();
		script.onerror = () => reject(new Error(`Couldn't load ${src}`));
		document.head.appendChild(script);
	});
}

/** Clerk's SDK, created for this publishable key (the script sets `window.Clerk`). */
async function loadClerk(publishableKey: string): Promise<Clerk> {
	const host = frontendApiHost(publishableKey);
	await loadScript(
		`https://${host}/npm/@clerk/clerk-js@${CLERK_JS_VERSION}/dist/clerk.browser.js`,
		{
			'data-clerk-publishable-key': publishableKey
		}
	);
	if (!window.Clerk) throw new Error('Clerk SDK loaded without creating window.Clerk');
	return window.Clerk;
}

async function loadClerkUi(publishableKey: string): Promise<Awaited<ClerkUIConstructor>> {
	const host = frontendApiHost(publishableKey);
	await loadScript(`https://${host}/npm/@clerk/ui@${CLERK_UI_VERSION}/dist/ui.browser.js`);
	if (!window.__internal_ClerkUICtor) throw new Error('Clerk UI loaded without its UI');
	return window.__internal_ClerkUICtor;
}

/** Sign-in with Clerk (https://clerk.com). Clerk keeps the session itself (a long-lived
 * httpOnly cookie on its own domain) and hands out short-lived tokens for the API. */
export class ClerkAuth implements AuthProvider {
	readonly kind = 'clerk';
	loaded = $state(false);
	signedIn = $state(false);

	#clerk: Clerk | null = null;
	readonly #ready: Promise<void>;

	constructor(publishableKey: string) {
		this.#ready = this.#load(publishableKey);
	}

	async #load(publishableKey: string): Promise<void> {
		// Loaded only in builds that use Clerk, and from Clerk (see the comment at the top).
		const clerk = await loadClerk(publishableKey);
		await clerk.load({
			ui: { ClerkUI: loadClerkUi(publishableKey) },
			// Clerk's own navigations (e.g. after signing in) go through SvelteKit's router.
			// eslint-disable-next-line svelte/no-navigation-without-resolve -- Clerk passes in app paths
			routerPush: (to) => goto(to),
			// eslint-disable-next-line svelte/no-navigation-without-resolve -- Clerk passes in app paths
			routerReplace: (to) => goto(to, { replaceState: true }),
			signInUrl: '/login',
			afterSignOutUrl: '/login'
		});
		this.#clerk = clerk;
		this.signedIn = clerk.isSignedIn;
		clerk.addListener(({ session }) => {
			this.signedIn = Boolean(session);
		});
		this.loaded = true;
	}

	async getToken(): Promise<string | null> {
		await this.#ready;
		// Returns a cached token, or a fresh one when it's about to expire (~60s lifetime).
		return (await this.#clerk?.session?.getToken()) ?? null;
	}

	async signOut(): Promise<void> {
		await this.#ready;
		await this.#clerk?.signOut();
	}

	/** Renders Clerk's sign-in form into `element`, then goes to `next` once signed in. */
	async mountSignIn(element: HTMLDivElement, next: string): Promise<void> {
		await this.#ready;
		this.#clerk?.mountSignIn(element, {
			// Clerk's multi-step flow lives in the URL hash, so /login needs no extra routes.
			routing: 'hash',
			fallbackRedirectUrl: next
		});
	}

	unmountSignIn(element: HTMLDivElement): void {
		this.#clerk?.unmountSignIn(element);
	}
}
