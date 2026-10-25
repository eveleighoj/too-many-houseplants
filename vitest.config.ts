// Runs every frontend's tests from the repo root (`npm test`). Each frontend's own
// vite.config.ts defines its test projects; their tests live in tests/<frontend>/.
import { defineConfig } from 'vitest/config';

export default defineConfig({
	test: {
		projects: ['services/*-frontend/vitest.*.config.ts']
	}
});
