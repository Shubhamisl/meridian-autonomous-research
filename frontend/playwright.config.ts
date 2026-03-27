import { defineConfig } from '@playwright/test';

const firebasePlaceholderEnv = {
  VITE_FIREBASE_API_KEY: 'your_firebase_api_key',
  VITE_FIREBASE_AUTH_DOMAIN: 'your_project.firebaseapp.com',
  VITE_FIREBASE_PROJECT_ID: 'your_project_id',
  VITE_FIREBASE_STORAGE_BUCKET: 'your_project.appspot.com',
  VITE_FIREBASE_MESSAGING_SENDER_ID: 'your_sender_id',
  VITE_FIREBASE_APP_ID: 'your_app_id',
} as const;

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  reporter: process.env.CI ? 'dot' : 'list',
  use: {
    baseURL: 'http://127.0.0.1:4173',
    trace: 'on-first-retry',
  },
  webServer: {
    command: 'npm run dev -- --host 127.0.0.1 --port 4173',
    url: 'http://127.0.0.1:4173',
    reuseExistingServer: true,
    timeout: 120_000,
    env: {
      VITE_E2E_TESTING: '1',
      ...firebasePlaceholderEnv,
    },
  },
});
