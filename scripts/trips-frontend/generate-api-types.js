// Regenerates trips-frontend's src/lib/api/*.d.ts from the api's OpenAPI specs, so its types
// always match the API. Run after any api change: `make api-types` (= `npm run api:types
// -w services/trips-frontend`, which runs this from the services/trips-frontend folder).
//
// By default it reads the running backend (e.g. after `make up`; set API_URL to point
// elsewhere). Set API_SPEC_DIR to read <dir>/<api>.json files instead, as written by
// `python -m scripts.api.export_openapi <dir>` — no running backend needed (CI and
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
