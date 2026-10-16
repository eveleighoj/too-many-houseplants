// Regenerates src/lib/api/*.d.ts from the running backend's OpenAPI specs, so the frontend's
// types always match the API. Run after any backend API change: `npm run api:types`
// (needs the backend up, e.g. `make up`; set API_URL to point elsewhere).
// Runs a pinned openapi-typescript via npx rather than as a devDependency: it declares a
// TypeScript 5 peer dependency, which conflicts with this project's TypeScript 6.
import { execFileSync } from 'node:child_process';

const apiUrl = process.env.API_URL ?? 'http://localhost:8000';

for (const api of ['trips']) {
	execFileSync(
		'npx',
		[
			'-y',
			'openapi-typescript@7.13.0',
			`${apiUrl}/${api}/openapi.json`,
			'-o',
			`src/lib/api/${api}.d.ts`
		],
		{ stdio: 'inherit' }
	);
}
