import { createContext, useEffect, useState, type ReactNode } from 'react';
import { onAuthStateChanged, signInWithPopup, signOut, type User } from 'firebase/auth';
import { auth, firebaseSetup, googleProvider } from '../lib/firebase';

export interface AuthContextType {
  user: User | null;
  loading: boolean;
  isConfigured: boolean;
  setupMessage: string | null;
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
  const [loading, setLoading] = useState(() => {
    if (bypassEnabled) {
      return false;
    }

    return Boolean(auth);
  });

  useEffect(() => {
    if (bypassEnabled) return undefined;

    if (!auth) {
      return undefined;
    }

    const unsubscribe = onAuthStateChanged(auth, (u) => {
      setUser(u);
      setLoading(false);
    });
    return unsubscribe;
  }, [bypassEnabled]);

  const login = async () => {
    if (!auth || !googleProvider) {
      throw new Error(firebaseSetup.message ?? 'Firebase sign-in is not configured.');
    }

    await signInWithPopup(auth, googleProvider);
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
