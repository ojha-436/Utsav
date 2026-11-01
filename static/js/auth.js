// Firebase sign-in (Google or email/password). The server verifies every token.
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.14.1/firebase-app.js";
import {
  GoogleAuthProvider,
  createUserWithEmailAndPassword,
  signOut as firebaseSignOut,
  getAuth,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signInWithPopup,
} from "https://www.gstatic.com/firebasejs/10.14.1/firebase-auth.js";
import { api, setTokenProvider } from "./api.js";
import { state } from "./state.js";

let auth = null;

const FRIENDLY = {
  "auth/invalid-credential": "That email and password don't match.",
  "auth/invalid-email": "Enter a valid email address.",
  "auth/user-disabled": "This account has been disabled.",
  "auth/email-already-in-use": "An account with this email already exists. Sign in instead.",
  "auth/weak-password": "Use at least 6 characters for your password.",
  "auth/too-many-requests": "Too many attempts. Wait a moment and try again.",
  "auth/popup-blocked": "Your browser blocked the sign-in window. Allow pop-ups and try again.",
  "auth/network-request-failed": "Network problem. Check your connection and try again.",
  "auth/unauthorized-domain":
    "Google sign-in isn't switched on for this site yet. Use email and password for now.",
};

/** A plain-language message for a Firebase Auth error. */
export function authMessage(err) {
  return FRIENDLY[err?.code] ?? "Sign-in didn't work. Please try again.";
}

/** True when the user simply closed the Google pop-up. */
export const isCancelled = (err) =>
  ["auth/popup-closed-by-user", "auth/cancelled-popup-request"].includes(err?.code);

/**
 * Starts Firebase Auth and calls `onUser` on every sign-in change.
 * @returns {Promise<boolean>} false when accounts aren't configured (local development).
 */
export async function initAuth(onUser) {
  const config = await api("/api/config");
  if (!config.firebaseApiKey) return false;
  const app = initializeApp({
    apiKey: config.firebaseApiKey,
    authDomain: config.firebaseAuthDomain,
    projectId: config.projectId,
  });
  auth = getAuth(app);
  onAuthStateChanged(auth, (user) => {
    state.user = user;
    setTokenProvider(user ? () => user.getIdToken() : null);
    onUser(user);
  });
  return true;
}

/** Signs in with a Google pop-up. */
export const signInGoogle = () => signInWithPopup(auth, new GoogleAuthProvider());
/** Signs in with email and password. */
export const signInEmail = (email, password) => signInWithEmailAndPassword(auth, email, password);
/** Creates an account with email and password. */
export const signUpEmail = (email, password) => createUserWithEmailAndPassword(auth, email, password);
/** Signs the current user out. */
export const signOut = () => firebaseSignOut(auth);
