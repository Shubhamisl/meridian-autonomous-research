import { createContext, useEffect, useState, type ReactNode } from 'react';
import {
  getRedirectResult,
  onAuthStateChanged,
  signInWithPopup,
  signInWithRedirect,
  signOut,
  type User,
} from 'firebase/auth';
import { auth, firebaseSetup, googleProvider } from '../lib/firebase';

export interface AuthContextType {
  user: User | null;
  loading: boolean;
  isConfigured: boolean;
  setupMessage: string | null;
  authError: string | null;
  login: () => Promise<void>;
  logout: () => Promise<void>;
  getToken: () => Promise<string | null>;
}

const AuthContext = createContext<AuthContextType | null>(null);
const E2E_BYPASS_STORAGE_KEY = 'meridian:e2e-auth';
const isE2ETestingEnabled = import.meta.env.VITE_E2E_TESTING === '1';

function isLocalE2EHost() {
  if (typeof window === 'undefined') {
    return false;
  }

  return ['127.0.0.1', 'localhost'].includes(window.location.hostname);
}

function createE2ETestUser(): User {
  return {
    uid: 'e2e-user',
    displayName: 'E2E Researcher',
    email: 'e2e@example.com',
    emailVerified: true,
    isAnonymous: false,
    phoneNumber: null,
    photoURL: null,
    metadata: {
      creationTime: '',
      lastSignInTime: '',
    },
    providerData: [],
    providerId: 'firebase',
    refreshToken: 'e2e-refresh-token',
    tenantId: null,
    delete: async () => undefined,
    getIdToken: async () => 'e2e-token',
    getIdTokenResult: async () => ({
      token: 'e2e-token',
      authTime: '',
      expirationTime: '',
      issuedAtTime: '',
      signInProvider: 'custom',
      signInSecondFactor: null,
      claims: {},
    }),
    reload: async () => undefined,
    toJSON: () => ({ uid: 'e2e-user' }),
  } as User;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const bypassEnabled =
    isE2ETestingEnabled &&
      isLocalE2EHost() &&
      window.localStorage.getItem(E2E_BYPASS_STORAGE_KEY) === '1';
  const [user, setUser] = useState<User | null>(() => {
    return bypassEnabled ? createE2ETestUser() : null;
  });
  const [authError, setAuthError] = useState<string | null>(null);
  const [loading, setLoading] = useState(() => {
    if (bypassEnabled) {
      return false;
    }

    return Boolean(auth);
  });

  useEffect(() => {
    if (bypassEnabled) return undefined;

    if (!auth) return undefined;

    getRedirectResult(auth).catch((error) => {
      console.error('Firebase redirect auth failed', error);
      setAuthError('Google sign-in could not be completed. Please try again.');
    });

    const unsubscribe = onAuthStateChanged(auth, (u) => {
      setUser(u);
      setLoading(false);
      if (u) {
        setAuthError(null);
      }
    });
    return unsubscribe;
  }, [bypassEnabled]);

  const login = async () => {
    if (!auth || !googleProvider) {
      throw new Error(firebaseSetup.message ?? 'Firebase sign-in is not configured.');
    }

    setAuthError(null);

    try {
      await signInWithPopup(auth, googleProvider);
      return;
    } catch (error) {
      console.warn('Firebase popup sign-in failed, falling back to redirect', error);
    }

    try {
      await signInWithRedirect(auth, googleProvider);
    } catch (error) {
      console.error('Firebase redirect sign-in failed', error);
      setAuthError('Google sign-in is unavailable right now. Check Firebase authorized domains and try again.');
    }
  };

  const logout = async () => {
    if (bypassEnabled) {
      window.localStorage.removeItem(E2E_BYPASS_STORAGE_KEY);
      setUser(null);
      return;
    }

    if (!auth) return;
    await signOut(auth);
  };

  const getToken = async (): Promise<string | null> => {
    if (!user) return null;
    return user.getIdToken();
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        isConfigured: firebaseSetup.isConfigured,
        setupMessage: firebaseSetup.message,
        authError,
        login,
        logout,
        getToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export { AuthContext };
