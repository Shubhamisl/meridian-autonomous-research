import { initializeApp, type FirebaseApp } from 'firebase/app';
import { getAuth, GoogleAuthProvider, type Auth } from 'firebase/auth';

const firebaseEnv = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
} as const;

function isConfiguredValue(value: string | undefined) {
  return Boolean(value && value.trim() && !value.startsWith('your_'));
}

const missingFirebaseKeys = Object.entries(firebaseEnv)
  .filter(([, value]) => !isConfiguredValue(value))
  .map(([key]) => key);

export const firebaseSetup = {
  isConfigured: missingFirebaseKeys.length === 0,
  missingKeys: missingFirebaseKeys,
  message:
    missingFirebaseKeys.length === 0
      ? null
      : `Firebase sign-in is not configured yet. Add ${missingFirebaseKeys.join(', ')} to the frontend .env file.`,
};

let app: FirebaseApp | null = null;
let auth: Auth | null = null;
let googleProvider: GoogleAuthProvider | null = null;

if (firebaseSetup.isConfigured) {
  app = initializeApp(firebaseEnv);
  auth = getAuth(app);
  googleProvider = new GoogleAuthProvider();
}

export { app, auth, googleProvider };
