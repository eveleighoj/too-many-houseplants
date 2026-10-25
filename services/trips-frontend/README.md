# trips-frontend

The Svelte frontend for the trips API — a static single-page app (SvelteKit +
`adapter-static`). See [docs/frontend.md](../../docs/frontend.md) for how it's built, run,
tested and hosted.

From the repo root (it's an npm workspace):

```bash
make setup                               # installs everything
npm run dev -w services/trips-frontend   # http://localhost:5173 (or `make up`)
make test-frontends                      # unit + component tests (in tests/trips-frontend/)
make api-types                           # regenerate API types from the running api
```
