// trips-frontend's unit tests: plain functions, run in Node.
import { configDefaults, defineProject, mergeConfig } from 'vitest/config';
import viteConfig from './vite.config.ts';

export default mergeConfig(
	viteConfig,
	defineProject({
		test: {
			name: 'trips-frontend:unit',
			environment: 'node',
			include: ['unit/**/*.test.ts'],
			exclude: [...configDefaults.exclude, 'unit/components/**']
		}
	})
);
