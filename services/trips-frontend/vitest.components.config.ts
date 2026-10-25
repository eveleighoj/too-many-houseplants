// trips-frontend's component tests: rendered in a real (headless) Chromium.
import { playwright } from '@vitest/browser-playwright';
import { defineProject, mergeConfig } from 'vitest/config';
import viteConfig from './vite.config.ts';

export default mergeConfig(
	viteConfig,
	defineProject({
		test: {
			name: 'trips-frontend:components',
			include: ['unit/components/**/*.test.ts'],
			browser: {
				enabled: true,
				provider: playwright(),
				instances: [{ browser: 'chromium', headless: true }]
			}
		}
	})
);
