import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vitest/config';
import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';

export default defineConfig({
	plugins: [
		sveltekit({
			compilerOptions: {
				// Force runes mode for the project, except for libraries. Can be removed in svelte 6.
				runes: ({ filename }) =>
					filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},
			// SPA: every path is served index.html and routed in the browser. Hosts must rewrite
			// unknown paths to /index.html (see render.yaml and ARCHITECTURE.md).
			adapter: adapter({ fallback: 'index.html' })
		})
	],
	test: {
		expect: { requireAssertions: true },
		// Tests live outside the app, in the repo's tests/trips-frontend/ (see
		// docs/repository-structure.md), and import it through its workspace package name
		// (`trips-frontend/src/lib/...`). vitest.unit.config.ts and vitest.components.config.ts
		// define the two test projects; the root vitest.config.ts runs them.
		dir: fileURLToPath(new URL('../../tests/trips-frontend', import.meta.url))
	}
});
