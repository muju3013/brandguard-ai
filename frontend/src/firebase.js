import { initializeApp, getApps } from 'firebase/app';
import {
  getAuth,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  sendPasswordResetEmail,
  signOut,
  onAuthStateChanged
} from 'firebase/auth';

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || '',
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || '',
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || '',
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || '',
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || '',
  appId: import.meta.env.VITE_FIREBASE_APP_ID || ''
};

export const isFirebaseConfigured = Boolean(
  firebaseConfig.apiKey &&
  firebaseConfig.apiKey !== 'YOUR_API_KEY' &&
  firebaseConfig.projectId
);

export const isDemoAuthEnabled =
  import.meta.env.VITE_ENABLE_DEMO_AUTH !== 'false' &&
  !import.meta.env.PROD &&
  import.meta.env.MODE !== 'production';

let firebaseApp = null;
let firebaseAuthInstance = null;

if (isFirebaseConfigured) {
  try {
    firebaseApp = getApps().length === 0 ? initializeApp(firebaseConfig) : getApps()[0];
    firebaseAuthInstance = getAuth(firebaseApp);
  } catch (err) {
    console.warn('Firebase initialization error:', err);
  }
}

// ---------------------------------------------------------------------------
// Unified Auth API supporting both live Firebase and Developer Demo Auth
// ---------------------------------------------------------------------------

const LOCAL_STORAGE_KEY = 'brandguard_auth_user';

export async function loginWithEmail(email, password) {
  if (isFirebaseConfigured && firebaseAuthInstance) {
    const cred = await signInWithEmailAndPassword(firebaseAuthInstance, email, password);
    const token = await cred.user.getIdToken();
    const userObj = {
      uid: cred.user.uid,
      email: cred.user.email,
      token,
      mode: 'firebase'
    };
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(userObj));
    return userObj;
  }

  if (!isDemoAuthEnabled) {
    throw new Error('Production mode requires active Firebase Authentication. Demo authentication is disabled.');
  }

  // Demo Fallback: deterministic authentication for development and testing
  const token = `demo-token:${email}`;
  const userObj = {
    uid: `user_${email.split('@')[0]}`,
    email,
    token,
    mode: 'demo'
  };
  localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(userObj));
  window.dispatchEvent(new Event('brandguard_auth_change'));
  return userObj;
}

export async function registerWithEmail(email, password) {
  if (isFirebaseConfigured && firebaseAuthInstance) {
    const cred = await createUserWithEmailAndPassword(firebaseAuthInstance, email, password);
    const token = await cred.user.getIdToken();
    const userObj = {
      uid: cred.user.uid,
      email: cred.user.email,
      token,
      mode: 'firebase'
    };
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(userObj));
    return userObj;
  }

  if (!isDemoAuthEnabled) {
    throw new Error('Production mode requires active Firebase Authentication. Demo registration is disabled.');
  }

  // Demo register fallback
  return loginWithEmail(email, password);
}

export async function resetPassword(email) {
  if (isFirebaseConfigured && firebaseAuthInstance) {
    await sendPasswordResetEmail(firebaseAuthInstance, email);
    return true;
  }
  throw new Error('Firebase Authentication is not configured on the client.');
}

export async function loginWithDemoIdentity(demoUser) {
  if (!isDemoAuthEnabled) {
    throw new Error('Demo authentication is disabled in production.');
  }
  const userObj = {
    uid: demoUser.user_id,
    email: demoUser.email,
    token: demoUser.token,
    role: demoUser.role,
    org_id: demoUser.org_id,
    org_name: demoUser.org_name,
    display_name: demoUser.display_name,
    mode: 'demo'
  };
  localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(userObj));
  window.dispatchEvent(new Event('brandguard_auth_change'));
  return userObj;
}

export async function logoutUser() {
  if (isFirebaseConfigured && firebaseAuthInstance) {
    await signOut(firebaseAuthInstance);
  }
  localStorage.removeItem(LOCAL_STORAGE_KEY);
  window.dispatchEvent(new Event('brandguard_auth_change'));
}

export function getStoredUser() {
  try {
    const data = localStorage.getItem(LOCAL_STORAGE_KEY);
    return data ? JSON.parse(data) : null;
  } catch {
    return null;
  }
}

export function subscribeToAuthState(callback) {
  if (isFirebaseConfigured && firebaseAuthInstance) {
    return onAuthStateChanged(firebaseAuthInstance, async (user) => {
      if (user) {
        const token = await user.getIdToken();
        const userObj = {
          uid: user.uid,
          email: user.email,
          token,
          mode: 'firebase'
        };
        localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(userObj));
        callback(userObj);
      } else {
        localStorage.removeItem(LOCAL_STORAGE_KEY);
        callback(null);
      }
    });
  }

  // Demo listener
  const handler = () => {
    callback(getStoredUser());
  };
  window.addEventListener('brandguard_auth_change', handler);
  // initial call
  callback(getStoredUser());

  return () => {
    window.removeEventListener('brandguard_auth_change', handler);
  };
}

// Resolve the current Firebase ID token for each authenticated API operation.
// Firebase refreshes expiring ID tokens internally; the forced variant is used
// once after a server rejects a request with HTTP 401.
export async function getFreshAuthToken(existingToken, forceRefresh = false) {
  if (isFirebaseConfigured && firebaseAuthInstance?.currentUser) {
    return firebaseAuthInstance.currentUser.getIdToken(forceRefresh);
  }
  if (isDemoAuthEnabled && existingToken?.startsWith('demo-token:')) {
    return existingToken;
  }
  throw new Error('Your Firebase session is no longer active. Please sign in again.');
}
