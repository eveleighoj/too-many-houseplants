// Regenerates src/lib/api/*.d.ts from the backend's OpenAPI specs, so the frontend's types
// always match the API. Run after any backend API change: `npm run api:types`.
//
// By default it reads the running backend (e.g. after `make up`; set API_URL to point
// elsewhere). Set API_SPEC_DIR to read <dir>/<api>.json files instead, as written by the
// backend's `python -m houseplants.export_openapi <dir>` — no running backend needed (CI and
// `make api-types-check` do this).
//
// Runs a pinned openapi-typescript via npx rather than as a devDependency: it declares a
// TypeScript 5 peer dependency, which conflicts with this project's TypeScript 6.
import { execFileSync } from 'node:child_process';

const apiUrl = process.env.API_URL ?? 'http://localhost:8000';
const specDir = process.env.API_SPEC_DIR;

for (const api of ['trips']) {
	const source = specDir ? `${specDir}/${api}.json` : `${apiUrl}/${api}/openapi.json`;
	execFileSync(
		'npx',
		['-y', 'openapi-typescript@7.13.0', source, '-o', `src/lib/api/${api}.d.ts`],
		{ stdio: 'inherit' }
	);
}
